"""Utility file to seed database from files in seed_data directory"""


from model import Location, Activation, Study, StudyTerm, Term, TermCluster, Cluster
from model import connect_to_db, db
from server import app

def load_indices():
    """Adds surface x-y-z locations and their BrainBrowser index."""

    mniobj = open('static/models/brain-surface2.obj')
    coords = mniobj.readlines()
    counter = 0

    for i in range(0, 81924):
        row = coords[i].strip().split(" ")
        x = round(float(row[0]), 0)
        y = round(float(row[1]), 0)
        z = round(float(row[2]), 0)
        location_to_add = Location(x_coord=x, y_coord=y, z_coord=z,
                                       space=None, index=i)
        db.session.add(location_to_add)

    db.session.commit()


# Maybe it makes sense to add an MNI obj table here

def load_studies():
    """Load data from database.txt into Location, Activation, Study tables."""

    # Delete all rows in existing tables, so if we need to run this a second time,
    # we won't add duplicates
    Location.query.delete()     # comment this out if load_indices is being run
    Study.query.delete()
    Activation.query.delete()

    skip = True
    count_studies = 0

    # Parse txt file and convert to appropriate data types for seeding
    for row in open("seed_data/database.txt"):

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
        space = row[5]

        # Check whether PMID is already in Study; if not, add it to db.
        study_obj = Study.get_study_by_pmid(pmid)

        if study_obj is None:
            study_to_add = Study(pmid=pmid, doi=doi, title=title,
                                 authors=authors, year=year, journal=journal)
            db.session.add(study_to_add)
            db.session.commit()

        # Check whether xyz is already in Location; if not, add it to db and
        # retrieve its location ID (an autoincrementing primary key).
        # If xyz already in Location, retrieve its location_id.
        location_obj = Location.check_by_xyz_space(x, y, z, space)

        if location_obj is None:
            location_to_add = Location(x_coord=x, y_coord=y, z_coord=z,
                                       space=space)
            db.session.add(location_to_add)
            db.session.commit()
            loc_id = Location.check_by_xyz_space(x, y, z, space).location_id
        else:
            loc_id = location_obj.location_id

        # Add activation to db, using location_id identified/generated above
        activation_to_add = Activation(pmid=pmid, location_id=loc_id)
        db.session.add(activation_to_add)
        db.session.commit()

        # Print where we are and increment counter
        print "Database.txt seeding row ", count_studies
        count_studies += 1

def load_studies_terms():
    """Load info from studies_terms.txt into StudyTerm & Term tables.

    File format: R ID \t pmid \t word \t frequency
    Source: Neurosynth features.txt, transformed in R to long format."""


    print "Studies_terms.txt seeding"

    # Delete all rows in existing tables, so if we need to run this a second time,
    # we won't be trying to add duplicate users
    StudyTerm.query.delete()
    Term.query.delete()

    skip = True
    count_studies_terms = 0

    for row in open("seed_data/studies_terms.txt"):
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


def load_clusters():
    """Load info from topics.txt file into Cluster, TermCluster tables"""

    # Delete whatever's in the db already
    Cluster.query.delete()
    TermCluster.query.delete()

    count_clusters = 0

    for row in open('seed_data/topics.csv'):

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


if __name__ == "__main__":
    connect_to_db(app)

    # In case tables haven't been created, create them
    db.create_all()

    # Import different types of data
    load_studies()
    load_studies_terms()
    load_clusters()
