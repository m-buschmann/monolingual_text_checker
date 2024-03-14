import json
from flask import Flask, request, render_template, url_for
from sqlalchemy import func, desc, select
import nltk
from nltk.stem import SnowballStemmer
import nh3
from read_data import insert_data
import os
import numpy as np
import difflib
from langdetect import detect

from models import *

# download the punkt nltk dataset that is required for splitting the text
nltk.download('punkt')

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

supported_languages = ["english", "german"]

# Get the directory of the current script
current_directory = os.path.dirname(os.path.realpath(__file__))

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    global db
    insert_data(db)
    print('Initialized the database.')


# Home page
@app.route('/', methods=['GET'])
def home():
    # render home.html template
    return render_template("home.html")


@app.route('/submit', methods=['POST'])
def submit():
    # use default values if no user_text or language were provided
    user_text = request.form.get('user_text', '')
    language = request.form.get('language', 'auto') # Default to auto-detect
    detected = 0

    if language == 'auto':
        detected = 1
        language = auto_detect_language(user_text)

    if user_text is not None and user_text.strip() and language in supported_languages: # only process if there is user text to process and it is in one of the supported languages
        # sanitize input
        clean_text = nh3.clean(user_text)

        # Find sensitive terms in the user text
        indices, terms, split_text = find_sensitive_terms(clean_text, language)

        # create corresponding HTML that will be inserted in the displayed page
        marked_html, modals = create_marked_html(clean_text, split_text, indices, terms, language)

        # create dictionary with the textarea template and the modals
        result = {"textarea": render_template("textarea.html", user_text=clean_text, indices=indices, terms=terms, marked_html=marked_html), 
                "modals": modals,
                "detected": detected,
                "language": language.capitalize()}
    else:
        # create dictionary with the textarea template and no modals
        result = {"textarea": render_template("textarea.html", user_text=user_text), 
                "modals": None,
                "detected": detected,
                "language": language.capitalize()}
    
    # return the result dictionary as json
    return json.dumps(result)

def auto_detect_language(text): #[TODO] shouldn't this return German even if there was an error? Otherwise we have to check for 'unknown' or it will lead to errors in the other functions
    """
    Detects the language of the given text.
    Parameters:
    - text (str): The text for which the language needs to be detected.
    Returns:
    - str: The detected language ('english', 'german', or 'unknown').
    """
    try:
        language_code = detect(text)
        if language_code == 'en':
            return 'english'
        elif language_code == 'de':
            return 'german'
        else:
            return 'german'  # Default to German if language cannot be detected or is not one of the supported languages
    except Exception as e:
        print(f"Error detecting language: {e}")
        return 'unknown'

