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
    """
    Inserts terms from a JSON file into a SQLite database, managing both new and existing entries.

    This function reads terms and their details from 'terms.json' and 'modified_data.json', 
    then inserts or updates these terms in a SQLite database. It assigns unique identifiers to 
    new terms, links alternative terms based on shared translations, and handles language-specific 
    definitions appropriately. If a term's definition is missing, a default message is used. The 
    function also ensures that alternative term relationships are symmetric and avoids duplicates.

    Parameters:
    - None: This function does not take any parameters.

    Files read:
    - 'terms.json': Contains initial terms with IDs, values, and definitions.
    - 'modified_data.json': Contains terms to be inserted, including lemma, translations, and language.

    Database operations:
    - Creates or updates entries in the `Term` table with terms' lemmas, descriptions, languages, 
      and alternatives list.
    - Inserts new relationships into the `AlternativeTerm` table, ensuring that each relationship 
      is represented both ways (symmetrically) between terms.
    - Checks for existing terms and relationships to prevent duplicates.
    - Uses a counter to generate new unique IDs for terms that do not already have one.


    Requires:
    - A Flask application context to be active, with a configured SQLAlchemy instance pointing to 
      the target SQLite database.
    - The `models.py` file should define the SQLAlchemy models `Term`, `AlternativeTerm`, `AlternativeRating`, 
      and `OffensivenessRating`.
    """
    with open('terms.json', 'r', encoding='utf-8') as terms_file:
        terms_data = json.load(terms_file)
        value_to_id = {item['value']: item['id'] for item in terms_data}
        value_to_def = {item['value']: item['definition'] for item in terms_data}
        
    with open('modified_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

        # Initialize counter for new IDs
        initial_id_num = 1
        id_counter = count(initial_id_num)

        # Function to generate new IDs
        def generate_new_id():
            return f"{next(id_counter):020}"
            # Step 1: Collect translation relationships
        
        translation_to_terms = {}  # Maps a translation to all terms that include it
        for item in data:
            for translation in item.get('translations', []):
                if translation not in translation_to_terms:
                    translation_to_terms[translation] = set()
                translation_to_terms[translation].add(item['lemma'])
        
        # Convert sets to lists for JSON serialization
        term_to_alternatives = {item['lemma']: [] for item in data}
        for translation, terms in translation_to_terms.items():
            for term in terms:
                # Exclude the term itself from its alternatives list
                term_to_alternatives[term].extend([t for t in terms if t != term])
        
        # Ensure unique entries
        for term, alternatives in term_to_alternatives.items():
            term_to_alternatives[term] = list(set(alternatives))

        # Step 2: Update terms with alternatives list
        # Insert terms
        for item in data:
            language = "german" if item['lemma_lang'] == 'de' else "english"
            term_id = value_to_id.get(item['lemma'])
            
            # Check if term definition exists and is not None
            term_def = value_to_def.get(item['lemma'], None)
            if term_def:
                definition_key = "langB" if language == "german" else "langA"
                definition = term_def.get(definition_key, "")
            else:
                definition = "No definition available"

            # Generate a new ID if none is found
            if term_id is None:
                while True:
                    potential_new_id = generate_new_id()
                    if not Term.query.filter_by(id=potential_new_id).first():
                        term_id = potential_new_id
                        break
            # Update to use collected relationships for alternatives_list
            try:
                alternatives_list = json.dumps(term_to_alternatives[item['lemma']], ensure_ascii=False)
                term = Term(
                    id=term_id,
                    term=bytes(item['lemma'], "utf-8").decode("utf-8"), 
                    description= bytes(definition, "utf-8").decode("utf-8"), 
                    language=language,
                    alternatives_list=alternatives_list
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

