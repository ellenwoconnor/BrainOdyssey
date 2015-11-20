"""Utility file to seed database from files in seed_data directory"""


from model import Location, Activation, Study, StudyTerm, Term, TermCluster, Cluster
from model import connect_to_db, db
from server import app


def load_indices():
    """Adds surface x-y-z locations and their BrainBrowser index.

    File format:    x-coord y-coord z-coord
                    x-coord y-coord z-coord

    Row number corresponds to MNI object index.

    Source: Brainbrowser MNI object file"""

    print "Seeding indices..."
    # First we populate the locations table with all of the surface locations
    # tracked by Brainbrowser, along with their Brainbrowser indices (which I
    # am going to use as the location ID - i.e. the primary key)

    # Location.query.delete()

    mniobj = open('static/models/brain-surface2.obj')
    coords = mniobj.readlines()
    counter = 0

    for i in range(0, 81924):
        row = coords[i].strip().split(" ")
        x = round(float(row[0]), 0)
        y = round(float(row[1]), 0)
        z = round(float(row[2]), 0)
        location_to_add = Location(location_id = i, x_coord=x, y_coord=y, z_coord=z)
        db.session.add(location_to_add)

    db.session.commit()
    mniobj.close()


def load_studies():
    """Loads data from database.txt into Location, Activation, Study tables.

    File format:    PMID \t doi \t x \t y \t z \t space \t peak_id \t table_id 
                    \t table_num \t title \t authors \t year \t journal \t

    Source: Neurosynth database.txt file"""

    skip = True
    count_studies = 0
    database = open("seed_data/database.txt")

    # Parse txt file and convert to appropriate data types for seeding
    for row in database:

        # Skip the header of the txt file
        if skip:
            skip = False
            continue

        # Stop after the first 5000 rows for now
        # if count_studies > 5000:
        #     break

        row = row.rstrip().split('\t')

        # Information to go into Study, if applicable:
        pmid = int(row[0])
        doi = row[1]
        title = row[9]
        authors = row[10]
        year = int(row[11])
        journal = row[12].rstrip()

        # Information to go into Location, if applicable
        x = float(row[2])
        y = float(row[3])
        z = float(row[4])

        # Check whether PMID is already in Study; if not, add it to db.
        study_obj = Study.get_study_by_pmid(pmid)

        if study_obj is None:
            study_to_add = Study(pmid=pmid, doi=doi, title=title,
                                 authors=authors, year=year, journal=journal)
            db.session.add(study_to_add)
            db.session.commit()

        # Check whether xyz is already in Location; if not, add it to db and
        # retrieve its location ID (an autoincrementing primary key).
        # If xyz already in Location, get its location_id.
        location_obj = Location.check_by_xyz(x, y, z)

        if location_obj is None:
            location_to_add = Location(x_coord=x, y_coord=y, z_coord=z)
            db.session.add(location_to_add)
            db.session.commit()
            loc_id = Location.check_by_xyz(x, y, z).location_id
        else:
            loc_id = location_obj.location_id

        # Add activation to db, using location_id identified/generated above
        activation_to_add = Activation(pmid=pmid, location_id=loc_id)
        db.session.add(activation_to_add)
        db.session.commit()

        # Print where we are and increment counter
        print "Database.txt seeding row ", count_studies
        count_studies += 1

    database.close()


