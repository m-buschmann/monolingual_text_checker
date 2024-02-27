from flask import Flask, request, render_template
from sqlalchemy import func, desc, select
import nltk
from nltk.stem import SnowballStemmer
import nh3
nltk.download('punkt')
from read_data import insert_data
import os
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

    marked_html = create_marked_html(split_text, indices)
    
    # when we have the html, we can use this line to return the results
    return render_template("textarea.html", user_text=clean_text, indices=indices, terms=terms, marked_html=marked_html)

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
    stemmer = SnowballStemmer(language)
    words = nltk.word_tokenize(text)
    words_lower = [word.lower() for word in words]
    stemmed_words = [stemmer.stem(word) for word in words_lower]
    stemmed_text = " ".join(stemmed_words)
    
    # Fetch terms from the database and sort them by word count (descending)
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



                # Check for approximate matches for typos or different spellings
                for index, word in enumerate(stemmed_words):
                    if index in covered_indices:  # Skip if index is already covered
                        continue

                    close_matches = difflib.get_close_matches(word, [term.term for term in sorted_terms], n=1, cutoff=0.8)
                    if close_matches:
                        close_match_term_string = close_matches[0]
                        # Find the term object from sorted_terms that matches the close_match_term_string
                        for possible_term_object in sorted_terms:
                            if possible_term_object.term == close_match_term_string:
                                term_object = possible_term_object
                                break
                        else:
                            term_object = None

                        if term_object:
                            # Check if this term_object is already in matched_terms_details based on object identity or other unique identifier
                            for matched_term in matched_terms_details:
                                if term_object == matched_term[2]:  # Assuming matched_term[2] is the term object
                                    # Check if the index range of the current word overlaps with the matched term
                                    if not any(index in covered_indices for index in range(matched_term[0], matched_term[1])):
                                        matched_terms_details.append((index, index + 1, term_object))
                                        covered_indices.add(index)
                                    break  # Exit the loop as we found a match
                            else:
                                # If term_object is not found in matched_terms_details or does not overlap, add it
                                matched_terms_details.append((index, index + 1, term_object))
                                covered_indices.add(index)

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

    marked_html = ""
    skip_next = False  # Flag to skip the next item if it's punctuation immediately after a highlighted word

    for i, word in enumerate(text):
        if skip_next:
            # Skip this iteration if the previous word was highlighted and followed by punctuation
            skip_next = False
            continue

        if i in term_indices or (i + 1 in term_indices and word[-1] in ",.!?;:"):
            # Highlight this word and, if the next item is punctuation, include it in the highlight
            if i + 1 < len(text) and text[i + 1] in ",.!?;:":  # Check if next is punctuation
                marked_html += "<mark>{}{}</mark> ".format(word, text[i + 1])
                skip_next = True  # Skip the next item since it's punctuation included in the current highlight
            else:
                marked_html += "<mark>{}</mark> ".format(word)
        else:
            marked_html += "{} ".format(word)

    return marked_html.strip()

    """if len(term_indices) == 0:
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

    return marked_html.rstrip()"""

    """marked_html = ""
        for i, word in enumerate(text):
            if i in term_indices:
                # Highlight this word
                marked_html += "<mark>{}</mark> ".format(word)
            else:
                marked_html += "{} ".format(word)

        return marked_html.strip()"""       

if __name__ == '__main__':
    app.run(debug=True)