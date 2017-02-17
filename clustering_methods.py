from sklearn.cluster import KMeans
from sklearn.cluster import AffinityPropagation
from sklearn.cluster import MeanShift, estimate_bandwidth
from sklearn.cluster import spectral_clustering
#from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import DBSCAN
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn import metrics
import networkx as nx
import community.community_louvain as com
import numpy as np
import operator
from sklearn.datasets.samples_generator import make_blobs
from sklearn.metrics.pairwise import euclidean_distances


def kmeans(data, n_clusters=5):
    km = KMeans(n_cluster=n_clusters, init='k-means++', max_iter=200, n_init=1)
    km.fit(data)
    return km.labels_

def affinityPropagation(data, preference=-50):
    af = AffinityPropagation(preference=preference)
    af.fit(data)
    return af.labels_

def meanShift(data):
    bandwidth = estimate_bandwidth(data, quantile=0.2)
    ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
    ms.fit(data)
    return ms.labels_

def spectral(similarity_matrix):
    labels = spectral_clustering(similarity_matrix)
    return label

def dbscan(data):
    db = DBSCAN(eps=0.3, min_samples=10)
    db.fit(data)
    return db.labels_

def agglomerative(data):
    # check here how to return the labels
    Z = linkage(data, 'Ward')
    return Z

def knnGraph(similarity_matrix, k):
    graph = create_knn_graph(similarity_matrix, k)
    classes = com.best_partition(graph)
    return [classes[k] for k in range(len(classes.keys()))]
    
def create_knn_graph(similarity_matrix, k):
    """ Returns a knn graph from a similarity matrix - NetworkX module """
    np.fill_diagonal(similarity_matrix, 0) # for removing the 1 from diagonal
    g = nx.Graph()
    g.add_nodes_from(range(len(similarity_matrix)))
    for idx in range(len(similarity_matrix)):
        g.add_edges_from([(idx, i) for i in nearest_neighbors(similarity_matrix, idx, k)])
    return g  
    
def nearest_neighbors(similarity_matrix, idx, k):
    distances = []
    for x in range(len(similarity_matrix)):
        distances.append((x,similarity_matrix[idx][x]))
    distances.sort(key=operator.itemgetter(1), reverse=True)
    return [d[0] for d in distances[0:k]]    
 
#X, y = make_blobs(n_samples=10, centers=10, n_features=2, random_state=0)
#similarity = euclidean_distances(X)

def evaluate(labels_true, labels):
    homogeneity = metrics.homogeneity_score(labels_true, labels)
    completeness = metrics.completeness_score(labels_true, labels)
    v_measure = metrics.v_measure_score(labels_true, labels)
    adjusted_rand = metrics.adjusted_rand_score(labels_true, labels)
    adjusted_mutual_info = metrics.adjusted_mutual_info_score(labels_true, labels)
    #silhouette = metrics.silhouette_score(data, labels, metric='sqeuclidean')
    return homogeneity, completeness, v_measure, adjusted_rand, adjusted_mutual_info#, silhouette

