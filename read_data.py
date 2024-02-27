"""from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from models import db, Term, AlternativeTerm, AlternativeRating, OffensivenessRating
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensitive_terms.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def insert_data():
    with open('terms.json', 'r', encoding='utf-8') as terms_file:
        terms_data = json.load(terms_file)
        value_to_id = {item['value']: item['id'] for item in terms_data}

    with open('modified_data.json', 'r', encoding='utf-8') as modified_file:
        data = json.load(modified_file)
        
        # Insert terms
        for item in data:
            language = "german" if item['lemma_lang'] == 'de' else "english"
            term_id = value_to_id.get(item['lemma'])
            if term_id:
                try:
                    term = Term(
                        id=term_id,
                        term=item['lemma'],
                        description=item['definition'],
                        language=language,
                        alternatives_list=json.dumps(item.get('translations', []))
                    )
                    db.session.add(term)
                    db.session.add(OffensivenessRating(term_id=term.id, rating=None))
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()

        # After inserting terms, create a dictionary for quick access to terms by name
        terms_dict = {term.term: term for term in Term.query.all()}

        # Identify alternative terms based on shared translations
        for item in data:
            if item['lemma'] in terms_dict and 'translations' in item:
                original_term = terms_dict[item['lemma']]
                for translation in item['translations']:
                    for other_item in data:
                        if translation in other_item.get('translations', []) and other_item['lemma'] != item['lemma'] and other_item['lemma'] in terms_dict:
                            alternative_term = terms_dict[other_item['lemma']]
                            # Avoid duplicates and self-references
                            if original_term.id != alternative_term.id and not AlternativeTerm.query.filter_by(original_term_id=original_term.id, alternative_term_id=alternative_term.id).first():
                                db.session.add(AlternativeTerm(original_term_id=original_term.id, alternative_term_id=alternative_term.id))
                                db.session.add(AlternativeRating(term_id=original_term.id, alternative_term_id=alternative_term.id, rating=None))
                                db.session.add(AlternativeTerm(original_term_id=alternative_term.id, alternative_term_id=original_term.id))
                                db.session.add(AlternativeRating(term_id=alternative_term.id, alternative_term_id=original_term.id, rating=None))
                db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        insert_data()"""
        
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from models import db, Term, AlternativeTerm, AlternativeRating, OffensivenessRating
import json
from itertools import count

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensitive_terms.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def insert_data():
    with open('terms.json', 'r', encoding='utf-8') as terms_file:
        terms_data = json.load(terms_file)
        value_to_id = {item['value']: item['id'] for item in terms_data}

    with open('modified_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

        # Initialize counter for new IDs
        initial_id_num = 1
        id_counter = count(initial_id_num)

        # Function to generate new IDs
        def generate_new_id():
            return f"{next(id_counter):020}"
        
        # Insert terms
        for item in data:
            language = "german" if item['lemma_lang'] == 'de' else "english"
            term_id = value_to_id.get(item['lemma'])

            # Generate a new ID if none is found
            if term_id is None:
                while True:
                    potential_new_id = generate_new_id()
                    if not Term.query.filter_by(id=potential_new_id).first():
                        term_id = potential_new_id
                        break

            try:
                term = Term(
                    id=term_id,
                    term=item['lemma'],
                    description=item['definition'],
                    language=language,
                    alternatives_list=json.dumps(item.get('translations', []))
                )
                db.session.add(term)
                db.session.commit()
            except IntegrityError as e:
                print(f"IntegrityError: {e}")
                db.session.rollback()



        # After inserting terms, create a dictionary for quick access to terms by name
        terms_dict = {term.term: term for term in Term.query.all()}

        # Identify alternative terms based on shared translations
        for item in data:
            if item['lemma'] in terms_dict:
                original_term = terms_dict[item['lemma']]
                for translation in item.get('translations', []):
                    for other_item in data:
                        if translation in other_item.get('translations', []) and other_item['lemma'] != item['lemma'] and other_item['lemma'] in terms_dict:
                            alternative_term = terms_dict[other_item['lemma']]
                            # Use the id from terms_dict (which is now correctly linked to terms.json IDs)
                            original_term_id = original_term.id
                            alternative_term_id = alternative_term.id
                            # Avoid duplicates and self-references
                            if original_term_id != alternative_term_id and not AlternativeTerm.query.filter_by(original_term_id=original_term_id, alternative_term_id=alternative_term_id).first():
                                db.session.add(AlternativeTerm(original_term_id=original_term_id, alternative_term_id=alternative_term_id))
                                db.session.add(AlternativeTerm(original_term_id=alternative_term_id, alternative_term_id=original_term_id))
                            db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        insert_data()

"""from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from models import db, Term, AlternativeTerm, AlternativeRating, OffensivenessRating
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensitive_terms.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def insert_data():
    # Load terms.json into a dictionary for quick lookup.
    with open('terms.json', 'r', encoding='utf-8') as file:
        terms_data = json.load(file)
        # Create a mapping of 'value' to its entire item for quick access.
        terms_dict = {item['value']: item for item in terms_data}
        #print(terms_dict.keys())

    # Load modified_data.json.
    with open('modified_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        #print(data[0])

    # Iterate over each item in modified_data.json to find and insert data.
    for item in data:
        lemma = item['lemma']
        # Attempt to find the corresponding entry in terms_dict using lemma.
        if lemma in terms_dict:
            #print ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            term_details = terms_dict[lemma]
            print(term_details)
            # Determine the language and select the appropriate definition.
            language = "german" if item['lemma_lang'] == 'de' else "english"
            description_key = "langB" if language == "german" else "langA"
            description = term_details.get(description_key, "")

            # Prepare alternatives list, if available.
            alternatives_list = json.dumps(item.get('translations', []))

            try:
                # Insert data into the database.
                term = Term(
                    id=term_details['id'],
                    term=lemma,
                    description=description,
                    language=language,
                    alternatives_list=alternatives_list
                )
                db.session.add(term)
                db.session.add(OffensivenessRating(term_id=term.id, rating=None))
                db.session.commit()
            except IntegrityError:
                print(f"Integrity error for term: {lemma}")
                db.session.rollback()
        else:
            print(f"Error: Lemma '{lemma}' not found in terms.json")



        # After inserting terms, create a dictionary for quick access to terms by name
        terms_dict = {term.term: term for term in Term.query.all()}

        # Identify alternative terms based on shared translations
        for item in data:
            if item['lemma'] in terms_dict:
                original_term = terms_dict[item['lemma']]
                for translation in item.get('translations', []):
                    for other_item in data:
                        if translation in other_item.get('translations', []) and other_item['lemma'] != item['lemma'] and other_item['lemma'] in terms_dict:
                            alternative_term = terms_dict[other_item['lemma']]
                            # Avoid duplicates and self-references
                            if original_term.id != alternative_term.id and not AlternativeTerm.query.filter_by(original_term_id=original_term.id, alternative_term_id=alternative_term.id).first():
                                db.session.add(AlternativeTerm(original_term_id=original_term.id, alternative_term_id=alternative_term.id))
                                db.session.add(AlternativeRating(term_id=original_term.id, alternative_term_id=alternative_term.id, rating=None))
                                db.session.add(AlternativeTerm(original_term_id=alternative_term.id, alternative_term_id=original_term.id))
                                db.session.add(AlternativeRating(term_id=alternative_term.id, alternative_term_id=original_term.id, rating=None))
                db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        insert_data()"""



