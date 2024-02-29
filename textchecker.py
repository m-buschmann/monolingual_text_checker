import json
from flask import Flask, request, render_template, url_for
from sqlalchemy import func, desc, select
import nltk
from nltk.stem import SnowballStemmer
import nh3
nltk.download('punkt')
from read_data import insert_data
import os
import numpy as np
import difflib
from langdetect import detect

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

# Home page
@app.route('/', methods=['GET'])
def home():
    # render home.html template
    return render_template("home.html")


@app.route('/submit', methods=['POST'])
def submit():
    user_text = request.form['user_text']
    language = request.form.get('language', 'dgerman') # default to german if no language set
    
    # sanitize input
    clean_text = nh3.clean(user_text)

    # Find sensitive terms in the user text
    indices, terms, split_text = find_sensitive_terms(clean_text, language)

    marked_html, modals = create_marked_html(split_text, indices, terms, language)

    # return json with the textarea template ad the modals
    result = {"textarea": render_template("textarea.html", user_text=clean_text, indices=indices, terms=terms, marked_html=marked_html), 
              "modals": modals}
    
    # when we have the html, we can use this line to return the results
    return json.dumps(result)

def find_sensitive_terms(text, language='german'):
    """
    Identifies sensitive terms in the input text, including multi-word terms, and returns the text split into terms,
    with words merged again that together form a term from the database. It also returns the starting indices of
    each sensitive term found.
    
    Parameters:
    - text (str): The input text in which to find sensitive terms.
    - language (str): The language of the input text, used to select the appropriate stemmer.
    
    Returns:
    - tuple: A tuple containing three elements:
        1. A list of starting indices (int) where sensitive terms were found in the input text.
        2. A list of the original forms (str) of these sensitive terms as they are stored in the database.
        3. A list of terms (str) as they appear in the input text, with multi-word terms merged.
    """
    stemmer = SnowballStemmer(language)
    words = nltk.word_tokenize(text)
    words_lower = [word.lower() for word in words]
    stemmed_words = [stemmer.stem(word) for word in words_lower]
    stemmed_text = " ".join(stemmed_words)
    terms = Term.query.filter(Term.language == language)


    sensitive_indices, sensitive_terms = [], []
    split_text = []  # To store the split terms
    current_index = 0  # Track the current index in stemmed_words

    for term in terms:
        stemmed_term = " ".join([stemmer.stem(word) for word in term.term.split()])
        if stemmed_term in stemmed_text:
            # Identify the start and end indices for the matched term
            start_index = stemmed_text.find(stemmed_term)
            end_index = start_index + len(stemmed_term)
            # Convert indices back to word indices in the original list
            word_start_index = len(stemmed_text[:start_index].split())
            word_end_index = len(stemmed_text[:end_index].split())
            # Add the matched term to sensitive_indices and sensitive_terms
            sensitive_indices.append(word_start_index)
            sensitive_terms.append(term.term)
            # Append non-matched words to split_text before the matched term
            split_text.extend(words[current_index:word_start_index])
            # Append the matched term as a single entry
            split_text.append(" ".join(words[word_start_index:word_end_index]))
            current_index = word_end_index  # Update current_index to continue after the matched term

    # Append any remaining words after the last matched term
    split_text.extend(words[current_index:])

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
    next_modal_id = 0
    modals = ""

    for i,word in enumerate(text):
        # add to the text until text should be marked changes
        text_to_add += word + " "
        if text[i] in ",;.:-_!?": # TODO check for all non special characters
            text_to_add = text_to_add[:-1]

        if next_marked!=-1 and i+1>next_marked:
            next_marked = indices.pop(0) if len(indices)>0 else -1
            #term_index += 1
            # current text is currently should be marked
            # create highlight

        


        if next_marked == i+1 and not text_should_be_marked and text_to_add:
            # text should be marked next but isn't currently
            # create a span with the current text
            marked_html += span.format(text_to_add)
            text_to_add = ""
            next_marked = indices.pop(0) if len(indices)>0 else -1
            text_should_be_marked = True
        elif text_should_be_marked:
            popups, new_modals, next_modal_id = create_popup_html(terms[term_index], language, next_modal_id)
            modals += new_modals
            marked_html += highlight.format(text_to_add.rstrip(), popups)+" "
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

    return marked_html.rstrip(), modals

@app.route('/rate_alternative', methods=['POST'])
def rate_alternative():
    # Handle exceptions 
    if not 'original_id' in request.form:
        return "No original_id provided", 400
    if not 'alternative_id' in request.form:
        return "No alternative_id provided", 400
    if not 'rating' in request.form:
        return "No rating provided", 400
    else:
        try:
            original_id = request.form.get('original_id')
            alternative_id = request.form.get('alternative_id')
            rating = int(request.form.get('rating'))
            
            if Term.query.get(original_id) is None or Term.query.get(alternative_id) is None:
                return "Not a valid id", 400

        except ValueError:
            return "Malformed request parameters provided", 400
        
        # add rating to database
        alt_rating = AlternativeRating(term_id=original_id, alternative_term_id=alternative_id, rating=rating)
        db.session.add(alt_rating)
        db.session.commit()

    
    return "rate alternative"

@app.route('/report', methods=["POST"])
def report():
    print("report")
    print(request.form)
    # Handle exceptions 
    if not 'term_id' in request.form:
        return "No term_id provided", 400
    else:
        try:
            term_id = request.form.get('term_id')
            if Term.query.get(term_id) is None:
                return "Not a valid term id", 400

        except ValueError:
            return "Malformed request parameters provided", 400

        # create offensiveness rating
        o_rating = OffensivenessRating(term_id=term_id, rating=1)
        db.session.add(o_rating)
        db.session.commit()
    
    return "okay", 200
        
