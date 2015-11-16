"""Models and database functions for Brain Odyssey project"""


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc, Index
from sqlalchemy.sql import label


db = SQLAlchemy()

###########################################################################
# MODEL DEFINITIONS
###########################################################################


###########################################################################
# LOCATION TABLE
###########################################################################

class Location(db.Model):
    """An individual pinpoint location in the brain represented by an x-y-z
    coordinate."""

    __tablename__ = 'locations'

    location_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    x_coord = db.Column(db.Float, nullable=False)
    y_coord = db.Column(db.Float, nullable=False)
    z_coord = db.Column(db.Float, nullable=False)
    label = db.Column(db.String, nullable=True)
    # space = db.Column(db.String(30), nullable=True)  # MNI, TAL or Unknown

    activation = db.relationship('Activation')
    __table_args__ = (Index('location_index', 'x_coord', 'y_coord', 'z_coord'),)


### Retrieve xyz from db ######################################################

    @classmethod
    def check_by_xyz(cls, x=None, y=None, z=None):
        """Returns existing xyz instance of the class (None if no such
        instance exists).

        Used in database seeding"""

        location_obj = cls.query.filter(cls.x_coord == x,
                                        cls.y_coord == y,
                                        cls.z_coord == z).first()
        return location_obj


### Look up xyz locations associated with a word ################################

    @classmethod
    def get_xyzs_from_word(cls, word, freq=.1):
        """Returns all surface xyz coordinates associated with a word.

            >>> len(Location.get_locations_from_word('semantic'))
            27279

        """

        location_coords = db.session.query(
            cls.x_coord, cls.y_coord, cls.z_coord).join(
            Activation).join(Study).join(StudyTerm).filter(
            StudyTerm.word == word,
            StudyTerm.frequency > freq,
            cls.location_id < 81925).group_by(Activation.location_id).all()

        return location_coords

        # Note that these searches typically yield locations in the tens of thousands
        # e.g. 'emotion' is linked to almost the entire surface


###  Display coordinate information ############################################

    def __repr__(self):
        """Displays info about a location."""

        return "<Location id=%d x=%d y=%d z=%d label=%s space=%s>" % (
            self.location_id, self.x_coord, self.y_coord,
            self.z_coord, self.label, self.space)


###########################################################################
# ACTIVATION TABLE
###########################################################################

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

    def __repr__(self):
        """Displays info about an activation."""

        return "<Activation pmid=%d location_id=%s>" % (self.pmid,
                                                       self.location_id)

### Get studies reporting location ############################################

    @classmethod
    def get_pmids_from_xyz(cls, x_coord, y_coord, z_coord, radius=None):
        """Returns the PubMed IDs (unique identifiers) for any studies reporting
        activation at or near the xyz coordinate.

            >>> Activation.get_pmids_from_xyz(-60, 0, -30, 3)
            Getting all studies with radius 3
            [15737663, 16481375, 17121746, 21908871]

            >>> Activation.get_pmids_from_xyz(-60, 0, -30, 2)
            Getting all studies with radius 2
            Getting all studies with radius 3
            [15737663, 16481375, 17121746, 21908871]

        """

        # If the radius is provided, use it get studies reporting activation
        # in locations within +/- n millimeters of xyz
        if radius:
            print "Getting all studies with radius", radius
            pmids = db.session.query(cls.pmid).join(Location).filter(
                Location.x_coord < (x_coord + radius),
                Location.x_coord > (x_coord - radius),
                Location.y_coord < (y_coord + radius),
                Location.y_coord > (y_coord - radius),
                Location.z_coord < (z_coord + radius),
                Location.z_coord > (z_coord - radius),
                ).group_by(cls.pmid).all()

            pmids = [pmid[0] for pmid in pmids]

            # If there are no hits, widen the radius and re-search.
            if len(pmids) < 1:
                radius += 1
                return cls.get_pmids_from_xyz(x_coord, y_coord, z_coord, radius)

        # If no radius is specified, query for exact location
        else:
            pmids = db.session.query(cls.pmid).join(Location).filter(
                Location.x_coord == x_coord,
                Location.y_coord == y_coord,
                Location.z_coord == z_coord).all()

            pmids = [pmid[0] for pmid in pmids]

        # Return all studies matching the specified location
        return pmids

### Look up location ids associated with a word ################################

    @classmethod
    def get_activations_from_word(cls, word, scale=4):

        activations = db.session.query(
            cls.location_id, func.sum(StudyTerm.frequency)).join(
            Study).join(StudyTerm).filter(
            StudyTerm.word == word, cls.location_id < 81925).group_by(
            cls.location_id).all()

        location_ids = {}
        for element in activations:
            location_ids[element[0]] = element[1] * scale

        return location_ids


###########################################################################
# STUDY TABLE
###########################################################################

