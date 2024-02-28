from flask import Flask, request, render_template, url_for
from sqlalchemy import func, desc, select
import nltk
from nltk.stem import SnowballStemmer
import nh3
nltk.download('punkt')
from read_data import insert_data
import os

from models import *


# APP CONFIGURATION 
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///sensitive_terms.sqlite'  # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Avoids SQLAlchemy warning


# CREATE FLASK APP 
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  
app.app_context().push()  
db.init_app(app)  
db.create_all()

# Get the directory of the current script
current_directory = os.path.dirname(os.path.realpath(__file__))

@app.cli.command('initdb')
def initdb_command():
    global db
    """Creates the database tables."""
    insert_data(db)
    print('Initialized the database.')


# Home page
@app.route('/', methods=['GET'])
def home():
    # render home.html template
    return render_template("home.html")


@app.route('/submit', methods=['POST'])
def submit():
    user_text = request.form['user_text']
    language = request.form.get('language', 'german') # default to german if no language set
    
    # sanitize input
    clean_text = nh3.clean(user_text)

    # Find sensitive terms in the user text
    indices, terms, split_text = find_sensitive_terms(clean_text, language)

    marked_html = create_marked_html(split_text, indices, terms, language)
    
    # when we have the html, we can use this line to return the results
    return render_template("textarea.html", user_text=clean_text, indices=indices, terms=terms, marked_html=marked_html)

def find_sensitive_terms(text, language='german'):
    stemmer = SnowballStemmer(language)
    words = nltk.word_tokenize(text)
    words_lower = [word.lower() for word in words]
    stemmed_words = [stemmer.stem(word) for word in words_lower]
    stemmed_text = " ".join(stemmed_words)
    
    # Fetch terms from the database and sort them by word count (descending) -> first check for the longest terms
    terms = Term.query.filter().all()
    sorted_terms = sorted(terms, key=lambda t: len(t.term.split()), reverse=True)

    matched_terms_details = []
    covered_indices = set()  # Keep track of indices already covered by a match

    for term in sorted_terms:
        stemmed_term = " ".join([stemmer.stem(word) for word in term.term.split()])
        if stemmed_term in stemmed_text:
            term_index = stemmed_text.find(stemmed_term)
            if term_index != -1:
                word_index = len(stemmed_text[:term_index].split())
                end_word_index = word_index + len(stemmed_term.split())
                
                # Check if any of the words in the term are already covered
                if not any(index in covered_indices for index in range(word_index, end_word_index)):
                    matched_terms_details.append((word_index, end_word_index, term))
                    # Mark these indices as covered
                    covered_indices.update(range(word_index, end_word_index))

    # Sort matched terms by their start index to ensure correct order
    matched_terms_details.sort(key=lambda x: x[0])

    # Generate the final split text in the correct order, merging terms as needed
    split_text, sensitive_indices, sensitive_terms = [], [], []
    last_index = 0
    for start_index, end_index, term in matched_terms_details:
        # Add words before the matched term
        split_text.extend(words[last_index:start_index])
        # Add the matched term itself
        split_text.append(" ".join(words[start_index:end_index]))
        # Update sensitive_indices to only include the start index of the term
        sensitive_indices.append(start_index)
        sensitive_terms.append(term)
        last_index = end_index
    # Add any remaining words after the last matched term
    split_text.extend(words[last_index:])
    
    print(sensitive_indices, sensitive_terms, split_text)
    return sensitive_indices, sensitive_terms, split_text



