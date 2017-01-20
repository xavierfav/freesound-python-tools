import manager
from scipy.spatial.distance import pdist
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.metrics.pairwise import cosine_similarity
import webbrowser
import community.community_louvain as com
import networkx as nx
import numpy as np
import operator

#c = manager.Client()
#b = c.load_basket_pickle('UrbanSound8K') # Can load a basket from a search result instead
#b = c.load_basket_pickle('freesound_db_071216.pkl')
#
#k_nn = 200 # param for k-nn graph creation
#
#
## __________________ FEATURE __________________ #
## Extract features and create similarity matrix from:
## Acoustic descriptors
#b.analysis_stats = [None] * len(b) # this is because the basket is old and now analysis_stats contains None values initialy
#b.add_analysis_stats()
#b.remove_sounds_with_no_analysis()
#d = b.extract_descriptor_stats(scale=True)
#sound_similarity_matrix_d = euclidean_distances(d)
#sound_similarity_matrix_d = sound_similarity_matrix_d/sound_similarity_matrix_d.max()
#sound_similarity_matrix_d = 1 - sound_similarity_matrix_d
#
## Tags
#t = b.preprocessing_tag()
#for idx, tt in enumerate(t):
#    b.sounds[idx].tags = tt
#nlp = manager.Nlp(b)
#nlp.create_sound_tag_matrix()
#sound_similarity_matrix_t = nlp.return_similarity_matrix_tags(nlp.sound_tag_matrix)
#
#
## __________________ GRAPH __________________ #
## Create k-nn graphs
#g_t = nlp.create_knn_graph(sound_similarity_matrix_t, k_nn)
#g_d = nlp.create_knn_graph(sound_similarity_matrix_d, k_nn)
#g_t.name = 'Tag knn graph'
#g_d.name = 'Audio knn graph'
#
## community detection
#cc_t = com.best_partition(g_t)
#cc_d = com.best_partition(g_d)
#nb_c_t = max(cc_t.values()) + 1
#nb_c_d = max(cc_d.values()) + 1
#
## generate dendrogram
#dendro_t = com.generate_dendrogram(g_t)
#dendro_d = com.generate_dendrogram(g_d)
#
## extract clusters (list of ids for each cluster)
#clas_t = [[e for e in cc_t.keys() if cc_t[e]==cl] for cl in range(nb_c_t)]
#clas_d = [[e for e in cc_d.keys() if cc_d[e]==cl] for cl in range(nb_c_d)]