def create_popup_html(term, language, starting_modal_id):
    # templates
    alternative_heading = "Alternative terms" if language=="english" else "Alternative Begriffe"
    popup = "<div class='popuptext'><h3>{term_term}{report}</h3><p>{term_description}<p><h4>{alternative_heading}</h4>{alternative_list}</div>"
    alternative_list = "<ol>{list}</ol>"
    list_item = "<li><a href=\"{term_base_url}{term_id}\">{term_term}</a> {alt_rating} {rate} {report}</li>"

    button_html = "<button type=\"button\" class=\"open-modal\" data-open=\"modal{modal_id}\">{button_text}</button>"
    offensive_modal_html = "<div class=\"modal\" id=\"modal{modal_id}\"><div class=\"modal-dialog\"><header class=\"modal-header\"><button class=\"close-modal\" aria-label=\"close modal\" data-close>✕</button></header><section class=\"modal-content\">Do you want to mark the term {term} as offensive?<button class=\"mark-offensive\" onclick=\"mark_offensive('{term_id}')\" data-close>Yes</button><button class=\"close-modal\" aria-label=\"close modal\" data-close>No</button></section></div></div>"
    rating_modal_html = """ <div class="modal" id="modal{modal_id}">
  <div class="modal-dialog">
    <header class="modal-header">
      Rate {alternative_term} as alternative to {original_term}
      <button class="close-modal" aria-label="close modal" data-close>✕</button>
    </header>
    <section class="modal-content">
      <p>Select how good of an alternative {alternative_term} is for the original term {original_term}</p>
      <fieldset id="rate{modal_id}">
        <legend>Rate the appropriateness of the term:</legend>
      
        <div>
          <input type="radio" id="1" name="alternative_rating" value="1" checked />
          <label for="1">1</label>
        </div>
      
        <div>
          <input type="radio" id="2" name="alternative_rating" value="2" />
          <label for="2">2</label>
        </div>
      
        <div>
          <input type="radio" id="3" name="alternative_rating" value="3" />
          <label for="3">3</label>
        </div>
      
        <div>
          <input type="radio" id="4" name="alternative_rating" value="4" />
          <label for="4">4</label>
        </div>
      
        <div>
          <input type="radio" id="5" name="alternative_rating" value="5" />
          <label for="5">5</label>
        </div>
      </fieldset>
      <button class="rate-alternative" term_id={term_id} alt_id={alt_term_id} data-open={modal_id} data-close rate-alternative>Submit rating</button>
      <button class="close-modal" aria-label="close modal" data-close>Cancel</button>
    </section>
  </div>
</div>"""


    

    # get alternative terms
    alternatives = AlternativeTerm.query.filter(AlternativeTerm.original_term_id==term.id).all()
    modal_id = starting_modal_id
    
    # for each alteranative term
    alternatives_list = []
    alt_mean_rating_list = []

    all_modals = ""

    for alt_term in alternatives:
        # get the term object
        alternative_term_object = Term.query.get(alt_term.alternative_term_id)

        # get the average rating for the term
        avg = AlternativeRating.query.filter(AlternativeRating.term_id==term.id, AlternativeRating.alternative_term_id==alternative_term_object.id).with_entities(func.avg(AlternativeRating.rating)).first()
        
        # if there are no ratings set the average to the middle value
        a = avg[0] if avg[0] is not None else 2.5
        alt_mean_rating_list.append(a)

        alt_rating = "{:.2f}".format(avg[0]) if avg[0] is not None else ""

        # get the url for the rate function
        rate_url = url_for('rate_alternative', original_id=term.id, alternative_id=alternative_term_object.id)
        report = button_html.format(modal_id=modal_id, button_text="Mark as offensive")
        
        # create modal and add it to the string with all modals
        modal = offensive_modal_html.format(modal_id=modal_id, term=alternative_term_object.term, term_id=alternative_term_object.id)
        all_modals = all_modals + modal
        modal_id += 1

        rate = button_html.format(modal_id=modal_id, button_text="Rate")
        modal = rating_modal_html.format(term_id=term.id, alt_term_id=alternative_term_object.id, modal_id=modal_id, alternative_term=alternative_term_object.term, original_term=term.term)
        all_modals = all_modals + modal
        modal_id += 1
        

        # construct each list item
        alternatives_list.append(list_item.format(rate=rate, report=report, rate_url=rate_url, term_term=alternative_term_object.term, term_base_url="https://www.machtsprache.de/term/", term_id=alternative_term_object.id, alt_rating=alt_rating, original_id=term.id, alt_id=alternative_term_object.id))
    # construct the whole list
        
    # sort by rating
    sorted_indices = np.argsort(np.array(alt_mean_rating_list).flatten())
    sorted_alternatives = np.array(alternatives_list)[sorted_indices[::-1]] # TODO: higher is better?
    
    complete_list = ""+alternative_list.format(list="".join(sorted_alternatives))

    #report = report_string.format(report_url=url_for('report', term_id=term.id))
    report = button_html.format(modal_id=modal_id, button_text="Mark as offensive")
    modal = offensive_modal_html.format(modal_id=modal_id, term=term.term, term_id=term.id)
    all_modals = all_modals + modal
    modal_id += 1

    # construct the whole popup and return it
    return popup.format(report=report, term_term=term.term, term_description=term.description, alternative_heading=alternative_heading, alternative_list=complete_list), all_modals, modal_id

if __name__ == '__main__':
    app.run(debug=True)
