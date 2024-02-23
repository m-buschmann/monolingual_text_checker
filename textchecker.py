from flask import Flask, request, render_template
from sqlalchemy import func, desc, select

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
    return render_template("home.html", user_text=user_text)

def create_marked_html(text, indices):
    """
    text: list of strings, can be turned into a text string by appending elements separated by a space
    indices: indices of the sensitive terms within the text list that are to be marked

    returns:
    marked_html: html containing the text in the format needed to display it with highlights
    """

    marked_html = ""
    span = "<span>{}</span>"
    highlight= "<button class='style_sensitive_word_highlight'>{}</button>"

    text_to_add = text[0] + " "
    next_marked = indices.pop(0)
    text_should_be_marked = True if next_marked==0 else False
    for i,word in enumerate(text[1:]):
        print("i", i, "next", next_marked, "should be marked", text_should_be_marked,"word", word)

        if next_marked == i+1 and not text_should_be_marked:
            # text should be marked next but isn't currently
            # create a span with the current text
            marked_html += span.format(text_to_add.rstrip())
            text_to_add = ""
            next_marked = indices.pop(0) if len(indices)>0 else -1
            text_should_be_marked = True
        elif next_marked != i+1 and text_should_be_marked:
            # text is currently marked but should not be for the next word
            # create highlight
            marked_html += highlight.format(text_to_add.rstrip())
            text_to_add = ""
            text_should_be_marked = False

        if next_marked!=-1 and i+2>next_marked:from flask import Flask, request, render_template
from sqlalchemy import func, desc, select

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
    return render_template("home.html", user_text=user_text)

def create_marked_html(text, indices):
    """
    inputs
        text: list of strings, can be turned into a text string by appending elements separated by a space
        indices: indices of the sensitive terms within the text list that are to be marked

    returns:
        marked_html: html containing the text in the format needed to display it with highlights
    """

    marked_html = ""
    span = "<span>{}</span>"
    highlight= "<button class='style_sensitive_word_highlight'>{}</button>"

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
            marked_html += span.format(text_to_add.rstrip())
            text_to_add = ""
            next_marked = indices.pop(0) if len(indices)>0 else -1
            text_should_be_marked = True
        elif next_marked != i+1 and text_should_be_marked and text_to_add:
            # text is currently marked but should not be for the next word
            # create highlight
            marked_html += highlight.format(text_to_add.rstrip())
            text_to_add = ""
            text_should_be_marked = False


    # add the last part of the text if there is something to add
    if text_should_be_marked and text_to_add:
        marked_html += highlight.format(text_to_add.rstrip())
    elif text_to_add:
        marked_html += span.format(text_to_add.rstrip())

    return marked_html
        

if __name__ == '__main__':
    app.run(debug=True)