class Cluster:
    """
    Compute the clusters with the knn-graph based clustering using Louvain aglorithm.
    
    Parameters
    ----------
    name : string, optional
        a name for the cluster (use it to store the experiment configurations)
    basket : manager.Basket
        a basket holding the sound collection to cluster
    k_nn : int
        the parameter of the k nearest neighbour for graph generation. Default to 50
    feature_type : 'text' or 'acoustic'
        the type of features used for computing similarity between sounds. 
      
    Examples
    --------
    from script_clustering import *
    c = manager.Client()
    b = c.load_basket_pickle('UrbanSound8K')
    cluster = Cluster(basket=b)
    cluster.compute_similarity_matrix()
    cluster.generate_graph()
    cluster.cluster_graph()
    cluster.create_cluster_baskets()
    cluster.display_clusters()
    
    """
    def __init__(self, name='Cluster Object', basket=None, k_nn=50):
        self.name = name
        self.basket = basket
        self.k_nn = k_nn
        self.feature_type = None
        self.acoustic_features = None
        self.acoustic_similarity_matrix = None
        self.text_features = None
        self.text_similarity_matrix = None
        self.graph = None
        self.nb_clusters = None
        self.ids_in_clusters = None
    
    def compute_similarity_matrix(self, basket=None, feature_type='text'):
        self.feature_type  = feature_type
        basket = basket or self.basket
        if basket == None:
            print 'You must provide a basket as argument'
        else:
            if feature_type == 'text':
                self.extract_text_features(basket)
                self.create_similarity_matrix_text(self.text_features)
            elif feature_type == 'acoustic':
                self.extract_acoustic_features(basket)
                self.create_similarity_matrix_acoustic(self.acoustic_features)
                
    def extract_text_features(self, basket=None):
        basket = basket or self.basket
        t = basket.preprocessing_tag() #some stemming 
        for idx, tt in enumerate(t):
            basket.sounds[idx].tags = tt
        nlp = manager.Nlp(basket) # counting terms...
        nlp.create_sound_tag_matrix() # create the feature vectors
        self.text_features = nlp.sound_tag_matrix
        
    def create_similarity_matrix_text(self, features=None):
        if features == None:
            features = self.text_features
        if features == None:
            print 'You must provide the text features as argument or run extract_text_features() first'
        else:
            self.text_similarity_matrix = cosine_similarity(features)
        
    def extract_acoustic_features(self, basket=None):
        """Extract acoustic features"""
        basket = basket or self.basket
        basket.analysis_stats = [None] * len(b) # is case of the basket is old, now analysis_stats contains None values initialy
        basket.add_analysis_stats()
        basket.remove_sounds_with_no_analysis()
        self.acoustic_features = basket.extract_descriptor_stats(scale=True) # list of all descriptors stats for each sound in the basket
    
    def create_similarity_matrix_acoustic(self, features=None):
        features = features or self.acoustic_features
        if features == None:
            print 'You must provide the acoustic features as argument or run extract_acoustic_features() first'
        else:
            matrix = euclidean_distances(features)
            matrix = matrix/matrix.max()
            self.acoustic_similarity_matrix = 1 - matrix
    
    def generate_graph(self, similarity_matrix=None, k_nn=None):
        k_nn = k_nn or self.k_nn
        if similarity_matrix == None:
            if self.feature_type == 'text':
                similarity_matrix = self.text_similarity_matrix
            elif self.features_type == 'acoustic':
                similarity_matrix = self.acoustic_similarity_matrix
        self.graph = self.create_knn_graph(similarity_matrix, k_nn)
        
    def cluster_graph(self, graph=None):
        graph = graph or self.graph
        classes = com.best_partition(graph)
        self.nb_clusters = max(classes.values()) + 1
        #dendrogram = com.generate_dendrogram(graph)
        self.ids_in_clusters = [[e for e in classes.keys() if classes[e]==cl] for cl in range(self.nb_clusters)]

    @staticmethod
    def nearest_neighbors(similarity_matrix, idx, k):
        distances = []
        for x in range(len(similarity_matrix)):
            distances.append((x,similarity_matrix[idx][x]))
        distances.sort(key=operator.itemgetter(1), reverse=True)
        return [d[0] for d in distances[0:k]]
    
    def create_knn_graph(self, similarity_matrix, k):
        """ Returns a knn graph from a similarity matrix - NetworkX module """
        np.fill_diagonal(similarity_matrix, 0) # for removing the 1 from diagonal
        g = nx.Graph()
        g.add_nodes_from(range(len(similarity_matrix)))
        for idx in range(len(similarity_matrix)):
            g.add_edges_from([(idx, i) for i in self.nearest_neighbors(similarity_matrix, idx, k)])
            print idx, self.nearest_neighbors(similarity_matrix, idx, k)
        return g
    
    def create_cluster_baskets(self):
        list_baskets = [self.basket.parent_client.new_basket() for i in range(self.nb_clusters)]
        for cl in range(len(self.ids_in_clusters)):
            for s in self.ids_in_clusters[cl]:
                list_baskets[cl].push(self.basket.sounds[s])
        self.cluster_baskets = list_baskets
        
    def display_clusters(self):
        tags_occurrences = [basket.tags_occurrences() for basket in self.cluster_baskets]
        normalized_tags_occurrences = []
        for idx, tag_occurrence in enumerate(tags_occurrences):
            normalized_tags_occurrences.append([(t_o[0], float(t_o[1])/len(self.cluster_baskets[idx].sounds)) for t_o in tag_occurrence])
        
        def print_basket(list_baskets, normalized_tags_occurrences, num_basket, max_tag = 20):
            """Print tag occurrences"""
            print '\n Cluster %s, containing %s sounds' % (num_basket, len(list_baskets[num_basket])) 
            for idx, tag in enumerate(normalized_tags_occurrences[num_basket]):
                if idx < max_tag:
                    print tag[0].ljust(30) + str(tag[1])[0:5]
                else:
                    break
                    
        print '\n ____________________________________________________'
        print '\n Cluster tags occurrences for Tag based method:'
            
        for i in range(len(self.ids_in_clusters)):
                print_basket(self.cluster_baskets, normalized_tags_occurrences, i, 10)
                
                