def load_studies_terms():
    """Loads info from studies_terms.txt into StudyTerm & Term tables.

    File format: R ID \t pmid \t word \t frequency

    Source: Neurosynth features.txt, transformed in R to long format."""


    print "Studies_terms.txt seeding"

    # Delete all rows in existing tables, so if we need to run this a second time,
    # we won't be trying to add duplicate users
    StudyTerm.query.delete()
    Term.query.delete()

    skip = True
    count_studies_terms = 0
    studies_terms = open("seed_data/studies_terms.txt")

    for row in studies_terms:
        # Skip the first line of the file
        if skip:
            skip = False
            continue

        # Stop after 5000 lines
        # if count_studies_terms > 5000:
        #     break

        # Parse txt file and convert to appropriate data types for seeding
        row = row.rstrip().split('\t')

        # If the term starts with "X", it is not a word but a number, e.g. "X01"
        # These don't make sense to track, so skip these rows.
        if row[2].startswith('\"X'):
            continue

        # Skip the lines indicating that a term did not appear anywhere
        # in the article (frequency of 0)
        if float(row[3]) == 0.0:
            continue

        pmid = int(row[1])
        word = row[2].strip('\"').replace(".", " ")
        freq = float(row[3])

        # Check if the word is already in Term; if not, add it
        if Term.check_for_term(word) is False:
            word_to_add = Term(word=word)
            db.session.add(word_to_add)

        # Add the row to the studies_terms table
        studies_terms_to_add = StudyTerm(word=word, pmid=pmid, frequency=freq)
        db.session.add(studies_terms_to_add)
        db.session.commit()

        # Print where we are and increment counter
        print "studies_terms.txt seeding row ", count_studies_terms
        count_studies_terms += 1


def load_study_clusters():
    """Loads info about topically clustered studies into Study table.

    File format: PMID \t study cluster ID

    Source: generated from a K-means cluster analysis to group related studies; see 
    DimReductionSelectingK.py for more details"""

    print "Seeding study clusters..."

    study_clusters = open('Clusters.txt')
    for row in study_clusters:
        row = row.rstrip().split('\t')
        pmid = int(row[0])
        cluster_id = int(row[1])

        study = Study.query.filter(Study.pmid == pmid).first()
        if study:
            study.study_cluster = cluster_id

    db.session.commit()
    study_clusters.close()


def load_clusters():
    """Load info from topics.txt file into Cluster, TermCluster tables

    File format: R row id,Topic XXX,R column ID,word

        where XXX represents a number between 0-400
        R ids can be discarded during seeding 

    Source: topic clustering data from Neurosynth, converted to long format
    in R prior to seeding. 
    Notes: the words tracked in this clustering are not in perfect
    alignment with those tracked in studies_terms.txt. Approximately 2000 of the 
    terms in studies_terms have a topical cluster, the remaining ~1000 do not.
    This number could be improved by stemming. Many of the words not tracked
    in clusters are multi-word phrases."""

    # Delete whatever's in the db already
    Cluster.query.delete()
    TermCluster.query.delete()

    count_clusters = 0
    topics_fileobj = open('seed_data/topics.csv')

    for row in topics_fileobj:

        row = row.rstrip().split(',')

        # Parse the txt into the appropriate data types for seeding
        cluster = int(row[1][-3:])
        word = row[3].strip()

        # Check if word is in our list of key terms. If it is, add to
        # TermCluster table to allow for lookup later (see model.py for TODO)

        if Term.check_for_term(word) is True:
            term_cluster_to_add = TermCluster(word=word, cluster_id=cluster)
            db.session.add(term_cluster_to_add)
            db.session.commit()

        # Check if a cluster is in our list of clusters. If it's not, add it.
        if Cluster.check_for_cluster(cluster) is False:
            cluster_to_add = Cluster(cluster_id=cluster)
            db.session.add(cluster_to_add)
            db.session.commit()

        # Print where we are and increment counter
        print "Topics.txt seeding row", count_clusters

        count_clusters += 1

    topics_fileobj.close()


if __name__ == "__main__":
    connect_to_db(app)

    # In case tables haven't been created, create them
    db.create_all()

    # Delete all rows in existing tables, so if we need to run this a second time,
    # we won't add duplicates
    # Location.query.delete()
    # Study.query.delete()
    # Activation.query.delete()

    # Import different types of data
    # load_indices()
    # load_studies()
    # load_study_clusters()
    load_studies_terms()
    load_clusters()
