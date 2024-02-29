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
    language = request.form.get('language', 'auto') # Default to auto-detect
    if language == 'auto':
        language = auto_detect_language(user_text)
    
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

def auto_detect_language(text):
    """
    Detects the language of the given text.
    Parameters:
    - text (str): The text for which the language needs to be detected.
    Returns:
    - str: The detected language ('english' or 'german').
    """
    try:
        language_code = detect(text)
        if language_code == 'en':
            return 'english'
        elif language_code == 'de':
            return 'german'
        else:
            return 'german'  # Default to German if language cannot be detected
    except Exception as e:
        print(f"Error detecting language: {e}")
        return 'unknown'

def find_sensitive_terms(text, language='german'):
    """
    Identify and extract sensitive terms from the given text using stemming and approximate matching.
    
    This function processes a given text to find sensitive terms predefined in a database. It employs stemming to normalize both the input text and the sensitive terms for matching in a specified language. It sorts the terms by word count in descending order to prioritize matching longer terms first. The function also checks for approximate matches to catch typos or different spellings. Finally, it returns the indices of sensitive terms within the text, the terms themselves, and the text split into segments with sensitive terms isolated.
    
    Parameters:
    - text (str): The text to be analyzed for sensitive terms.
    - language (str, optional): The language used for stemming. Defaults to 'german'.
    
    Returns:
    - tuple: A tuple containing three elements:
        1. A list of indices where sensitive terms start in the original text.
        2. A list of sensitive term objects that were matched.
        3. The original text split into segments, with sensitive terms isolated.
    """
    # Initialize the stemmer for the specified language
    stemmer = SnowballStemmer(language)

    # Tokenize and stem the input text
    words = nltk.word_tokenize(text)
    words_lower = [word.lower() for word in words] # Lowercase all words for consistent matching
    stemmed_words = [stemmer.stem(word) for word in words_lower]
    stemmed_text = " ".join(stemmed_words) # Rejoin the stemmed words into a single string
    
    # Fetch predefined sensitive terms from the database, sorted by their length (descending)
    terms = Term.query.filter().all()
    sorted_terms = sorted(terms, key=lambda t: len(t.term.split()), reverse=True)

    matched_terms_details = [] # To store details of matched terms
    covered_indices = set()  # Track indices in the text that are already covered by a match

    # Iterate over each term to find matches in the stemmed text
    for term in sorted_terms:
        stemmed_term = " ".join([stemmer.stem(word) for word in term.term.split()])
        
        # Find all occurrences of the stemmed term in the stemmed text
        start_pos = 0
        while True:
            term_index = stemmed_text.find(stemmed_term, start_pos)
            if term_index == -1:
                break # Exit the loop if no more occurrences are found
            # Calculate the start and end word indices in the original text
            word_index = len(stemmed_text[:term_index].split())
            end_word_index = word_index + len(stemmed_term.split())

            # Append matched term details if it doesn't overlap with previously covered indices
            if not any(index in covered_indices for index in range(word_index, end_word_index)):
                matched_terms_details.append((word_index, end_word_index, term))
                # Mark indices as covered
                covered_indices.update(range(word_index, end_word_index))

            # Prepare for the next search iteration
            start_pos = term_index + len(stemmed_term)  # Update start_pos to search for next occurrence


            # Check for approximate matches for each word to account for typos or different spellings
            for index, word in enumerate(stemmed_words):
                if index in covered_indices:  # Skip if index is already covered
                    continue
                close_matches = difflib.get_close_matches(word, [term.term for term in sorted_terms], n=1, cutoff=0.8)
                if close_matches:
                    # Process each close match found
                    close_match_stemmed = close_matches[0]
                    # Find the term object from sorted_terms that matches the close_match_term_string
                    for possible_term_object in sorted_terms:
                        if stemmer.stem(term.term) == close_match_stemmed:
                            term_object = possible_term_object
                            break
                    else:
                        term_object = None # No matching term object found

                    if term_object:
                        # Check if this term object is not yet processed and add its details
                        for matched_term in matched_terms_details:
                            if term_object == matched_term[2]:  # If the term object matches
                                # Check if the index range of the current word overlaps with the matched term
                                if not any(index in covered_indices for index in range(matched_term[0], matched_term[1])):
                                    matched_terms_details.append((index, index + 1, term_object))
                                    covered_indices.add(index)
                                break  # Exit the loop as we found a match
                        else:
                            # Add new term object if it hasn't been matched yet
                            matched_terms_details.append((index, index + 1, term_object))
                            covered_indices.add(index)
    
    # Sort matched terms by their starting index for proper ordering
    matched_terms_details.sort(key=lambda x: x[0])

    # Reconstruct the text, isolating sensitive terms and recording their indices
    split_text, sensitive_indices, sensitive_terms = [], [], []
    last_index = 0 # Track the last processed index
    reduce_index_by = 0 # Adjustment for indices due to joining terms
    for start_index, end_index, term in matched_terms_details:
        
        # Add non-sensitive segments of the text
        split_text.extend(words[last_index:start_index])
        # Add the matched sensitive term
        split_text.append(" ".join(words[start_index:end_index]))
        # Record the index of the sensitive term
        sensitive_indices.append(start_index-reduce_index_by)
        sensitive_terms.append(term)
        last_index = end_index
        reduce_index_by += end_index-1-start_index
    # Add any remaining text after the last matched term
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

    if len(term_indices) == 0:
        return text

    marked_html = ""
    span = "{}"
    highlight= "<mark  class='popup' style=\"background-color:{color};\">{}{}</mark>"
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
        word =  "\"" if word == "``" else word # TODO change this in the future to not be hardcoded
        text_to_add += word + " "
        if not text[i].isalpha(): # check for all non special characters
            text_to_add = text_to_add[:-1]
            print("removing non alpha", text[i])

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
            # get offensiveness rating:
            o_ratings = len(OffensivenessRating.query.filter(OffensivenessRating.term_id==terms[term_index].id).all())
            color = "var(--green)"
            if o_ratings > 3: # TODO decide on proper cutoff values
                color = "var(--orange)"
            if o_ratings > 4:
                color = "var(--red)"
        
            marked_html += highlight.format(text_to_add.rstrip(), popups, color=color)+" "
            term_index += 1
            text_to_add = ""
            if next_marked == i+1:
                text_should_be_marked = True
            else:
                text_should_be_marked = False

    # add the last part of the text if there is something to add
    if text_should_be_marked and text_to_add:
        marked_html += highlight.format(text_to_add.rstrip(), popups, color=color)
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
    popup = "<div class='popuptext'><h3><a href=\"{term_base_url}{term_id}\">{term_term}</a>{report}</h3><p>{term_description}<p><h4>{alternative_heading}</h4>{alternative_list}</div>"
    alternative_list = "<ol>{list}</ol>"
    list_item = "<li><a href=\"{term_base_url}{term_id}\">{term_term}</a> {alt_rating} {rate} {report}</li>"

    button_html = "<button type=\"button\" class=\"open-modal\" data-open=\"modal{modal_id}\">{button_text}</button>"
    offensive_modal_html = "<div class=\"modal\" id=\"modal{modal_id}\"><div class=\"modal-dialog\"><header class=\"modal-header\"><button class=\"close-modal\" aria-label=\"close modal\" data-close>✕</button></header><section class=\"modal-content\">Do you want to mark the term \"{term}\" as offensive?<button class=\"mark-offensive\" onclick=\"mark_offensive('{term_id}')\" data-close>Yes</button><button class=\"close-modal\" aria-label=\"close modal\" data-close>No</button></section></div></div>"
    rating_modal_html = """ <div class="modal" id="modal{modal_id}">
  <div class="modal-dialog">
    <header class="modal-header">
      Rate "{alternative_term}" as alternative to "{original_term}"
      <button class="close-modal" aria-label="close modal" data-close>✕</button>
    </header>
    <section class="modal-content">
      <p>Select how good of an alternative "{alternative_term}" is for the original term "{original_term}"</p>
      <fieldset id="rate{modal_id}">      
        <div>
          <input type="radio" id="1" name="alternative_rating" value="1" checked />
          <label for="1">1 - Bad alternative, do not use</label>
        </div>
      
        <div>
          <input type="radio" id="2" name="alternative_rating" value="2" />
          <label for="2">2 - Inappropriate alternative</label>
        </div>
      
        <div>
          <input type="radio" id="3" name="alternative_rating" value="3" />
          <label for="3">3 - Appropriate alternative, both terms can be used interchangibly without affecting meaning or sensitivity</label>
        </div>
      
        <div>
          <input type="radio" id="4" name="alternative_rating" value="4" />
          <label for="4">4 - Good alternative</label>
        </div>
      
        <div>
          <input type="radio" id="5" name="alternative_rating" value="5" />
          <label for="5">5 - Great alternative, always replace the original with this</label>
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
    sorted_alternatives = np.array(alternatives_list)[sorted_indices[::-1]]
    
    complete_list = ""+alternative_list.format(list="".join(sorted_alternatives))

    #report = report_string.format(report_url=url_for('report', term_id=term.id))
    report = button_html.format(modal_id=modal_id, button_text="Mark as offensive")
    modal = offensive_modal_html.format(modal_id=modal_id, term=term.term, term_id=term.id)
    all_modals = all_modals + modal
    modal_id += 1

    # construct the whole popup and return it
    return popup.format(term_base_url="https://www.machtsprache.de/term/", term_id=term.id,report=report, term_term=term.term, term_description=term.description, alternative_heading=alternative_heading, alternative_list=complete_list), all_modals, modal_id

if __name__ == '__main__':
    app.run(debug=True)
