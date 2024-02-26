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
        # First, insert all terms
        for item in data:
            if item['lemma_lang'] == 'de':
                language_item = "german"
            else:
                language_item = "english"
            alternatives_json = json.dumps(item.get('translations', []))
            try:
                term = Term(
                    id=item['id'],
                    term=item['lemma'],
                    description=item['definition'],
                    language=language_item,
                    alternatives_list=alternatives_json
                )
                db.session.add(term)
                
                # Immediately create an OffensivenessRating entry with an empty rating for this term
                offensiveness_rating = OffensivenessRating(term_id=term.id, rating=None)
                db.session.add(offensiveness_rating)

                db.session.commit()
            except IntegrityError:
                print(f"Ignoring duplicate term: {item['lemma']}")
                db.session.rollback()

        # After all terms are inserted, link alternative terms and create ratings in both directions
        for item in data:
            original_term = Term.query.filter_by(term=item['lemma']).first()
            if original_term:
                for alt_term_name in item.get('translations', []):
                    alt_term = Term.query.filter_by(term=alt_term_name).first()
                    if alt_term and original_term.id != alt_term.id:  # Check to ensure not linking term to itself
                        # Create or verify link from original to alternative
                        existing_link = AlternativeTerm.query.filter_by(original_term_id=original_term.id, alternative_term_id=alt_term.id).first()
                        if not existing_link:
                            alt_link = AlternativeTerm(original_term_id=original_term.id, alternative_term_id=alt_term.id)
                            db.session.add(alt_link)
                            # Create a corresponding entry in appropriate_alternative_ratings
                            new_rating = AlternativeRating(term_id=original_term.id, alternative_term_id=alt_term.id, rating=None)
                            db.session.add(new_rating)

                        # Create or verify link in the opposite direction, from alternative to original
                        reverse_existing_link = AlternativeTerm.query.filter_by(original_term_id=alt_term.id, alternative_term_id=original_term.id).first()
                        if not reverse_existing_link:
                            reverse_alt_link = AlternativeTerm(original_term_id=alt_term.id, alternative_term_id=original_term.id)
                            db.session.add(reverse_alt_link)
                            # Create a corresponding entry in appropriate_alternative_ratings in the reverse direction
                            reverse_new_rating = AlternativeRating(term_id=alt_term.id, alternative_term_id=original_term.id, rating=None)
                            db.session.add(reverse_new_rating)

                        db.session.commit()


if __name__ == '__main__':

    with app.app_context():
        db.create_all()
        insert_data(db)