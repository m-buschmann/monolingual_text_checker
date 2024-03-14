# Monolingual Text Checker

Project Idea: Expanding the text checker on macht.sprache by adding a monolingual text checking tool. The goal is to highlight sensitive terms within a users text and provide alternatives and additional information within the same language.  
  
<img width="836" alt="image" src="https://github.com/m-buschmann/monolingual_text_checker/assets/61427823/ec6a2479-7518-408c-a2c5-3d216eb462bc">

## Table of Contents
- Installation & Usage
  - Local installation
  - Using the Monolingual text checker
- File structure
- Important decisions made during the project implementation
- Limitations
- License
- Project plan

## Installation & Usage

To use the monolingual text checker you can either install and run it locally or access it via the following link from within the network of the University of Osnabrück (e.g. connected to the university's WiFi or using the university VPN): http://vm455.rz.uni-osnabrueck.de/user031/textchecker.wsgi/

### Local installation
To set up the Monolingual Text Checker on your local machine, follow these steps:
1. Clone the project repository to your local machine and navigate to the project directory. 
   ```
   git clone https://github.com/m-buschmann/monolingual_text_checker.git
   cd monolingual_text_checker
   ```
   
2. Ensure that Python is installed on your system, if it is not already installed, follow the [official installation instructions](https://wiki.python.org/moin/BeginnersGuide/Download). The Monolingual Text Checker was tested with Python 3.10. 
3. Set up a new virtual environment (this is optional but strongly recommended) and activate it
   ```
   conda create -n text_checker
   conda activate text_checker
   ```
5. Install the required Python packages listed in ```requirements.txt```
   ```
   pip install -r requirements.txt
   ```


Accessing the Monolingual text checker from your local machine:
1. Run the textchecker.py script.
   ```
   flask --app textchecker.py run
   ```
3. Access the application through a web browser by navigating to the appropriate URL (which is printed in the terminal in which the the textchecker was started).


### Using the Monolingual text checker
1. Enter the text you want to check into the provided input field.
2. Select the desired language for checking, or choose the auto-detect option.
3. Click the "Check" button to initiate the text checking process.
4. View the results: Sensitive terms will be highlighted. Hover over these terms to see their descriptions and alternative suggestions.
5. Rate the alternative terms based on how good of an alternative they are for the original term on a scale from 1-5.
6. If a term is offensive, you can mark it accordingly. Multiple offensive markings will result in the highlight changing color, indicating the severity of the offense.

<img width="836" alt="image" src="https://github.com/m-buschmann/monolingual_text_checker/assets/61427823/868971be-42d1-431d-865d-d670b08ff682">
<img width="836" alt="image" src="https://github.com/m-buschmann/monolingual_text_checker/assets/61427823/57e40d6b-8aaa-4769-a2df-da288d9dd6ed">


## File structure
-  ```instance/sensitive_terms.sqlite```:  
          the database, containing tables for the sensitive terms

-  ```static/style.css```:  
    style classes for the front end

-  ```templates/home.html```:  
    contains the html code for the website.Builds with options to auto-detect language or choose between English and German. Users can submit text to be analyzed, edit their input, and view highlighted sensitive terms via dynamically generated modal popups. JavaScript is used for form submission handling, scrolling synchronization between the textarea and a highlighted backdrop, and for the display and interaction with modal popups, including rating alternatives for flagged terms.

-  ```templates/textarea.html```:  
    builds the text box where users input their text

-  ```LICENSE```:  
    contains the license 
  
-  ```models.py```:  
    defines a set of database models for the Flask application using SQLAlchemy ORM. It includes four models: AlternativeTerm, OffensivenessRating, AlternativeRating, and Term, structured to support a system for managing terms, their alternatives, and ratings regarding their offensiveness or appropriateness.

-  ```modified_data.json```:  
    contains data of the terms from macht.sprache, with  lemma, lemma_lang, definition, author, date, guidelines, relatedterms, translations, id. "lemma", "translations", "lemma_lang" used to build the database.

-  ```terms.json```:  
    contains data of the terms from macht.sprache, with id, relatedTerms, creator, createdAt, value, racial justice, variants, lang, commentCount, adminComment, definition, adminTags, guidelines. "id" and "definition" used to build the database. 

-  ```read_data.py```:  
    Flask application that facilitates the management of sensitive terms using an SQLite database. It features functionality to import terms from two JSON files, `terms.json` and `modified_data.json`, to insert or update terms, link alternative terms, and handle their offensiveness and appropriateness ratings. The `insert_data` function processes the JSON data, ensuring terms are uniquely identified, alternatives are correctly linked, and language-specific details are accurately maintained. 

-  ```requirements.txt```:  
    list of necessary libraries

-  ```textchecker.py```:  
    establishes a Flask web application to handle the text input. Employs NLTK for natural language processing to detect sensitive terms, SQLAlchemy for database interactions, and custom logic for language detection and processing user inputs. Features of the application include:

    - Initialization of an SQLite database to store terms and their alternatives.
    - Routes for rendering a home page, submitting texts for analysis, and handling user feedback on term offensiveness and alternative ratings.
    - Functions for automatic language detection, identification of sensitive terms using stemming, and creation of interactive HTML content to highlight sensitive terms and present alternatives.

-  ```textchecker.wsgi```:
  contains the wsgi file to run the application on a server

## Important decisions made during the project implementation
- Rating of alternative terms: We decided to deviate from the way ratings are handled on the macht.sprache website, trying to implement a more intuitive rating - a number between 1-5 - which the user can see directly next to the alternative terms suggested, when hovering over the highlighted sensitive terms.
- Rating a term as offensive: We decided to add a possibility of rating a term as offensive, to provide users with a way to flag terms that they find offensive or inappropriate. In our implementation we coded hard boundaries (>3 changes highlight to light red, >4 changes highlight to red). If this feature would be integrated into the macht.sprache website, the highlight boundaries should be calculated with ratios, based on how many users the website has.
- Which terms are detected in which language? We decided to detect both English and German terms within English text, as well as both English and German terms within German text. This approach increases the likelihood of detecting all sensitive terms, considering the prevalent use of English words in the German language.
- Order of related terms: ordered after the rating of users, best alternative at the top

## Limitations
- The word stemmer is very basic (the NLTK SnowballStemmer). It sometimes produces incorrect word stems, leading to mismatching sensitive terms.
- The marking of sensitive terms as offensive is done by users. This could lead to terms that are generally regarded as politically correct marked as red, and expects some degree of knowledge and interpretation of the users.
- We used the database from macht.sprache. Some of the terms are censored by "***". Those terms cannot be detected by our algorithm. 
- This project uses server-side processing, possibly leading to security issues.
- Spell checking only works partially and on a basic level.
  
## License
Copyright 2024 Paula Meyer, Fabia Klausing, Hannah Köster, Mathilda Buschmann

Licensed under the GLP License, Version 3.0 (the "LICENSE"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

GPLv3: https://www.gnu.org/licenses/gpl-3.0.en.html

## Project plan
This is where we planned our project, handled & distributed To-Dos: https://github.com/users/Cl4ryty/projects/7/views/2