class Study(db.Model):
    """An individual study by PubMed ID."""

    __tablename__ = "studies"

    pmid = db.Column(db.Integer, primary_key=True)
    doi = db.Column(db.String(200))
    title = db.Column(db.String(300))
    authors = db.Column(db.String(300))
    year = db.Column(db.Integer)
    journal = db.Column(db.String(200))


    ### Check if study is already in db ########################################

    @classmethod
    def get_study_by_pmid(cls, pmid):
        """Returns existing instance of Study class associated
        with a PubMed ID.

        Used in database seeding"""

        study_obj = cls.query.filter(cls.pmid == pmid).first()
        return study_obj

    ### Retrieve studies associated with location #############################

    @classmethod
    def get_references(cls, pmids):
        """Returns a list of references associated with specified PubMed IDs.
        """

        reference_data = cls.query.filter(cls.pmid.in_(pmids)).all()
        print reference_data
        citations = []

        for reference in reference_data:
            citation = reference.authors + ". (" + str(reference.year) + "). " + reference.title + " " + reference.journal + "."
            citations.append(citation)

        return citations

    ### Get information about a study ########################################

    def __repr__(self):
        """Displays info about a study."""

        return "<Study pmid=%d doi=%s title=%s year=%d>" % (
            self.pmid, self.doi, self.title, self.year)


###########################################################################
# STUDYTERM TABLE
###########################################################################


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


    ### Get information about a study topic ##################################

    def __repr__(self):
        """Displays info about a word associated with a study."""

        return "<StudyTerm word=%s pmid=%d frequency=%f>" % (
            self.word, self.pmid, self.frequency)

    ### Retrieve terms assoc. with studies  ###################################

    @classmethod
    def get_terms_by_pmid(cls, pmids, lim=100, freq_threshold=.05):
        """Returns all terms associated with certain PMIDs, and the frequency
        the term is used in each text.

            >>> StudyTerm.get_terms_by_pmid([15737663, 16481375, 17121746, 21908871]) # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
            Getting all terms from studies [15737663, 16481375, 17121746, 21908871]
            ([(u'stress', 0.648257962749), (u'asd', 0.536948763846),
                (u'voice', 0.522110847073), (u'children', 0.390914181003), ...
                u'patient group', u'modulating', u'shifting', u'group',
                u'information', u'impairments'])
        """

        print "Getting all terms from studies", pmids

        terms = db.session.query(cls.word, cls.frequency).filter(
            cls.pmid.in_(pmids)).order_by(desc(cls.frequency)).limit(lim).all()

        # Terms will be used to build a json dictionary;
        # List will be used to constrain the cluster search
        return terms, [term[0] for term in terms if term[1] > freq_threshold]


###########################################################################
# TERM TABLE
###########################################################################

class Term(db.Model):
    """A term extracted from study text."""

    __tablename__ = "terms"

    word = db.Column(db.String(100), primary_key=True)

    def __repr__(self):
        """Displays info about a term."""

        return "<Terms term=%s>" % (self.word)

    ### Check if term in db ################################################

    @classmethod
    def check_for_term(cls, word):
        """Returns True if a word is in Term table already, False if not.

            >>> Term.check_for_term('willy-nilly')
            False
            >>> Term.check_for_term('emotion')
            True

        Used in database seeding"""

        # TO DO: allow for some kind of fuzzy search so that:
        #
        # (1) If a word is really a two-word phrase, check if
        # either of those words is in the Term table.
        #
        # (2) If the stemmed word is in stemmed terms, add it as a match

        if cls.query.filter(cls.word == word).first() is None:
            return False
        else:
            return True



###########################################################################
# TERMCLUSTER TABLE
###########################################################################

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


    ### Get "popular" clusters f###############################################

    @classmethod
    def get_top_clusters(cls, terms, n=12):
        """Returns the 15 'most relevant' topic clusters given some
        list of words by maximizing the # of words per cluster.

            >>> TermCluster.get_top_clusters([u'accurate', u'addiction', u'advantage', u'agreement', u'alzheimer'])
            Getting the top clusters associated with terms [u'accurate', u'addiction', u'advantage', u'agreement', u'alzheimer']
            [35, 98, 100, 228, 231, 304, 305, 306, 338, 377, 379, 393]

        """

        print "Getting the top clusters associated with terms", terms[0:25]

        clusters = db.session.query(cls.cluster_id).filter(
            cls.word.in_(terms)).group_by(cls.cluster_id).order_by(desc(
            func.count(cls.word))).limit(n).all()

        return [cluster[0] for cluster in clusters]


    ### Get information about a study ########################################

    @classmethod
    def get_word_cluster_pairs(cls, clusters, words):
        """Returns a list of cluster-word pairs.

            >>> TermCluster.get_word_cluster_pairs([133], [u'disease'])
            Getting the associations with clusters [133]
            [(133, u'disease')]

        """
        print "Getting the associations with clusters", clusters

        associations = db.session.query(cls.cluster_id, cls.word).filter(
            cls.cluster_id.in_(clusters), cls.word.in_(words)).all()

        return associations


###########################################################################
# CLUSTER TABLE
###########################################################################

class Cluster(db.Model):
    """A topic cluster, identified by an integer from 0-400."""

    __tablename__ = "clusters"

    cluster_id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        """Displays info about a cluster."""

        return "<Cluster id=%s>" % (self.id)

    ### Check if cluster in db ########################################

    @classmethod
    def check_for_cluster(cls, cluster_id):
        """Returns True if a cluster_id is already in the table, False if not."""

        if cls.query.filter(cls.cluster_id == cluster_id).first() is None:
            return False
        else:
            return True



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
