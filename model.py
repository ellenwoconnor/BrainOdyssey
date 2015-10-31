"""Models and database functions for Brain Odyssey project"""


from flask_sqlalchemy import SQLAlchemy


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
        return "<Location id=%d x=%d y=%d z=%d label=%s space=%s" % (
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
    study = db.relationship('Study', backref="activations")
    location = db.relationship('Location', backref="activations")

    def __repr__(self):
        """Displays info about an activation."""

        return "<Activation pmid=%d location_id=%s" % (self.pmid,
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

        return "<Study pmid=%d doi=%s title=%s year=%d" % (
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
        return "<StudyTerm word=%s pmid=%d frequency=%f" % (
            self.word, self.pmid, self.frequency)


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

        return "<Terms term=%s" % (self.term)


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

        return "<TermCluster id=%d term=%s cluster_id=%d" % (
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

        return "<Cluster id=%s" % (self.id)


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
