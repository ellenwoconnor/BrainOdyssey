"""Brain Odyssey server"""

from jinja2 import StrictUndefined
from model import Location,  Activation, Study, StudyTerm, Term, TermCluster, Cluster, connect_to_db
from flask import Flask, render_template, jsonify, request


app = Flask(__name__)

# If you use an undefined variable in Jinja2, it raises an error.
app.jinja_env.undefined = StrictUndefined


################################################################################
#  HOMEPAGE ROUTE
################################################################################

@app.route('/')
def index():
    """Homepage."""

    return render_template('index.html')


################################################################################
#  ROUTE FOR CREATING JSON FOR D3
################################################################################

@app.route('/d3topic.json')
def generate_topic_d3():

    cluster_id = request.args.get("cluster_id")
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
        x_coord = float(request.args.get("xcoord"))
        y_coord = float(request.args.get("ycoord"))
        z_coord = float(request.args.get("zcoord"))

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

    citations = Study.get_references(pmids)

    return jsonify(citations)


################################################################################
#  ROUTES FOR GENERATING ACTIVATION PATTERNS IN BRAINBROWSER
################################################################################


# @app.route('/locations.json')
# def generate_locations():
#     """Returns a list of locations [(x, y, z), (x, y, z) ...]
#     associated with some word.

#     DEPRECATED - NO LONGER IN USE"""

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
    intensity_vals = ""
    activations = None

    if clicked_on == 'clear':
        for i in range(0, 81925):
            intensity_vals = intensity_vals + "0\n"

        return intensity_vals

    elif clicked_on == 'cluster':
        cluster = request.args.get('cluster')
        word = TermCluster.get_words_in_cluster(cluster)
        activations = Activation.get_activations_from_word(word)

    elif clicked_on == 'word':
        word = request.args.get('word')
        activations = Activation.get_activations_from_word(word)

    elif clicked_on == 'study':
        pmid = request.args.get('pmid')
        study = Study.get_study_by_pmid(pmid)
        cluster_mates = study.get_cluster_mates()
        activations = Activation.get_activations_from_studies(cluster_mates, pmid)

    # For each Brainbrowser index i, if there was no activation, add 0 to the string
    # If there was activation, add its frequency value.
    if activations:
        for i in range(0, 81925):
            if i not in activations:
                intensity_vals = intensity_vals + "0\n"
            else:
                intensity_vals = intensity_vals + str(activations[i]) + "\n"
    else:
        intensity_vals = None

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


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    # DebugToolbarExtension(app)

    app.run()