def create_marked_html(text, term_indices, terms, language):
    """
    inputs
        text: list of strings, can be turned into a text string by appending elements separated by a space
        indices: indices of the sensitive terms within the text list that are to be marked

    returns:
        marked_html: html containing the text in the format needed to display it with highlights
    """

    print("text", text)
    print("term_indices", term_indices)
    print("terms", terms)
    if len(term_indices) == 0:
        return text

    marked_html = ""
    span = "{}"
    highlight= "<mark  class='popup'>{}{}</mark>"
    indices = term_indices.copy()
    text_to_add = ""
    next_marked = indices.pop(0)
    term_index = 0
    term = terms[term_index]
    text_should_be_marked = True if next_marked==0 else False

    for i,word in enumerate(text):
        print(i, word, next_marked, text_should_be_marked)
        # add to the text until text should be marked changes
        text_to_add += word + " "

        if next_marked!=-1 and i+1>next_marked:
            print("1")
            next_marked = indices.pop(0) if len(indices)>0 else -1
            #term_index += 1
            # current text is currently should be marked
            # create highlight

        


        if next_marked == i+1 and not text_should_be_marked and text_to_add:
            print("2")
            # text should be marked next but isn't currently
            # create a span with the current text
            marked_html += span.format(text_to_add)
            text_to_add = ""
            next_marked = indices.pop(0) if len(indices)>0 else -1
            
            text_should_be_marked = True
        elif text_should_be_marked:
            marked_html += highlight.format(text_to_add.rstrip(), create_popup_html(terms[term_index], language))+" "
            term_index += 1
            text_to_add = ""
            if next_marked == i+1:
                text_should_be_marked = True
            else:
                text_should_be_marked = False

    # add the last part of the text if there is something to add
    if text_should_be_marked and text_to_add:
        marked_html += highlight.format(text_to_add.rstrip(), terms[term_index].term, terms[term_index].description, "todo terms")
    elif text_to_add:
        marked_html += span.format(text_to_add.rstrip())

    return marked_html.rstrip()

@app.route('/rate_alternative')
def rate_alternative():
    
    return 200, "rate alternative"
        
def create_popup_html(term, language):
    # templates
    alternative_heading = "Alternative terms" if language=="english" else "Alternative Begriffe"
    popup = "<div class='popuptext'><h3>{term_term}</h3><p>{term_description}<p><h4>{alternative_heading}</h4>{alternative_list}</div>"
    alternative_list = "<ol>{list}</ol>"
    list_item = "<li><a href=\"{term_base_url}{term_id}\">{term_term}</a> {alt_rating} <a href=\"{rate_url}\">Rate</a></li>"
    # get the correct description base on the language

    # TODO
    description = term.description

    # get alternative terms
    alternatives = AlternativeTerm.query.filter(AlternativeTerm.original_term_id==term.id).all()
    
    # for each alteranative term
    alternatives_list = []
    alt_mean_rating_list = []

    for alt_term in alternatives:
        # get the term object
        alternative_term_object = Term.query.get(alt_term.alternative_term_id)

        # TODO get the alternative rating
        AlternativeRating.query.filter(AlternativeRating.term_id==term.id, AlternativeRating.alternative_term_id==alternative_term_object.id)#TODO get the average of all ratings
        # TODO if there are no ratings set the average to the middle value

        # get the average rating for the term
        avg = AlternativeRating.query.filter(AlternativeRating.term_id==term.id, AlternativeRating.alternative_term_id==alternative_term_object.id).with_entities(func.avg(AlternativeRating.rating)).first()
        
        print("avg", avg)
        # avg_rating = np.array(avg).flatten()[0]
        alt_mean_rating_list.append(avg[0])

        # sort alternatives by rating
        # get the url for the rate function
        rate_url = url_for('rate_alternative', original_id=term.id, alternative_id=alternative_term_object.id)
        # construct each list item
        alternatives_list.append(list_item.format(rate_url=rate_url, term_term=alternative_term_object.term, term_base_url="https://www.machtsprache.de/term/", term_id=alternative_term_object.id, alt_rating="TODO", original_id=term.id, alt_id=alternative_term_object.id))
    # construct the whole list
    
    complete_list = ""+alternative_list.format(list="".join(alternatives_list))

    # construct the whole popup and return it
    return popup.format(term_term=term.term, term_description=term.description, alternative_heading=alternative_heading, alternative_list=complete_list)

if __name__ == '__main__':
    app.run(debug=True)
