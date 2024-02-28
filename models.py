from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AlternativeTerm(db.Model):
    __tablename__ = 'alternative_terms'
    id = db.Column(db.Integer, primary_key=True)
    original_term_id = db.Column(db.String(30), db.ForeignKey('terms.id'), nullable=False)
    alternative_term_id = db.Column(db.String(30), db.ForeignKey('terms.id'), nullable=False)

class OffensivenessRating(db.Model):
    __tablename__ = 'offensiveness_ratings'
    id = db.Column(db.Integer, primary_key=True)
    term_id = db.Column(db.String(30), db.ForeignKey('terms.id'), nullable=False)
    rating = db.Column(db.Integer)

class AlternativeRating(db.Model):
    __tablename__ = 'appropriate_alternative_ratings'
    id = db.Column(db.Integer, primary_key=True)
    term_id = db.Column(db.String(30), db.ForeignKey('terms.id'), nullable=False)
    alternative_term_id = db.Column(db.String(30), db.ForeignKey('terms.id'), nullable=False)
    rating = db.Column(db.Integer)

class Term(db.Model):
    __tablename__ = 'terms'
    id = db.Column(db.String(30), primary_key=True)
    term = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(5000))
    language = db.Column(db.String(10), nullable=False, server_default='')
    alternatives_list = db.Column(db.String(100), nullable=False, server_default='')
    # Relationships
    offensiveness_ratings = db.relationship('OffensivenessRating', backref='term', lazy=True)
    
    # Adjusted relationships with overlaps parameter
    alternatives = db.relationship('AlternativeTerm', foreign_keys=[AlternativeTerm.original_term_id],
                                   backref=db.backref('original_term', lazy='joined', overlaps="alternatives,alternative_ratings"),
                                   lazy='dynamic', overlaps="alternative_ratings")
    alternative_ratings = db.relationship('AlternativeRating', secondary='alternative_terms',
                                          primaryjoin=id==AlternativeTerm.original_term_id,
                                          secondaryjoin=AlternativeTerm.id==AlternativeRating.alternative_term_id,
                                          backref=db.backref('term', lazy='dynamic', overlaps="alternatives,original_term"),
                                          lazy='dynamic', overlaps="alternatives,original_term")
    offensiveness_ratings = db.relationship('OffensivenessRating', backref='term', lazy=True)



