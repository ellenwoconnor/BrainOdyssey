"""Models and database functions for Brain Odyssey project"""


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc, Index
from sqlalchemy.sql import label



db = SQLAlchemy()

###########################################################################
# MODEL DEFINITIONS
###########################################################################
#
#
# Tables in this data model:
#   Location:       individual x-y-z locations
#   Study:          individual studies
#   Activation:     location-study associations
#   Term:           individual words
#   StudyTerm:      associations between studies and words
#   TermCluster:    associations between words and topical clusters
#   cluster:        topical cluster IDs
#
#
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


    def __repr__(self):
        """Displays info about a location."""

        return "<Location id=%d x=%d y=%d z=%d>" % (
            self.location_id, self.x_coord, self.y_coord, self.z_coord)


### Retrieve xyz from db ######################################################

    @classmethod
    def check_by_xyz(cls, x=None, y=None, z=None):
        """Returns existing xyz instance of the class (None if no such
        instance exists).

            >>> Location.check_by_xyz(4, -68, 6)
            <Location id=80039 x=4 y=-68 z=6>

            >>> Location.check_by_xyz(4, -68, 200) == None
            True

        Used in database seeding"""

        location_obj = cls.query.filter(cls.x_coord == x,
                                        cls.y_coord == y,
                                        cls.z_coord == z).first()
        return location_obj


### Look up xyz locations associated with a word ################################

    @classmethod
    def get_xyzs_from_word(cls, word, freq=.1):
        """Returns all surface xyz coordinates associated with a word.

        Used to place dots on the brain in locations associated with a word.
        [NO LONGER IN USE.]"""

        location_coords = db.session.query(
            cls.x_coord, cls.y_coord, cls.z_coord).join(
            Activation).join(Study).join(StudyTerm).filter(
            StudyTerm.word == word,
            StudyTerm.frequency > freq,
            cls.location_id < 81925).group_by(Activation.location_id).all()

        return location_coords


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


