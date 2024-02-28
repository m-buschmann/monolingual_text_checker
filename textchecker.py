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
    print(stemmed_text)

    for term in sorted_terms:
        stemmed_term = " ".join([stemmer.stem(word) for word in term.term.split()])
        
        start_pos = 0
        while True:
            print("stemmed_term", stemmed_term)
            term_index = stemmed_text.find(stemmed_term, start_pos)
            if term_index == -1:
                break
            word_index = len(stemmed_text[:term_index].split())
            end_word_index = word_index + len(stemmed_term.split())
            print(term.term, term_index, word_index, end_word_index, covered_indices)

            print([index in covered_indices for index in range(word_index, end_word_index)])
            # Check if any of the words in the term are already covered
            if not any(index in covered_indices for index in range(word_index, end_word_index)):
                print("here", term.term)
                matched_terms_details.append((word_index, end_word_index, term))
                # Mark these indices as covered
                covered_indices.update(range(word_index, end_word_index))

            print("details:", matched_terms_details)
            start_pos = term_index + len(stemmed_term)  # Update start_pos to search for next occurrence


            # Check for approximate matches for typos or different spellings
            for index, word in enumerate(stemmed_words):
                if index in covered_indices:  # Skip if index is already covered
                    continue
                possible_terms = [stemmer.stem(term.term) for term in sorted_terms]
                close_matches = difflib.get_close_matches(word, [term.term for term in sorted_terms], n=1, cutoff=0.8)
                if close_matches:
                    close_match_stemmed = close_matches[0]
                    # Find the term object from sorted_terms that matches the close_match_term_string
                    for possible_term_object in sorted_terms:
                        if stemmer.stem(term.term) == close_match_stemmed:
                            term_object = possible_term_object
                            break
                    else:
                        term_object = None

                    if term_object:
                        # Check if this term_object is already in matched_terms_details based on object identity
                        for matched_term in matched_terms_details:
                            #print(matched_term)
                            if term_object == matched_term[2]:  # matched_term[2] is the term object
                                # Check if the index range of the current word overlaps with the matched term
                                if not any(index in covered_indices for index in range(matched_term[0], matched_term[1])):
                                    matched_terms_details.append((index, index + 1, term_object))
                                    covered_indices.add(index)
                                break  # Exit the loop as we found a match
                        else:
                            # If term_object is not found in matched_terms_details or does not overlap, add it
                            matched_terms_details.append((index, index + 1, term_object))
                            covered_indices.add(index)
    print("details2:",matched_terms_details)
    # Sort matched terms by their start index to ensure correct order
    matched_terms_details.sort(key=lambda x: x[0])

    # Generate the final split text in the correct order, merging terms as needed
    split_text, sensitive_indices, sensitive_terms = [], [], []
    last_index = 0
    reduce_index_by = 0
    for start_index, end_index, term in matched_terms_details:
        
        # Add words before the matched term
        split_text.extend(words[last_index:start_index])
        # Add the matched term itself
        split_text.append(" ".join(words[start_index:end_index]))
        # Update sensitive_indices to only include the start index of the term
        sensitive_indices.append(start_index-reduce_index_by)
        sensitive_terms.append(term)
        last_index = end_index
        reduce_index_by += end_index-1-start_index
    # Add any remaining words after the last matched term
    split_text.extend(words[last_index:])
    
    print(sensitive_indices, sensitive_terms, split_text)
    return sensitive_indices, sensitive_terms, split_text



def create_marked_html(text, term_indices):
    """
    Generates HTML with sensitive terms highlighted, including an additional white space after highlights,
    and considering punctuation.
    
    Parameters:
    - text: List of strings, representing words and punctuation from the original text.
    - term_indices: Indices of the sensitive terms within the text list to be marked.

    Returns:
    - marked_html: HTML string with sensitive terms highlighted, and extra spaces after highlights.
    """

    marked_html = ""
    i = 0
    while i < len(text):
        word = text[i]
        if i in term_indices:
            # Highlight this word
            marked_html += "<mark>{}</mark>".format(word)  # Remove the space after </mark> here
            if i + 1 < len(text) and text[i + 1] in ",.!?;:":
                marked_html += "{}".format(text[i + 1])  # Directly append punctuation without a space
                if i + 2 < len(text) and text[i + 2] not in ",.!?;:":
                    marked_html += " "  # Add a space after punctuation if next term is not punctuation
                i += 1  # Increment to skip the punctuation since it's already handled
            else:
                marked_html += " "  # Add space after the highlighted term if not followed by punctuation
        else:
            # For non-highlighted terms, just add the word and a space (if not punctuation)
            marked_html += word
            if i + 1 < len(text) and text[i + 1] not in ",.!?;:":
                marked_html += " "  # Only add space if the next term is not punctuation
            
        i += 1  # Move to the next word

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