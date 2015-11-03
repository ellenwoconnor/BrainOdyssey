"""Models and database functions for Brain Odyssey project"""


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.sql import label


db = SQLAlchemy()

###########################################################################
# Model definitions

class Location(db.Model):
    """An individual pinpoint location in the brain represented by an x-y-z
    coordinate."""

    __tablename__ = "locations"

    location_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    x_coord = db.Column(db.Float, nullable=False)
    y_coord = db.Column(db.Float, nullable=False)
    z_coord = db.Column(db.Float, nullable=False)
    label = db.Column(db.String, nullable=True)
    space = db.Column(db.String(30), nullable=True)  # MNI, TAL or Unknown

    activation = db.relationship('Activation')

    @classmethod
    def check_by_xyz_space(cls, x=None, y=None, z=None, space=None):
        """Returns  existing xyz instance of the class (None if no such
        instance exists)."""

        location_obj = cls.query.filter(cls.x_coord == x,
                                        cls.y_coord == y,
                                        cls.z_coord == z,
                                        cls.space == space).first()
        return location_obj

    def __repr__(self):
        """Displays info about a location."""
        return "<Location id=%d x=%d y=%d z=%d label=%s space=%s>" % (
            self.location_id, self.x_coord, self.y_coord,
            self.z_coord, self.label, self.space)


class Activation(db.Model):
    """Peak activation coordinate reported in a study."""

    __tablename__ = "activations"

    activation_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    pmid = db.Column(db.Integer, db.ForeignKey('studies.pmid'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.location_id'),
                            nullable=False)

    # relationships
    study = db.relationship('Study')
    location = db.relationship('Location')

    @classmethod
    def get_pmid_by_location(cls, loc_id):
        """ WRITE ME"""
        studies_reporting_activation = cls.query.filter(
            cls.location_id == loc_id).all()
        return [study_obj.pmid for study_obj in studies_reporting_activation]

    def __repr__(self):
        """Displays info about an activation."""

        return "<Activation pmid=%d location_id=%s>" % (self.pmid,
                                                       self.location_id)


class Study(db.Model):
    """An individual study by PubMed ID."""

    __tablename__ = "studies"

    pmid = db.Column(db.Integer, primary_key=True)
    doi = db.Column(db.String(200))
    title = db.Column(db.String(300))
    authors = db.Column(db.String(300))
    year = db.Column(db.Integer)
    journal = db.Column(db.String(200))

    @classmethod
    def get_study_by_pmid(cls, pmid):
        """Returns existing instance of Study class associated
        with a PubMed ID."""

        study_obj = cls.query.filter(cls.pmid == pmid).first()
        return study_obj

    def __repr__(self):
        """Displays info about a study."""

        return "<Study pmid=%d doi=%s title=%s year=%d>" % (
            self.pmid, self.doi, self.title, self.year)


class StudyTerm(db.Model):
    """A relationship between a term and a study."""

    __tablename__ = "studies_terms"

    studyterm_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    word = db.Column(db.String(100), db.ForeignKey('terms.word'))
    pmid = db.Column(db.Integer, db.ForeignKey('studies.pmid'), nullable=False)
    # A value between 0-1 representing the relative frequency that the keyword
    # is mentioned in a study.
    frequency = db.Column(db.Float, nullable=False)

    term = db.relationship('Term', backref="studies_terms")
    study = db.relationship('Study', backref="studies_terms")

    def __repr__(self):
        """Displays info about a word associated with a study."""

        return "<StudyTerm word=%s pmid=%d frequency=%f>" % (
            self.word, self.pmid, self.frequency)

    @classmethod
    def get_terms_by_pmid(cls, pmid):
        studyterm_objs = cls.query.filter(pmid == pmid).all()
        return [obj.word for obj in studyterm_objs]

    @classmethod
    def get_terms_in_radius(cls, x_coord, y_coord, z_coord, radius):
        """Returns a set of terms associated with some xyz
        coordinate, +/- radius perimeter.

        If no terms are retrieved, increase the radius by 1 and call
        the function recursively."""

        # Test with: terms = StudyTerm.get_terms_in_radius(-60, 0, -30, 3)
        print "I am in this function with radius", radius

        terms = db.session.query(cls.word, func.sum(cls.frequency), func.count(
            cls.word)).join(Study).join(Activation).join(Location).filter(
            Location.x_coord < (x_coord + radius),
            Location.x_coord > (x_coord - radius),
            Location.y_coord < (y_coord + radius),
            Location.y_coord > (y_coord - radius),
            Location.z_coord < (z_coord + radius),
            Location.z_coord > (z_coord - radius)
            ).group_by(cls.word).all()

        # If there are no terms to display, increase the radius by 1.
        # Test with: terms = StudyTerm.get_terms_in_radius(-60, 0, -30, 2)
        if len(terms) < 1:
            radius += 1
            cls.get_terms_in_radius(x_coord, y_coord, z_coord, radius)
            # BOO!! Not working. WHY?
        else:
            return terms


class Term(db.Model):
    """A term extracted from study text."""

    __tablename__ = "terms"

    word = db.Column(db.String(100), primary_key=True)

    @classmethod
    def check_for_term(cls, word):
        """Returns True if a term is in Term table already, False if not."""

        if cls.query.filter(cls.word == word).first() is None:
            return False
        else:
            return True


    def __repr__(self):
        """Displays info about a term."""

        return "<Terms term=%s>" % (self.word)


class TermCluster(db.Model):
    """An association between a term and a topic cluster."""

    __tablename__ = "terms_clusters"

    termcluster_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    word = db.Column(db.String(100), db.ForeignKey('terms.word'))
    cluster_id = db.Column(db.Integer, db.ForeignKey('clusters.cluster_id'))

    term = db.relationship('Term', backref="terms_clusters")
    cluster = db.relationship('Cluster', backref="terms_clusters")

    def __repr__(self):
        """Displays info about a term-cluster association."""

        return "<TermCluster id=%d term=%s cluster_id=%d>" % (
            self.termcluster_id, self.term, self.cluster_id)



class Cluster(db.Model):
    """A topic cluster, identified by an integer from 0-200."""

    __tablename__ = "clusters"

    cluster_id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def check_for_cluster(cls, cluster_id):
        """Returns True if a cluster_id is already in the table, False if not."""

        if cls.query.filter(cls.cluster_id == cluster_id).first() is None:
            return False
        else:
            return True

    def __repr__(self):
        """Displays info about a cluster."""

        return "<Cluster id=%s>" % (self.id)


##############################################################################
# Helper functions


def connect_to_db(app):
    """Connect the database to our Flask app."""

    # Configure to use our SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///odyssey.db'
    db.app = app
    db.init_app(app)


if __name__ == "__main__":
    from server import app
    connect_to_db(app)
    print "Connected to DB."
