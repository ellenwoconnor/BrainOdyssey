import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer
from sklearn.decomposition import TruncatedSVD
from scipy.spatial.distance import cdist, pdist
from sklearn.cluster import KMeans

# Load data and transform to Numpy matrix

datafile = open('features.txt')
feature_names = datafile.readline()
vectorized_full = np.loadtxt(datafile)
pmids = vectorized_full[:,0]

# The data to be fed into LSA
# Row IDs, corresponding to PubMed ID, are removed, and the word frequency
# values are normalized as tf-idf values in preprocessing

# (TfidfVectorizer uses a in-memory vocabulary (a python dict) to map the most
# frequent words to features indices and hence compute a word occurrence
# frequency (sparse) matrix. The word frequencies are then reweighted using
# the Inverse Document Frequency (IDF) vector collected feature-wise over
# the corpus.)

vectorized = vectorized_full[:,1:]


#############################################################################
# Dimensionality reduction using LSA
#############################################################################

print("Performing dimensionality reduction using LSA")

# # of dimensions obtained by checking the amount of variance explained by 
# different values (e.g., 100, 200, 300 ... ). Our final analysis reduces
# the number of dimensions to 200. 

dims = input("Enter the number of dimensions desired: ")
svd = TruncatedSVD(dims)
normalizer = Normalizer(copy=False)
lsa = make_pipeline(svd, normalizer)

dims_reduced = lsa.fit_transform(vectorized)

explained_variance = svd.explained_variance_ratio_.sum()

print("Explained variance of the SVD step: {}%".format(
    int(explained_variance * 100)))

#############################################################################
# Determine optimal k via the elbow method
#############################################################################

# See http://www.learnbymarketing.com/methods/k-means-clustering/ for a helpful 
# toy example of how the resulting values are calculated under the hood. 

# The cluster numbers to consider: 
# "Choosing sqrt(n/2) is a good rule of thumb" as far as where to start, where n
# is the number of overall datapoints (in this case, ~10k). 
# An elbow graph shows that for this dataset the fit ceases to improve very much
# after about 150 clusters. 

print "Getting k-means clusters..."

k_range = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# Calculate k-means for all of the specified Ns
k_means_var = [KMeans(n_clusters=k, init='k-means++').fit(dims_reduced) for k in k_range]

# Calculate the cluster centers for each analysis
centroids = [X.cluster_centers_ for X in k_means_var]
k_euclid = [cdist(dims_reduced, cent, 'euclidean') for cent in centroids]
dist = [np.min(ke, axis=1) for ke in k_euclid]

wcss = [sum(d**2) for d in dist]  # distances to the cluster center: large # --> more variance within clusters
tss = sum(pdist(dims_reduced)**2)/dims_reduced.shape[0]  # total variance (constant)
bss = tss - wcss # Roughly, amount of variance explained by the clustering 


#############################################################################
# Perform k-means clustering after selection of optimal k 
#############################################################################

# km_final = KMeans(n_clusters=150, init='k-means++').fit(dims_reduced)

# Get the cluster IDs to verify performance:
# cluster_lookup = np.column_stack((pmids, km.labels_))