def find_sensitive_terms(text, language='german'):
    """
    Identify and extract sensitive terms from the given text using stemming and matching of similar words to account for different spellings.
    
    This function processes a given text to find sensitive terms predefined in a database. It employs stemming to normalize both the input text and the sensitive terms for matching in a specified language. 
    It sorts the terms by word count in descending order to prioritize matching longer terms first. The function also checks for approximate matches to catch typos or different spellings. 
    Finally, it returns the indices of sensitive terms within the text, the terms themselves, and the text split into segments with sensitive terms isolated.
    
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
   
    
    # Fetch predefined sensitive terms from the database, sorted by their length (descending)
    terms = Term.query.filter().all()
    sorted_terms = sorted(terms, key=lambda t: len(t.term.split()), reverse=True)

    split_sorted_terms = [term.term.split(" ") for term in sorted_terms]
    t  = []
    for terms in split_sorted_terms:
        for term in terms:
            t.append(term)
    split_sorted_terms = t
    
    matched_terms_details = [] # To store details of matched terms
    covered_indices = set()  # Track indices in the text that are already covered by a match

    # check for different spellings by correcting words close to the listed ones before checking
    new_stemmed_words = []
    for word in stemmed_words:
        close_matches = difflib.get_close_matches(word, split_sorted_terms, n=1, cutoff=0.8)
        if close_matches:
            new_stemmed_words.append(stemmer.stem(close_matches[0].lower()))
        else:
            new_stemmed_words.append(word)

    stemmed_words = new_stemmed_words
    stemmed_text = " ".join(stemmed_words) # Rejoin the stemmed words into a single string
    stemmed_text = " " + stemmed_text
    
    # Iterate over each term to find matches in the stemmed text
    for term in sorted_terms:

        stemmed_term = " ".join([stemmer.stem(word) for word in term.term.split()])

        if stemmed_term == "":
            print("empty stem term", term.term)
            # if there is no stem we don't have to search for it, just move on to the next term
            continue
        
        # Find all occurrences of the stemmed term in the stemmed text
        start_pos = 0
        while True:
            term_index = stemmed_text.find(" "+stemmed_term, start_pos)
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
    
    return sensitive_indices, sensitive_terms, split_text

def create_marked_html(text, split_text, term_indices, terms, language='german'):
    """
    Creates HTML of the text with the terms at the supplied indices marked, as well as for the popups of the corresponding terms. 

    arguments:
        text (str): The complete text in which to mark terms as one string. The marked text will match the white space of this text. 
        split_text (list): List of strings (words) from the text, can be turned into the text by appending with corresponding white space in between each list element. 
        term_indices (list): List of integers indicating the indices of the sensitive terms within the split_text list that are to be marked
        terms (list): List of term objects, containing the terms that are to be marks in the order they appear in the text. Needs to be of the same length as term_indices. 
        language (str): Optional parameter indicating the language of the text, should be one of the supported languages ('english' or 'german'). Defaults to 'german'. 

    returns:
        marked_html: HTML containing the text in the format needed to display it with highlights, including the popups with detailed information of each terms and alternatives. 
    """

    # if there are no terms to mark return None
    if len(term_indices) == 0:
        return None
    
    # if term_indices and terms do not have the same length, find common length and work with that
    if len(term_indices)<len(terms):
        terms=terms[:len(term_indices)]
        print("Warning: term_indices and terms do not have the same length, not all terms may be marked")
    if len(terms)<len(term_indices):
        term_indices=term_indices[:len(terms)]
        print("Warning: term_indices and terms do not have the same length, not all terms may be marked")

    marked_html = ""
    span = "{}"
    highlight= "<mark  class='popup' style=\"background-color:{color};\">{}{}</mark>"
    indices = term_indices.copy()
    text_to_add = ""
    next_marked = indices.pop(0)
    term_index = 0
    text_should_be_marked = True if next_marked==0 else False
    next_modal_id = 0
    modals = ""


    for i,word in enumerate(split_text):
        # find the word in the text string, and get the previous whitespace
        next_word_index = text.find(word)

        # if the word isn't in the text print warning and stop marking terms, this should never happen with correct text and split_text inputs
        if next_word_index == -1:
            print("Warning: word '{}' from split_text could not be found in text, will not mark any further terms".format(word))
            break

        whitespace = text[:next_word_index]
        # remove the whitespace and word from the text to search for next time
        text = text[next_word_index+len(word):]

        # add to the text until text should be marked changes
        word =  "\"" if word == "``" else word # TODO change this in the future to not be hardcoded
        text_to_add += whitespace + word

        if next_marked!=-1 and i+1>next_marked:
            # get the next marked index if the current one has been passed
            next_marked = indices.pop(0) if len(indices)>0 else -1

        if next_marked == i+1 and not text_should_be_marked and text_to_add:
            # the current text should not be marked but the next mark should start at the next index, so this chunk needs to be finished
            # create a span with the current text
            marked_html += span.format(text_to_add)
            text_to_add = ""
            # get the next index of marked text and remember that the next term(s) should be marked
            next_marked = indices.pop(0) if len(indices)>0 else -1
            text_should_be_marked = True

        elif text_should_be_marked: # mark each term that is to be marked
            # create the popup for the term
            popups, new_modals, next_modal_id = create_popup_html(terms[term_index], language, next_modal_id)
            modals += new_modals

            # get offensiveness rating which determines the color of the highlight
            o_ratings = len(OffensivenessRating.query.filter(OffensivenessRating.term_id==terms[term_index].id).all())
            color = "var(--green)"
            if o_ratings > 3: # TODO decide on proper cutoff values
                color = "var(--orange)"
            if o_ratings > 4:
                color = "var(--red)"
        
            marked_html += whitespace + highlight.format(text_to_add.lstrip(), popups, color=color)
            term_index += 1
            text_to_add = ""

            # reset if the next index should be marked
            if next_marked == i+1:
                text_should_be_marked = True
            else:
                text_should_be_marked = False

    # add the last part of the text if there is something to add
    if text_should_be_marked and text_to_add:
        marked_html += whitespace + highlight.format(text_to_add.lstrip(), popups, color=color)
    elif text_to_add:
        marked_html += span.format(text_to_add.rstrip())

    return marked_html, modals

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
        
def create_popup_html(term, language="german", starting_modal_id=0):
    """ 
    Create the HTML of the popup for the given term. 

    Arguments:
        term: term object of the term for which to create the popup. 
        language: optional argument specifying the language of the popup, defaults to 'german' (currently only affects the alternative heading as no other parts take internationalization into account). 
        starting_modal_id (int): the starting id used for the rating and offensiveness modals corresponding to the popup of the term, the modals of the alternative terms will use ascending ids.

    Returns:
        (str) the HTML of the popup as a string
        (str) the HTML of all modals as a string
        (int) the next free id (the last modal id + 1). This can be used as the text starting_modal_id. 

    """

    #  HTML as string templates
    alternative_heading = "Alternative terms" if language=="english" else "Alternative Begriffe"
    popup = "<div class='popuptext'><h3><a href=\"{term_base_url}{term_id}\" class='term-link'>{term_term}</a>{report}</h3><p>{term_description}<p><h4>{alternative_heading}</h4>{alternative_list}</div>"
    alternative_list = "<ol>{list}</ol>"
    list_item = "<li><div class=\"alt-item-div\"><a href=\"{term_base_url}{term_id}\" class='alternative-term-link'>{term_term}</a><div class=\"popup-inline\">{alt_rating}</div><div class=\"popup-inline\">{rate}</div><div class=\"popup-inline\">{report}</div></div></li>"
    button_html = "<button type=\"button\" class=\"open-modal\" data-open=\"modal{modal_id}\">{button_text}</button>"
    offensive_modal_html = "<div class=\"modal\" id=\"modal{modal_id}\"><div class=\"modal-dialog\"><header class=\"modal-header\">Mark as offensive</header><section class=\"modal-content\"><p>Do you want to mark the term \"{term}\" as offensive?</p><button class=\"mark-offensive\" onclick=\"mark_offensive('{term_id}')\" data-close>Yes</button><button class=\"close-modal\" aria-label=\"close modal\" data-close>Cancel</button></section></div></div>"
    rating_modal_html = """ <div class="modal" id="modal{modal_id}">
        <div class="modal-dialog">
            <header class="modal-header">
            Rate "{alternative_term}" as alternative to "{original_term}"
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
    
    
    alternatives_list = []
    alt_mean_rating_list = []
    all_modals = ""

    # for each alteranative term
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
        
        # create the report and rating buttons and corresponding modals and add those to the string with all modals
        report = button_html.format(modal_id=modal_id, button_text="Mark as offensive")
        modal = offensive_modal_html.format(modal_id=modal_id, term=alternative_term_object.term, term_id=alternative_term_object.id)
        all_modals = all_modals + modal
        modal_id += 1

        rate = button_html.format(modal_id=modal_id, button_text="Rate")
        modal = rating_modal_html.format(term_id=term.id, alt_term_id=alternative_term_object.id, modal_id=modal_id, alternative_term=alternative_term_object.term, original_term=term.term)
        all_modals = all_modals + modal
        modal_id += 1

        # construct the list item for the term
        alternatives_list.append(list_item.format(rate=rate, report=report, rate_url=rate_url, term_term=alternative_term_object.term, term_base_url="https://www.machtsprache.de/term/", term_id=alternative_term_object.id, alt_rating=alt_rating, original_id=term.id, alt_id=alternative_term_object.id))
   
    
    # construct the whole list
    # sort by rating
    sorted_indices = np.argsort(np.array(alt_mean_rating_list).flatten())
    sorted_alternatives = np.array(alternatives_list)[sorted_indices[::-1]]
    
    complete_list = ""+alternative_list.format(list="".join(sorted_alternatives))

    # created report button and modal for the term
    report = button_html.format(modal_id=modal_id, button_text="Mark as offensive")
    modal = offensive_modal_html.format(modal_id=modal_id, term=term.term, term_id=term.id)
    all_modals = all_modals + modal
    modal_id += 1

    # no heading if there are no alternatives
    alternative_heading = "" if len(alternatives)==0 else alternative_heading

    # construct the whole popup and return it
    return popup.format(term_base_url="https://www.machtsprache.de/term/", term_id=term.id,report=report, term_term=term.term, term_description=term.description, alternative_heading=alternative_heading, alternative_list=complete_list), all_modals, modal_id

if __name__ == '__main__':
    app.run(debug=True)