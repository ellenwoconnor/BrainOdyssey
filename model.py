"""Models and database functions for Brain Odyssey project"""


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc
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

    __tablename__ = "locations"

    location_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    x_coord = db.Column(db.Float, nullable=False)
    y_coord = db.Column(db.Float, nullable=False)
    z_coord = db.Column(db.Float, nullable=False)
    label = db.Column(db.String, nullable=True)
    space = db.Column(db.String(30), nullable=True)  # MNI, TAL or Unknown

    activation = db.relationship('Activation')


### Retrieve xyz from db ######################################################

    @classmethod
    def check_by_xyz_space(cls, x=None, y=None, z=None, space=None):
        """Returns existing xyz instance of the class (None if no such
        instance exists).

        Used in database seeding"""

        location_obj = cls.query.filter(cls.x_coord == x,
                                        cls.y_coord == y,
                                        cls.z_coord == z,
                                        cls.space == space).first()
        return location_obj

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
        activation at or near the xyz coordinate."""

        # If the radius is provided, use it get studies reporting activation
        # in locations within +/- n millimeters of xyz
        if radius:
            print "I am getting all studies with radius", radius
            # Test with: terms = StudyTerm.get_terms_in_radius(-60, 0, -30, 3)
            pmids = db.session.query(cls.pmid).join(Location).filter(
                Location.x_coord < (x_coord + radius),
                Location.x_coord > (x_coord - radius),
                Location.y_coord < (y_coord + radius),
                Location.y_coord > (y_coord - radius),
                Location.z_coord < (z_coord + radius),
                Location.z_coord > (z_coord - radius),
                ).group_by(cls.pmid).all()

            pmids = [pmid[0] for pmid in pmids]

            # If there are no hits, widen the radius and research.
            # Test with: terms = StudyTerm.get_terms_in_radius(-60, 0, -30, 2)
            if len(pmids) < 1:
                radius += 1
                return cls.get_terms_in_radius(x_coord, y_coord, z_coord, radius)

        # If no radius is specified, query for exact location
        else:
            pmids = db.session.query(cls.pmid).join(Location).filter(
                Location.x_coord == x_coord,
                Location.y_coord == y_coord,
                Location.z_coord == z_coord).all()

            pmids = [pmid[0] for pmid in pmids]

        # Return all studies matching the specified location
        return pmids

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


    ### Retrieve a study from db ########################################

    @classmethod
    def get_study_by_pmid(cls, pmid):
        """Returns existing instance of Study class associated
        with a PubMed ID.

        Used in database seeding"""

        study_obj = cls.query.filter(cls.pmid == pmid).first()
        return study_obj

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
    def get_terms_by_pmid(cls, pmids):
        """Returns all terms associated with certain PMIDs, and the frequency
        the term is used in each text.

        Test with: pmids = [15737663, 16481375, 17121746, 21908871]"""

        print "Getting all terms from studies", pmids

        terms = db.session.query(cls.word, cls.frequency).filter(
            cls.pmid.in_(pmids)).all()

        # Terms will be used to build a json dictionary; 
        # List will be used to constrain the cluster search
        return terms, [term[0] for term in terms if term[1] > .05]

    ### Normalize frequencies ##############################################

    @classmethod
    def transform_frequencies(cls, terms):
        """ TODO: 
        Normalize each frequency using the mean/sd frequency by word."""


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
    def get_top_clusters(cls, terms):
        """Returns the 15 'most relevant' topic clusters given some
        list of words by maximizing the # of words per cluster.

        Test with:
        words = [u'accurate', u'addiction', u'advantage', u'agreement', u'alzheimer', u'alzheimer disease', u'anterior', u'anterior cingulate', u'anxiety', u'asd', u'assessed using', u'associations', u'autism', u'autism spectrum', u'available', u'background', u'baseline', u'bases', u'canonical', u'caudate', u'caudate nucleus', u'change', u'characterized', u'children', u'cingulate', u'cingulate cortices', u'circuitry', u'cognitive deficits', u'cohort', u'compare', u'comprehensive', u'condition', u'confirm', u'contextual', u'control', u'control group', u'cortical', u'cortices', u'critical role', u'cross', u'cross modal', u'cues', u'decision', u'deficits', u'deficits', u'deficits', u'degeneration', u'demands', u'dementia', u'depending', u'developed', u'developing', u'development', u'difficulty', u'discrimination', u'disease', u'disease', u'disorders', u'dopamine', u'dopaminergic', u'drug', u'early', u'early stage', u'effortful', u'event', u'executive', u'exhibit', u'experiencing', u'explicit', u'face', u'face recognition', u'familiarity', u'female', u'frontal', u'frontal anterior', u'frontal cortices', u'frontotemporal', u'functioning', u'gender', u'grey', u'grey matter', u'group', u'group', u'group', u'groups', u'guide', u'guided', u'gyrus ifg', u'hand', u'handed', u'healthy adults', u'high functioning', u'higher level', u'hypoactivation', u'identification', u'ifg', u'ii', u'iii', u'imagery', u'impaired', u'impaired', u'impairments', u'impairments', u'impairments', u'included', u'included', u'individuals', u'induced', u'information', u'intended', u'interpret', u'inversely', u'involving', u'knowledge', u'listened', u'little', u'little known', u'lobe', u'male', u'matter', u'mean', u'mean age', u'meaning', u'measures', u'mediates', u'men', u'mental', u'mental states', u'methods functional', u'middle frontal', u'modal', u'modalities', u'model', u'modulating', u'needed', u'neuroanatomical', u'neurodegenerative', u'neutral', u'new', u'nucleus', u'observations', u'obtained', u'outcome', u'parkinson', u'parkinson disease', u'participated', u'particularly', u'patient', u'patient group', u'pattern', u'perception', u'periods', u'planning', u'play', u'play role', u'posterior cingulate', u'potentially', u'prefrontal posterior', u'prior', u'processes', u'protocol', u'provide evidence', u'range', u'rated', u'rating', u'recently', u'recognition', u'recruit', u'recruited', u'reflect', u'regard', u'relevant', u'require', u'required', u'requiring', u'research', u'role', u'second', u'seeking', u'session', u'set', u'seven', u'severe', u'sex', u'shift', u'shifting', u'short', u'showing', u'shown', u'situations', u'socially', u'speaker', u'speaker', u'specifically', u'spectrum', u'spectrum disorders', u'stage', u'stages', u'states', u'strategies', u'stress', u'strong', u'substrate', u'suggests', u'systematic', u'taking', u'task', u'task demands', u'temporal', u'traditional', u'trial', u'types', u'typically', u'typically developing', u'understanding', u'use', u'users', u'variant', u'varied', u'verbal', u'vocal', u'voice', u'women', u'years', u'young', u'young healthy']
        Output should be: [308, 228, 133, 325, 0, 197, 204, 276, 287, 373, 39, 59, 100, 123, 210]
        """

        print "Getting the top clusters associated with terms", terms

        clusters = db.session.query(cls.cluster_id).filter(
            cls.word.in_(terms)).group_by(cls.cluster_id).order_by(desc(
            func.count(cls.word))).limit(15).all()

        return [cluster[0] for cluster in clusters]


    ### Get information about a study ########################################

    @classmethod
    def get_word_cluster_pairs(cls, clusters, words):
        """Returns a list of cluster-word pairs.

        Test with:
        clusters = [228, 308, 133, 210, 0, 294, 37, 128, 261, 357, 98, 186, 215, 306, 59]
        words = [u'accurate', u'addiction', u'advantage', u'agreement', u'alzheimer', u'alzheimer disease', u'anterior', u'anterior cingulate', u'anxiety', u'asd', u'assessed using', u'associations', u'autism', u'autism spectrum', u'available', u'background', u'baseline', u'bases', u'canonical', u'caudate', u'caudate nucleus', u'change', u'characterized', u'children', u'cingulate', u'cingulate cortices', u'circuitry', u'cognitive deficits', u'cohort', u'compare', u'comprehensive', u'condition', u'confirm', u'contextual', u'control', u'control group', u'cortical', u'cortices', u'critical role', u'cross', u'cross modal', u'cues', u'decision', u'deficits', u'deficits', u'deficits', u'degeneration', u'demands', u'dementia', u'depending', u'developed', u'developing', u'development', u'difficulty', u'discrimination', u'disease', u'disease', u'disorders', u'dopamine', u'dopaminergic', u'drug', u'early', u'early stage', u'effortful', u'event', u'executive', u'exhibit', u'experiencing', u'explicit', u'face', u'face recognition', u'familiarity', u'female', u'frontal', u'frontal anterior', u'frontal cortices', u'frontotemporal', u'functioning', u'gender', u'grey', u'grey matter', u'group', u'group', u'group', u'groups', u'guide', u'guided', u'gyrus ifg', u'hand', u'handed', u'healthy adults', u'high functioning', u'higher level', u'hypoactivation', u'identification', u'ifg', u'ii', u'iii', u'imagery', u'impaired', u'impaired', u'impairments', u'impairments', u'impairments', u'included', u'included', u'individuals', u'induced', u'information', u'intended', u'interpret', u'inversely', u'involving', u'knowledge', u'listened', u'little', u'little known', u'lobe', u'male', u'matter', u'mean', u'mean age', u'meaning', u'measures', u'mediates', u'men', u'mental', u'mental states', u'methods functional', u'middle frontal', u'modal', u'modalities', u'model', u'modulating', u'needed', u'neuroanatomical', u'neurodegenerative', u'neutral', u'new', u'nucleus', u'observations', u'obtained', u'outcome', u'parkinson', u'parkinson disease', u'participated', u'particularly', u'patient', u'patient group', u'pattern', u'perception', u'periods', u'planning', u'play', u'play role', u'posterior cingulate', u'potentially', u'prefrontal posterior', u'prior', u'processes', u'protocol', u'provide evidence', u'range', u'rated', u'rating', u'recently', u'recognition', u'recruit', u'recruited', u'reflect', u'regard', u'relevant', u'require', u'required', u'requiring', u'research', u'role', u'second', u'seeking', u'session', u'set', u'seven', u'severe', u'sex', u'shift', u'shifting', u'short', u'showing', u'shown', u'situations', u'socially', u'speaker', u'speaker', u'specifically', u'spectrum', u'spectrum disorders', u'stage', u'stages', u'states', u'strategies', u'stress', u'strong', u'substrate', u'suggests', u'systematic', u'taking', u'task', u'task demands', u'temporal', u'traditional', u'trial', u'types', u'typically', u'typically developing', u'understanding', u'use', u'users', u'variant', u'varied', u'verbal', u'vocal', u'voice', u'women', u'years', u'young', u'young healthy']
        Output should be: [(133, u'disease'), (210, u'executive'), ...]
        """
        print "Getting the associations with clusters", clusters

        associations = db.session.query(cls.cluster_id, cls.word).filter(
            cls.cluster_id.in_(clusters), cls.word.in_(words)).all()

        return associations


###########################################################################
# CLUSTER TABLE
###########################################################################

class Cluster(db.Model):
    """A topic cluster, identified by an integer from 0-200."""

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

###########################################################################
# OTHER
###########################################################################


def build_json_for_FDG(x_coord, y_coord, z_coord, radius, scale=1):
    """ Returns a master dictionary with xyz at the root node.

    Test with parameters: -60, 0, -30, 3
    """

    # Get all of the needed information from the db first:
    # Get the studies citing activation at/near xyz
    pmids = Activation.get_pmids_from_xyz(x_coord, y_coord, z_coord, radius)
    # Get [(wd, freq), ...] and [wd1, wd2] for most frequent words
    terms_for_dict, words = StudyTerm.get_terms_by_pmid(pmids)
    # Optional: transform the terms
    # Get the top clusters
    top_clusters = TermCluster.get_top_clusters(words)
    # Get the cluster-word associations
    associations = TermCluster.get_word_cluster_pairs(top_clusters, words)

    # Make the root node:
    xyz_loc = "x: " + str(x_coord) + ", y: " + str(y_coord) + ", z:" + str(z_coord)
    root_dict = {'name': xyz_loc, 'children': []}

    # Build the terminal nodes (leaves) first using (wd, freq) tuples
    # Output: {word: {'name': word, 'size': freq}, word2: ... }
    leaves = {}
    for (word, freq) in terms_for_dict:
        if word not in leaves:
            leaves[word] = {'name': word, 'size': freq * scale}
        else:
            leaves[word]['size'] += freq * scale

    # Embed the leaves in the clusters:
    # Output: {cluster_id: {'name': ID, 'children': [...]}, ... }
    clusters = {}
    for (cluster_id, word) in associations:
        if cluster_id not in clusters:
            clusters[cluster_id] = {'name': cluster_id, 'children': [leaves[word]]}
        else:
            clusters[cluster_id]['children'].append(leaves[word])

    # Put the clusters in the root dictionary
    # Output: {'name': root, children: [{'name': id, 'children': []}, ...]
    for cluster in top_clusters:
        root_dict['children'].append(clusters[cluster])

    return root_dict

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
