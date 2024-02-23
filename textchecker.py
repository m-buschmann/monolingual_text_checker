from flask import Flask, request, render_template
from sqlalchemy import func, desc, select
import nltk
from nltk.stem import SnowballStemmer

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
language_map = {'de': 'german', 'en': 'english'}

def find_sensitive_terms(text, language_code='de'):
    # Convert ISO language code to SnowballStemmer's expected language name
    stemmer_language = language_map.get(language_code)

    # Initialize the stemmer based on the resolved language name
    stemmer = SnowballStemmer(stemmer_language)

    # Normalize and tokenize the input text
    words = nltk.word_tokenize(text.lower())
    stemmed_words = [stemmer.stem(word) for word in words]

    sensitive_indices = []
    sensitive_terms = []

    for index, word in enumerate(stemmed_words):
        # consider the language when filtering terms
        term = Term.query.filter(Term.language == language_code, func.lower(Term.term) == func.lower(word)).first()
        if term:
            sensitive_indices.append(index)
            sensitive_terms.append(term.term)  #TODO: Returns the term as stored in the database, is that what we want?

    # TODO: delete next line later, it's just to test the output
    # check that everything works:
    print(sensitive_indices, sensitive_terms)
    return sensitive_indices, sensitive_terms


@app.route('/submit', methods=['POST'])
def submit():
    user_text = request.form['user_text']
    # TODO: when we have the language button, we can use this line to get the language
    #language = request.form.get('language', 'german') # default to german if no language set
    
    # Find sensitive terms in the user text
    indices, terms = find_sensitive_terms(user_text) #, language)
    
    # when we have the html, we can use this line to return the results
    #return render_template("results.html", user_text=user_text, indices=indices, terms=terms)
    return render_template("home.html", user_text=user_text)

if __name__ == '__main__':
    app.run(debug=True)
