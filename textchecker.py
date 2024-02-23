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

if __name__ == '__main__':
    app.run(debug=True)
