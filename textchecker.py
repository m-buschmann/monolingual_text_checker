




from flask import Flask, request, render_template
from sqlalchemy import func, desc, select
import nltk
from nltk.stem import SnowballStemmer
import nh3

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

# Map ISO language codes to SnowballStemmer's expected full language names
language_map = {'german': 'de', 'english': 'en'}

@app.route('/submit', methods=['POST'])
def submit():
    user_text = request.form['user_text']
    language = request.form.get('language', 'german') # default to german if no language set
    
    # sanitize input
    clean_text = nh3.clean(user_text)

    # Find sensitive terms in the user text
    indices, terms = find_sensitive_terms(clean_text, language)

    marked_html = create_marked_html(clean_text.split(" "), indices)
    
    # when we have the html, we can use this line to return the results
    return render_template("textarea.html", user_text=clean_text, indices=indices, terms=terms, marked_html=marked_html)

def find_sensitive_terms(text, language='german'):
    """
    Identifies and returns indices and the original forms of sensitive terms found in the input text,
    based on a list of sensitive terms stored in a database. 

    Parameters:
    - text (str): The input text in which to find sensitive terms.
    - language_code (str): ISO language code indicating the language of the input text. Defaults to 'de' (German).
    
    Returns:
    - tuple: A tuple containing two elements:
        1. A list of indices (int) where sensitive terms were found in the input text.
        2. A list of the original forms (str) of the sensitive terms as they are stored in the database.
    
    Note:
    - assumes that sensitive terms in the database are stored in their stemmed form and lowercase    
    """
    # Convert ISO language code to SnowballStemmer's expected language name
    #stemmer_language = language_map.get(language_code)

    # Initialize the stemmer based on the resolved language name
    stemmer = SnowballStemmer(language)

    # Normalize and tokenize the input text
    words = nltk.word_tokenize(text.lower())
    stemmed_words = [stemmer.stem(word) for word in words]

    sensitive_indices = []
    sensitive_terms = []

    for index, word in enumerate(stemmed_words):
        # consider the language when filtering terms
        term = Term.query.filter(Term.language == language_map.get(language), func.lower(Term.term) == func.lower(word)).first()
        if term:
            sensitive_indices.append(index)
            sensitive_terms.append(term)
            
    # TODO: delete next line later, it's just to test the output
    # check that everything works:
    print(sensitive_indices, sensitive_terms)
    return sensitive_indices, sensitive_terms

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
            # text should be marked next but isn't currently
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
