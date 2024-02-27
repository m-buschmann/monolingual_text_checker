from flask import Flask, request, render_template
from sqlalchemy import func, desc, select
import nltk
from nltk.stem import SnowballStemmer
import nh3
nltk.download('punkt')

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

    marked_html = create_marked_html(split_text, indices, terms)
    
    # when we have the html, we can use this line to return the results
    return render_template("textarea.html", user_text=" ".join(split_text), indices=indices, terms=terms, marked_html=marked_html)

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
            sensitive_terms.append(term)
            # Append non-matched words to split_text before the matched term
            split_text.extend(words[current_index:word_start_index])
            # Append the matched term as a single entry
            split_text.append(" ".join(words[word_start_index:word_end_index]))
            current_index = word_end_index  # Update current_index to continue after the matched term

    # Append any remaining words after the last matched term
    split_text.extend(words[current_index:])

    print(sensitive_indices, sensitive_terms, split_text)
    return sensitive_indices, sensitive_terms, split_text

def create_marked_html(text, term_indices, terms):
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
    highlight= "<mark  class='popup'>{}<div class='popuptext'><h3>{}</h3><p>{}<p><h4>Alternative terms</h4>{}</div></mark>"
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
            term_index += 1
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
            marked_html += highlight.format(text_to_add.rstrip(), terms[term_index].term, terms[term_index].description, "todo terms")+" "
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
        

if __name__ == '__main__':
    app.run(debug=True)
