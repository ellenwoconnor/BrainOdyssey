"""Brain Odyssey server"""

from jinja2 import StrictUndefined
from model import Location, Activation, Study, StudyTerm, Term, TermCluster, Cluster, connect_to_db
from flask import Flask, render_template, jsonify, request
from operator import itemgetter
import numpy as np

app = Flask(__name__)

# If you use an undefined variable in Jinja2, it raises an error.
app.jinja_env.undefined = StrictUndefined


################################################################################
#  HOMEPAGE ROUTES
################################################################################

@app.route('/')
def index():
    """Homepage."""

    return render_template('index.html')


@app.route('/words')
def retrieve_words():
    """Retrieves all available words in the db for autocomplete functionality."""

    words = Term.get_all()

    return jsonify({'words': words})


################################################################################
#  ROUTE FOR D3 CREATION
################################################################################

@app.route('/d3topic.json')
def generate_topic_d3():

    cluster_id = request.args.get("cluster")
    words = TermCluster.get_words_in_cluster(cluster_id)

    root_dict = {'name': '', 'children': []}

    for word in words:
        root_dict['children'].append(
            {'name': '', 'children': [{'name': word, 'size': 40000}]})

    return jsonify(root_dict)


@app.route('/d3word.json')
def generate_word_d3():

    word = request.args.get("word")
    clusters = TermCluster.get_top_clusters(word, n=25)

    root_dict = {'name': '', 'children': []}

    for cluster in clusters:
        root_dict['children'].append(
            {'name': cluster, 'children': [{'name': word, 'size': 40000}]})

    return jsonify(root_dict)


@app.route('/d3.json')
def generate_d3(radius=3):
    """ Returns JSON with xyz at the root node.

    Test with parameters: 40, -45, -25    (Fusiform face area)
    """

    clicked_on = request.args.get("options")

    if clicked_on == 'location':

        x_coord = float(request.args.get("xcoord"))
        y_coord = float(request.args.get("ycoord"))
        z_coord = float(request.args.get("zcoord"))

        pmids = Activation.get_pmids_from_xyz(x_coord, y_coord, z_coord, radius)
        scale = 70000
        # Get [(wd, freq), ...] and [wd1, wd2] for most frequent words

    elif clicked_on == 'study':

        pmid = request.args.get('pmid')
        study = Study.get_study_by_pmid(pmid)
        pmids = study.get_cluster_mates()
        scale = 30000

    terms_for_dict, words = StudyTerm.get_terms_by_pmid(pmids)
    # Optional: transform the terms
    # Get the top clusters
    top_clusters = TermCluster.get_top_clusters(words)
    # Get the cluster-word associations
    associations = TermCluster.get_word_cluster_pairs(top_clusters, words)

    # Make the root node:
    root_dict = {'name': '', 'children': []}

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

    return jsonify(root_dict)


################################################################################
#  ROUTE FOR GENERATING CITATIONS
################################################################################

@app.route('/citations.json')
def generate_citations(radius=3):
    """Returns a list of text citations associated with some location, word
    or topic (cluster)."""

    clicked_on = request.args.get("options")

    if clicked_on == 'location':
        x_coord = float(request.args.get('xcoord'))
        y_coord = float(request.args.get('ycoord'))
        z_coord = float(request.args.get('zcoord'))

        pmids = Activation.get_pmids_from_xyz(x_coord, y_coord, z_coord, radius)

    elif clicked_on == 'word':
        word = request.args.get('word')

        # Get the pmids for a word
        pmids = StudyTerm.get_pmid_by_term(word)

    elif clicked_on == 'cluster':
        cluster = request.args.get('cluster')

        # Get the words for a cluster
        # Then get the top studies for the words
        words = TermCluster.get_words_in_cluster(cluster)
        pmids = StudyTerm.get_pmid_by_term(words)

    elif clicked_on == 'study':

        pmid = request.args.get('pmid')
        study = Study.get_study_by_pmid(pmid)

        # Look for cluster-mate studies
        pmids = study.get_cluster_mates()


    citations = Study.get_references(pmids)

    return jsonify(citations)


################################################################################
#  ROUTES FOR GENERATING ACTIVATION PATTERNS IN BRAINBROWSER
################################################################################


# @app.route('/locations.json')
# def generate_locations():
#     """Returns a list of locations [(x, y, z), (x, y, z) ...]
#     associated with some word.

#     NO LONGER IN USE"""

#     word = request.args.get("word")
#     loc_ids = {word: Location.get_xyzs_from_word(word)}
#     return jsonify(loc_ids)


