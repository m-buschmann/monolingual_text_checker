from flask import Flask, request, render_template
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

    marked_html = create_marked_html(split_text, indices)
    
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
                    matched_terms_details.append((word_index, end_word_index, term.term))
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



def create_marked_html(text, term_indices):
    """
    inputs
        text: list of strings, can be turned into a text string by appending elements separated by a space
        indices: indices of the sensitive terms within the text list that are to be marked

    returns:
        marked_html: html containing the text in the format needed to display it with highlights
    """

    if len(term_indices) == 0:
        return text

    marked_html = ""
    span = "{}"
    highlight= "<mark>{}</mark>"
    indices = term_indices.copy()
    text_to_add = ""
    next_marked = indices.pop(0)
    text_should_be_marked = True if next_marked==0 else False

    for i,word in enumerate(text):
        # add to the text until text should be marked changes
        text_to_add += word + " "

        if next_marked!=-1 and i+1>next_marked:
            next_marked = indices.pop(0) if len(indices)>0 else -1

        if next_marked == i+1 and not text_should_be_marked and text_to_add:
            # create a span with the current text
            marked_html += span.format(text_to_add)
            text_to_add = ""
            next_marked = indices.pop(0) if len(indices)>0 else -1
            text_should_be_marked = True
        elif next_marked != i+1 and text_should_be_marked and text_to_add:
            # text is currently marked but should not be for the next word
            # create highlight
            marked_html += highlight.format(text_to_add.rstrip())+" "
            text_to_add = ""
            text_should_be_marked = False


    # add the last part of the text if there is something to add
    if text_should_be_marked and text_to_add:
        marked_html += highlight.format(text_to_add.rstrip())
    elif text_to_add:
        marked_html += span.format(text_to_add.rstrip())

    return marked_html.rstrip()
        

if __name__ == '__main__':
    app.run(debug=True)
