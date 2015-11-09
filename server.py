"""Brain Odyssey server"""

from jinja2 import StrictUndefined
from model import Location,  Activation, Study, StudyTerm, Term, TermCluster, Cluster, connect_to_db
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# If you use an undefined variable in Jinja2, it raises an error.
app.jinja_env.undefined = StrictUndefined

@app.route('/')
def index():
    """Homepage."""

    return render_template('index.html')

@app.route('/d3.json')
def get_json(radius=2, scale=70000):
    """ Returns a master dictionary with xyz at the root node.

    Test with parameters: -60, 0, -30, 3    (Middle temporal gyrus)
    """

    x_coord = float(request.args.get("xcoord"))
    y_coord = float(request.args.get("ycoord"))
    z_coord = float(request.args.get("zcoord"))
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

    return jsonify(root_dict)


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    # DebugToolbarExtension(app)

    app.run()
