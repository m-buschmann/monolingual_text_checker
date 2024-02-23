from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()



"""class Term(db.Model):
    __tablename__ = 'terms'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(5000))
    language = db.Column(db.String(10), nullable=False, server_default='')
    alternatives = db.relationship('AlternativeTerm', backref='term', lazy=True)
    offensiveness_ratings = db.relationship('OffensivenessRating', backref='term', lazy=True)
    appropriate_alternative_ratings = db.relationship('AlternativeRating', backref='term', lazy=True)
   """
class AlternativeTerm(db.Model):
    __tablename__ = 'alternative_terms'
    id = db.Column(db.Integer, primary_key=True)
    original_term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    alternative_term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)

class Term(db.Model):
    __tablename__ = 'terms'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(5000))
    language = db.Column(db.String(10), nullable=False, server_default='')
    # Define a dynamic relationship for alternatives
    alternative_terms = db.relationship('AlternativeTerm',
                                        primaryjoin=id==AlternativeTerm.original_term_id,
                                        secondaryjoin=id==AlternativeTerm.alternative_term_id,
                                        secondary='alternative_terms',
                                        backref=db.backref('original_term', lazy='dynamic'),
                                        lazy='dynamic')

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

"""class AlternativeTerm(db.Model):
    __tablename__ = 'alternative_terms'
    id = db.Column(db.Integer, primary_key=True)
    original_term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    alternative_term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
"""