### Look up location ids associated with a list of studies ##################

    @classmethod
    def get_activations_from_studies(cls, studies):
        """Returns activations from a specified set of studies, reporting
        activation on the brain surface.

            >>> Activation.get_activations_from_studies([25619848])
            [<Activation pmid=25619848 location_id=1459>, <Activation pmid=25619848 location_id=81891>]

        Used to generate intensity maps when user clicks on a reference.
        """

        activations = cls.query.filter(
            cls.pmid.in_(studies), cls.location_id < 81925).all()

        return activations


    @classmethod
    def get_location_count_from_studies(cls, studies):
        """Returns activations from a specified set of studies, reporting
        activation on the brain surface.

            >>> Activation.get_activations_from_studies([25619848])
            [<Activation pmid=25619848 location_id=1459>, <Activation pmid=25619848 location_id=81891>]

        Used to generate intensity maps when user clicks on a reference.
        """

        activations = db.session.query(cls.location_id, func.count(cls.pmid
            )).filter(cls.pmid.in_(studies), cls.location_id < 81925
            ).group_by(cls.pmid).all()

        return activations

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
    study_cluster = db.Column(db.Integer)


    ### Check if study is already in db ########################################

    @classmethod
    def get_study_by_pmid(cls, pmid):
        """Returns existing instance of Study class associated
        with a PubMed ID.

        Used in database seeding"""

        print "Found study ", pmid
        study_obj = cls.query.filter(cls.pmid == pmid).first()
        return study_obj

    @classmethod
    def get_references(cls, pmids):
        """Returns a list of references associated with specified PubMed IDs.

            >>> Study.get_references([15737663])
            {15737663: u'Li CS, Kosten TR, Sinha R. (2005). Sex differences in brain activation during stress imagery in abstinent cocaine users: a functional magnetic resonance imaging study. Biological psychiatry.'}
        
        Used to display reference list."""

        references = cls.query.filter(cls.pmid.in_(pmids)).all()
        citations = {}

        for reference in references:
            citation_text = reference.authors + ". (" + str(reference.year) + "). " + reference.title + " " + reference.journal + "."
            citations[reference.pmid] = citation_text

        return citations

    ### Retrieve studies associated with a study cluster #######################

    def get_cluster_mates(self):
        """Returns the other studies in a study cluster.

            >>> study = Study.get_study_by_pmid(15737663)
            Found study  15737663
            >>> study.get_cluster_mates()
            Getting all cluster mates associated with cluster  62
            [14625150, 15737663, 16284946, 17032778, 17428684, 17686466, 17873968, 19403118, 19555674, 19596123, 19632211, 19641623, 19675245, 19720989, 19846063, 20004250, 20139149, 20621656, 20692349, 20861377, 21126593, 21211567, 21246665, 21498384, 21609968, 21664280, 21705195, 21783177, 22079927, 22291028, 22418012, 22442069, 22504779, 22674267, 22875937, 22929607, 23125822, 23401511, 23587493, 23730277, 23776438, 23840493, 23967320, 24316200, 24352030, 24478326, 24553284, 24760847, 25554429]
        
        """

        print "Getting all cluster mates associated with cluster ", self.study_cluster
        cluster_mates = Study.query.filter(Study.study_cluster == self.study_cluster).all()

        return [cluster_mate.pmid for cluster_mate in cluster_mates]


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

        Used to generate JSON for D3."""

        print "Getting all terms from studies", pmids

        terms = db.session.query(cls.word, cls.frequency).filter(
            cls.pmid.in_(pmids)).order_by(desc(cls.frequency)).limit(lim).all()

        # Terms will be used to build a json dictionary;
        # (Term, freq) lists will be used to constrain the cluster search
        return terms, [term[0] for term in terms if term[1] > freq_threshold]


    @classmethod
    def get_pmid_by_term(cls, word, limit=40):
        """Returns a list of the top n studies associated with a list of words
        [w1] or [w1, w2, w3...].

        PMIDs used to generate references."""

        print "Getting all studies associated with ", word

        if isinstance(word, list):
            pmids = db.session.query(cls.pmid).filter(
                cls.word.in_(word)).group_by(
                cls.pmid).order_by(
                cls.frequency).limit(limit).all()

        else:
            pmids = db.session.query(cls.pmid).filter(
                cls.word == word).group_by(
                cls.pmid).order_by(
                cls.frequency).limit(limit).all()

        return [pmid[0] for pmid in pmids]

    @classmethod
    def get_by_word(cls, word, limit=1000):
        """Returns db rows where the study mentions some desired word(s)
        at or above a given frequency threshold."""

        if isinstance(word, list):
            pmidfreqs = cls.query.filter(
                cls.word.in_(word)).order_by(desc(cls.frequency)).limit(limit).all()

        else:
            pmidfreqs = cls.query.filter(
                cls.word == word).order_by(desc(cls.frequency)).limit(limit).all()

        return pmidfreqs


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
        """Returns the 'most relevant' topic clusters given a word or
        list of words by maximizing the # of words per cluster.

            >>> TermCluster.get_top_clusters([u'accurate', u'addiction', u'advantage', u'agreement', u'alzheimer'])
            Getting the top clusters associated with terms [u'accurate', u'addiction', u'advantage', u'agreement', u'alzheimer']
            [35, 98, 100, 228, 231, 304, 305, 306, 338, 377, 379, 393]

        """

        print "Getting the top clusters associated with ", terms[0:25]

        if isinstance(terms, list):
            clusters = db.session.query(cls.cluster_id).filter(
                cls.word.in_(terms)).group_by(cls.cluster_id).order_by(desc(
                func.count(cls.word))).limit(n).all()

        else:
            clusters = db.session.query(cls.cluster_id).filter(
                cls.word == terms).limit(n).all()

        return [cluster[0] for cluster in clusters]


    ### Get all clusters associated with a list of words ######################

    @classmethod
    def get_word_cluster_pairs(cls, clusters, words):
        """Returns a list of cluster-word pairs.

            >>> TermCluster.get_word_cluster_pairs([133], [u'disease'])
            Getting the associations with clusters [133]
            [(133, u'disease')]

        Used to get word-cluster associations for D3, with respect to a set of words
        associated with a location, and a set of 'most talked about' clusters."""

        print "Getting the associations with clusters", clusters

        associations = db.session.query(cls.cluster_id, cls.word).filter(
            cls.cluster_id.in_(clusters), cls.word.in_(words)).all()

        return associations


    ### Get all words associated with a particular cluster #####################

    @classmethod
    def get_words_in_cluster(cls, cluster):
        """Returns a list of words associated with some cluster."""

        print "Getting the words associated with cluster", cluster

        words = db.session.query(cls.word).filter(cls.cluster_id == cluster).all()

        return [word[0] for word in words]


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
        """Returns True if a cluster_id is already in the table, False if not.

        Used in database seeding"""

        if cls.query.filter(cls.cluster_id == cluster_id).first() is None:
            return False
        else:
            return True



##############################################################################
# Helper functions


def connect_to_db(app):
    """Connect the database to our Flask app."""

    # Configure to use our SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///odyssey_v2.db'
    db.app = app
    db.init_app(app)


if __name__ == "__main__":
    from server import app
    connect_to_db(app)
    print "Connected to DB."
