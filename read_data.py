from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from models import db, Term, AlternativeTerm, AlternativeRating, OffensivenessRating
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensitive_terms.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def insert_data():
    with open('modified_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        # Insert terms
        for item in data:
            language = "german" if item['lemma_lang'] == 'de' else "english"
            try:
                term = Term(
                    id=item['id'],
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
        insert_data()