@app.route('/intensity')
def generate_intensity():
    """Generates an intensity data file related to some user action.

    Clear: clear the old intensity mapping
    Cluster: intensity mapping associated with a topic cluster
    Word: intensity mapping associated with a particular word
    Study: intensity mapping associated with a study cluster"""

    clicked_on = request.args.get("options")

    if clicked_on == 'clear':

        intensities_by_location = {}

    elif clicked_on == 'cluster' or clicked_on == 'word':

        if clicked_on == 'cluster':

            cluster = request.args.get('cluster')
            word = TermCluster.get_words_in_cluster(cluster)

        else:

            word = request.args.get('word')

        studies = StudyTerm.get_by_word(word)

        # Create a dictionary of {pmid: frequency} values
        frequencies_by_pmid, max_intensity = organize_frequencies_by_study(studies)
        pmids = frequencies_by_pmid.keys()

        # Get the activations for the keys of the dictionary
        activations = Activation.get_activations_from_studies(pmids)

        # Assemble the final dictionary of {location:intensity} values, scaling
        # each value as we go
        intensities_by_location = scale_frequencies_by_loc(
            activations, max_intensity, frequencies_by_pmid)

        # Then assemble the intensity map
        intensity_vals = generate_intensity_map(intensities_by_location)

        return intensity_vals

    elif clicked_on == 'study':

        pmid = request.args.get('pmid')
        study = Study.get_study_by_pmid(pmid)

        # Look for cluster-mate studies
        cluster_mates = study.get_cluster_mates()

        # Get (location, study count) tuples from db
        activations = Activation.get_location_count_from_studies(cluster_mates)

        # Scale study counts in preparation for intensity mapping
        intensities_by_location = scale_study_counts(activations)

    intensity_vals = generate_intensity_map(intensities_by_location)

    return intensity_vals


@app.route('/intensitytest')
def generate_example_intensity():
    """Returns the sample intensity data provided by Brainbrowser.

    Used for testing intensity mapping."""

    intensity_file = open('static/models/cortical-thickness.txt')
    intensity_data = ''.join(intensity_file.readlines())
    intensity_file.close()

    return intensity_data


@app.route('/colors')
def generate_color_map():
    """Retrieves a color map for Brainbrowser."""

    color_map_file = open('static/models/spectral.txt')
    color_data = ''.join(color_map_file.readlines())
    color_map_file.close()

    return color_data



################################################################################
# Helper functions
################################################################################


def organize_frequencies_by_study(studies):
    """Returns a dictionary of {PubMed ID : word frequency} values, given
    some raw data from StudyTerm table.

    Used as an intermediate lookup when building intensity map, in lieu of 
    performing a complex join query."""

    frequencies_by_pmid = {}

    # Add the {study : frequency} values to dictionary, summing by PubMed ID
    for study in studies:
        if study.pmid not in frequencies_by_pmid:
            frequencies_by_pmid[study.pmid] = study.frequency
    else:
        frequencies_by_pmid[study.pmid] += study.frequency

    # Get the maximal frequency for scaling
    max_intensity = max(frequencies_by_pmid.values())

    return frequencies_by_pmid, max_intensity


def scale_frequencies_by_loc(activations, max_intensity, frequencies_by_pmid):
    """Returns a dictionary of {location_id : scaled intensity} values.

    Intensity values are derived from word frequency metrics and scale using
    the maximal values.

    TO DO: Generate normalized intensities"""

    intensities_by_location = {}

    for activation in activations:
        intensity_to_add = frequencies_by_pmid[activation.pmid]

        if activation.location_id not in intensities_by_location:
            intensities_by_location[activation.location_id] = (
                intensity_to_add / max_intensity)
        else:
            intensities_by_location[activation.location_id] += (
                intensity_to_add / max_intensity)

    return intensities_by_location


def generate_intensity_map(intensities_by_location):
    """Returns a string with intensity values for each of 81925 surface
    locations."""

    intensity_vals = ""

    for i in range(0, 81925):

        if i not in intensities_by_location:

            intensity_vals = intensity_vals + "0\n"
        else:
            intensity_vals = intensity_vals + str(intensities_by_location[i]) + "\n"

    return intensity_vals


def scale_study_counts(activations):
    """Returns a dictionary of {location_id : scaled intensity} values.

    Intensity values are derived from study counts and scaled using the
    maximal counts.

    TO DO: Generate normalized intensities."""

    # counts = [activation[1] for activation in activations]

    # center = np.mean(np.array(counts)) - 3      # Center the distribution on 3
    # std_count = np.std(np.array(counts))        # Normalize by division by sd 

    # intensities_by_location = {}

    # for activation in activations:

    #     location_id, count = activation

    #     if std_count == 0:      # std dev is 0, so all values are at mean
    #         intensities_by_location[location_id] = 3

    #     else:
    #         if location_id not in intensities_by_location:
    #             intensities_by_location[location_id] = (
    #                 float(count)-float(center))/float(std_count)
    #         else:
    #             intensities_by_location[location_id] += (
    #                 float(count)-float(center))/float(std_count)

    # return intensities_by_location

    max_count = max(activations, key=itemgetter(1))[1]

    intensities_by_location = {}

    for activation in activations:

        location_id, count = activation

        if location_id not in intensities_by_location:
            intensities_by_location[location_id] = float(count)/float(max_count)
        else:
            intensities_by_location[location_id] += float(count)/float(max_count)

    return intensities_by_location


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    # DebugToolbarExtension(app)

    app.run()