## ________________ EVALUATION ________________ #
#list_baskets_t = [c.new_basket() for i in range(nb_c_t)]
#list_baskets_d = [c.new_basket() for i in range(nb_c_d)]
#
#for cl in range(len(clas_t)):
#    for s in clas_t[cl]:
#        list_baskets_t[cl].push(b.sounds[s])
#for cl in range(len(clas_d)):
#    for s in clas_d[cl]:
#        list_baskets_d[cl].push(b.sounds[s])
#               
#tags_occurrences_t = [basket.tags_occurrences() for basket in list_baskets_t]
#tags_occurrences_d = [basket.tags_occurrences() for basket in list_baskets_d]
#
#normalized_tags_occurrences_t = []
#normalized_tags_occurrences_d = []
#                
#for idx, tag_occurrence in enumerate(tags_occurrences_t):
#            normalized_tags_occurrences_t.append([(t_o[0], float(t_o[1])/len(list_baskets_t[idx].sounds)) for t_o in tag_occurrence])
#for idx, tag_occurrence in enumerate(tags_occurrences_d):
#            normalized_tags_occurrences_d.append([(t_o[0], float(t_o[1])/len(list_baskets_d[idx].sounds)) for t_o in tag_occurrence])
#
#def print_basket(list_baskets, normalized_tags_occurrences, num_basket, max_tag = 20):
#        """Print tag occurrences"""
#        print '\n Cluster %s, containing %s sounds' % (num_basket, len(list_baskets[num_basket])) 
#        for idx, tag in enumerate(normalized_tags_occurrences[num_basket]):
#            if idx < max_tag:
#                print tag[0].ljust(30) + str(tag[1])[0:5]
#            else:
#                break
#print '\n ____________________________________________________'
#print '\n Cluster tags occurrences for Tag based method:'
#for i in range(len(clas_t)):
#        print_basket(list_baskets_t, normalized_tags_occurrences_t, i, 10)
#print '\n ____________________________________________________'
#print '\n Cluster tags occurrences for Acoustic based method:'
#for i in range(len(clas_d)):
#        print_basket(list_baskets_d, normalized_tags_occurrences_d, i, 10)
#
## Create html pages with sound clustered
#def create_html_for_cluster(list_baskets, num_cluster):
#    """Create a html with the Freesound embed"""
#    # This list contains the begining and the end of the embed
#    # Need to insert the id of the sound
#    embed_blocks = ['<iframe frameborder="0" scrolling="no" src="https://www.freesound.org/embed/sound/iframe/', '/simple/medium/" width="481" height="86"></iframe>']
#
#    # Create the html string
#    message = """
#    <html>
#        <head></head>
#        <body>
#    """
#    for idx, ids in enumerate(list_baskets[num_cluster].ids):
#        message += embed_blocks[0] + str(ids) + embed_blocks[1]
#        if idx > 50:
#            break
#    message += """
#        </body>
#    </html>
#    """
#
#    # Create the file
#    f = open('result_cluster'+ str(num_cluster) +'.html', 'w')
#    f.write(message)
#    f.close()
#
#    # Open it im the browser
#    webbrowser.open_new_tab('result_cluster'+ str(num_cluster) +'.html')
#
#def pop_html(method):
#    if method == 't':
#        clas = clas_t
#        list_baskets = list_baskets_t
#    elif method == 'd':
#        clas = clas_d
#        list_baskets = list_baskets_d
#    for i in range(len(clas)):
#        create_html_for_cluster(list_baskets, i)
#    

