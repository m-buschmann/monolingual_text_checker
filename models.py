from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()



class Term(db.Model):
    __tablename__ = 'terms'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(100, collation='NOCASE'), unique=True)
    description = db.Column(db.String(5000, collation='NOCASE'))
    language = db.Column(db.String(10), nullable=False, server_default='')
    alternatives = db.relationship('Term', backref='movie', lazy=True)
    offensiveness_ratings = db.relationship('OffensivenessRating', backref='movie', lazy=True)
    appropriate_alternative_ratings = db.relationship('AlternativeRating', backref='movie', lazy=True)
   
class OffensivenessRating(db.Model):
    __tablename__ = 'offensiveness_ratings'
    id = db.Column(db.Integer, primary_key=True)
    term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    rating = db.Column(db.Integer)

class AlternativeRating(db.Model):
    __tablename__ = 'alternative_ratings'
    id = db.Column(db.Integer, primary_key=True)
    original_term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    alternative_term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    rating = db.Column(db.Integer)
