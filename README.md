# Monolingual Text Checker

Expand the text checker on macht.sprache by adding a monolingual text checking tool to highlight sensitive terms and provide alternatives and additional information within the same language.

## Installation & Usage

You can either access our monolingual text checker via this link: http://vm455.rz.uni-osnabrueck.de/user031/textchecker.wsgi/
(the only requirement for this is that you need to be in the Wifi of the university of Osnabrück, you can also use a VPN)

To set up the Monolingual Text Checker on your local machine, follow these steps:
1. Clone the project repository to your local machine and navigate to the project directory.
2. Ensure that Python is installed on your system, then install the required Python packages listed in requirements.txt by running 'pip install -r requirements.txt'

Accessing the Monolingual text checker from your local machine:
1. Run the textchecker.py script.
2. Access the application through a web browser by navigating to the appropriate URL.

Using the Monolingual text checker: 
1. Enter the text you want to check into the provided input field.
2. Select the desired language for checking, or choose the auto-detect option.
3. Click the "Check" button to initiate the text checking process.
4. View the results: Sensitive terms will be highlighted. Hover over these terms to see their descriptions and alternative suggestions.
5. Rate the alternative terms based on how good of an alternative they are for the original term on a scale from 1-5.
6. If a term is offensive, you can mark it accordingly. Multiple offensive markings will result in the highlight changing color, indicating the severity of the offense.

## Files
### instance/sensitive_terms.sqlite:
the database, containing tables for the sensitive terms

### static/style.css: 
    style classes for the front end

### templates/home.html: 
    contains the html code for the website.Builds with options to auto-detect language or choose between English and German. Users can submit text to be analyzed, edit their input, and view highlighted sensitive terms via dynamically generated modal popups. JavaScript is used for form submission handling, scrolling synchronization between the textarea and a highlighted backdrop, and for the display and interaction with modal popups, including rating alternatives for flagged terms.

### templates/textarea.html: 
    builds the text box where users input their text

### models.py: 
    defines a set of database models for the Flask application using SQLAlchemy ORM. It includes four models: AlternativeTerm, OffensivenessRating, AlternativeRating, and Term, structured to support a system for managing terms, their alternatives, and ratings regarding their offensiveness or appropriateness.

### modified_data.json: 
    contains data of the terms from macht.sprache, with  lemma, lemma_lang, definition, author, date, guidelines, relatedterms, translations, id. "lemma", "translations", "lemma_lang" used to build the database.

### terms.json: 
    contains data of the terms from macht.sprache, with id, relatedTerms, creator, createdAt, value, racial justice, variants, lang, commentCount, adminComment, definition, adminTags, guidelines. "id" and "definition" used to build the database. 

### read_data.py: 
    Flask application that facilitates the management of sensitive terms using an SQLite database. It features functionality to import terms from two JSON files, `terms.json` and `modified_data.json`, to insert or update terms, link alternative terms, and handle their offensiveness and appropriateness ratings. The `insert_data` function processes the JSON data, ensuring terms are uniquely identified, alternatives are correctly linked, and language-specific details are accurately maintained. 

### requirements.txt: 
    list of nececesary libraries

### textchecker.py: 
    establishes a Flask web application to handle the text input. Employs NLTK for natural language processing to detect sensitive terms, SQLAlchemy for database interactions, and custom logic for language detection and processing user inputs. Features of the application include:

    - Initialization of an SQLite database to store terms and their alternatives.
    - Routes for rendering a home page, submitting texts for analysis, and handling user feedback on term offensiveness and alternative ratings.
    - Functions for automatic language detection, identification of sensitive terms using stemming, and creation of interactive HTML content to highlight sensitive terms and present alternatives.

## Important decisions made during the project implementation
- Rating of alternative terms: We decided to deviate from the way ratings are handled on the macht.sprache website, trying to implement a more intuitive rating - a number between 1-5 - which the user can see directly next to the altrnative terms suggested, when hovering over the highlighted senstitive terms.
- Rating a term as offensive: We decided to add a possibility of rating a term as offensive, to provide users with a way to flag terms that they find offensive or inappropriate. In our implementation we coded hard boundaries (>3 changes highlight to light red, >4 changes hightlight to red). If this feature would be integrated into the macht.sprache website, the highlight boundaries should be calculated with ratios, based on how many users the website has.
- Which terms are detected in which language? We decided to detect both English and German terms within English text, as well as both English and German terms within German text. This approach increases the likelihood of detecting all sensitive terms, considering the prevalent use of English words in the German language.
- Order of related terms: ordered after the rating of users, best alternative at the top



This is where we planned our project, handled & distributed ToDos: https://github.com/users/Cl4ryty/projects/7/views/2
