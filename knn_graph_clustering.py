import manager
from scipy.spatial.distance import pdist
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import webbrowser
import community.community_louvain as com
import networkx as nx
import numpy as np
import operator
import sys, os
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
from math import log10
import pylab
from sklearn import metrics
from sklearn.metrics import normalized_mutual_info_score, homogeneity_score, f1_score
import pickle
import matplotlib.patches as mpatches

# Disable print
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore print
def enablePrint():
    sys.stdout = sys.__stdout__

#text_features = pickle.load(open('text_features_FS_lda50_10kTags.pkl', 'rb'))
text_features = pickle.load(open('text_features_FS_lda200_allTags.pkl', 'rb'))
#text_features = pickle.load(open('text_features_FS.pkl', 'rb'))
#text_features = pickle.load(open('text_features_US8K_ESC50.pkl', 'rb')) 



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
        the parameter of the k nearest neighbour for graph generation. Default to 20
      
    Examples
    --------
    from knn_graph_clustering import *
    c = manager.Client()
    b = c.load_basket_pickle('UrbanSound8K')
    cluster = Cluster(basket=b)
    cluster.run()
    
    """
    def __init__(self, name='Cluster Object', basket=None, k_nn=20):
        self.name = name
        self.basket = basket
        self.k_nn = k_nn
        self.feature_type = None
        self.acoustic_features = None
        self.acoustic_similarity_matrix = None
        self.text_features = None
        self.text_similarity_matrix = None
        self.graph = None
        self.graph_knn = None
        self.nb_clusters = None
        self.ids_in_clusters = None
        self.sql = manager.SQLManager('freesound_similarities')
    
    def run(self, k_nn=None, feature='text'):
        """Run all the steps for generating cluster (by default with text features)"""
        self.graph = None
        self.graph_knn = None
        self.nb_clusters = None
        self.ids_in_clusters = None
        
        if k_nn:
            self.k_nn = k_nn
            
        if True:#not(isinstance(self.text_similarity_matrix, np.ndarray)) and not(isinstance(self.text_similarity_matrix, np.ndarray)): # do not calculate again the similarity matrix if it is already done
            self.compute_similarity_matrix(feature_type=feature)
            
        if True:#not(self.graph_knn == self.k_nn): # do not generate graph it is already done with the same k_nn parameter
            self.generate_graph()
            
        self.cluster_graph()
        self.create_cluster_baskets()
        self.display_clusters()
        if hasattr(self.basket,'clas'): # some baskets have a clas attribute where are stored labels for each sound instance
            self.evaluate()
    
    # __________________ FEATURE __________________ #
    def compute_similarity_matrix(self, basket=None, feature_type='text'):
        """
        feature_type : 'text', 'acoustic' or 'fusion'
        the type of features used for computing similarity between sounds. 
        """
        self.feature_type  = feature_type
        basket = basket or self.basket
        if basket == None:
            print 'You must provide a basket as argument'
        else:
            if feature_type == 'text' and not(isinstance(self.text_similarity_matrix, np.ndarray)):
                self.extract_text_features(basket)
                #features = [text_features[str(s.id)] for s in self.basket.sounds]
                self.create_similarity_matrix_text(self.text_features)
                #self.create_similarity_matrix_text(features)
            elif feature_type == 'acoustic' and not(isinstance(self.acoustic_similarity_matrix, np.ndarray)):
                self.extract_acoustic_features(basket)
                self.create_similarity_matrix_acoustic(self.acoustic_features)
            elif feature_type == 'fusion':
                if not(isinstance(self.acoustic_similarity_matrix, np.ndarray)):
                    self.extract_acoustic_features(basket)
                    self.create_similarity_matrix_acoustic(self.acoustic_features)
                if not(isinstance(self.text_similarity_matrix, np.ndarray)):
                    #features = [text_features[str(s.id)] for s in self.basket.sounds]
                    #self.create_similarity_matrix_text(features)
                    self.extract_text_features(basket)
                    self.create_similarity_matrix_text(self.text_features)
                # different shapes in similarity matrix means that sounds with no analysis has been discarded in the acoustic on and not in the text one. For now recompute them starting with the acoustic to clean the basket. FUTURE: store id of missing aoustic features, and do not count it in the fusion...
                if self.text_similarity_matrix.shape != self.acoustic_similarity_matrix.shape:
                    self.extract_acoustic_features(basket)
                    self.create_similarity_matrix_acoustic(self.acoustic_features)
                    #features = [text_features[str(s.id)] for s in self.basket.sounds]
                    self.extract_text_features(basket)
                    self.create_similarity_matrix_text(self.text_features)
                    #self.create_similarity_matrix_text(features)

            print '\n\n >>> Similarity Matrix Computed <<< '
    
    def load_text_features(self):
        return pickle.load(open('text_features_US8K_ESC50.pkl', 'rb'))
    
    def extract_text_features(self, basket=None):
        basket = basket or self.basket
#        t = basket.preprocessing_tag() #some stemming 
#        for idx, tt in enumerate(t):
#            basket.sounds[idx].tags = tt
        #basket.text_preprocessing()
        #t_o = basket.return_tags_occurrences()
        #nlp = manager.Nlp(basket=basket, tags_occurrences=t_o) 
        #nlp.create_sound_tag_matrix() # create the feature vectors
        #self.text_features = nlp.sound_tag_matrix
        #self.text_features = nlp.return_feature_lda(nlp.sound_tag_matrix, 20)
        #print self.text_features
        features = []
        ids_to_remove = []
        for idx, sound in enumerate(basket.sounds):
            try:
                features.append(text_features[str(sound.id)])
            except:
                ids_to_remove.append(idx)
        basket.remove(ids_to_remove)
        self.text_features = features
        
    def create_similarity_matrix_text(self, features=None):
        if features == None:
            features = self.text_features
        if features == None:
            print 'You must provide the text features as argument or run extract_text_features() first'
        else:
            self.text_similarity_matrix = cosine_similarity(features)
        
#    def extract_acoustic_features(self, basket=None):
#        """ Extract acoustic features """
#        basket = basket or self.basket
#        basket.analysis_stats = [None] * len(self.basket) # is case of the basket is old, now analysis_stats contains None values initialy
#        basket.add_analysis_stats()
#        basket.remove_sounds_with_no_analysis()
#        self.acoustic_features = basket.extract_descriptor_stats(scale=True) # list of all descriptors stats for each sound in the basket
        
    def extract_acoustic_features(self, basket=None):
        """ Extract acoustic features from database """
        basket = basket or self.basket
        features = self.get_acoustic_feature_db(basket)
        ids_to_remove = []
        basket.analysis_stats = [None] * len(basket) # is case of the basket is old, now analysis_stats contains None values initialy
        for idx in range(len(basket)):
            try:
                basket.analysis_stats[idx] = features[basket.sounds[idx].id]
            except:
                ids_to_remove.append(idx)
                basket.analysis_stats[idx] = None
        basket.remove(ids_to_remove)
        self.basket = basket
        pca = PCA(n_components=100)
        self.acoustic_features = pca.fit_transform([feature for feature in basket.analysis_stats])
    
    def get_acoustic_feature_db(self, basket):
        """ Request to db and return a dict with freesound ids and acoustic feature """
        freesound_ids_tuple = tuple(s.id for s in basket.sounds)
        result = self.sql.command('select freesound_id, data from acoustic where freesound_id in %s', (freesound_ids_tuple,))
        return {result[i][0]:result[i][1] for i in range(len(result))}
    
        
    def create_similarity_matrix_acoustic(self, features=None):
        if features == None:
            features = self.text_features
        if features == None:
            print 'You must provide the acoustic features as argument or run extract_acoustic_features() first'
        else:
            matrix = euclidean_distances(features)
            matrix = matrix/matrix.max()
            self.acoustic_similarity_matrix = 1 - matrix
            
    # __________________ GRAPH __________________ #
    def generate_graph(self, similarity_matrix=None, k_nn=None):
        blockPrint()
        k_nn = k_nn or self.k_nn
        if similarity_matrix == None:
            if self.feature_type == 'text':
                similarity_matrix = self.text_similarity_matrix
            elif self.feature_type == 'acoustic':
                similarity_matrix = self.acoustic_similarity_matrix
            elif self.feature_type == 'fusion':
                similarity_matrix = 0.8*self.text_similarity_matrix + 0.2*self.acoustic_similarity_matrix
        self.graph = self.create_knn_graph(similarity_matrix, k_nn)
        enablePrint()
        self.graph_knn = k_nn #save the k_nn parameters
        print '\n >>> Graph Generated <<< '
        
    def cluster_graph(self, graph=None):
        graph = graph or self.graph
        self.classes = com.best_partition(graph)
        self.nb_clusters = max(self.classes.values()) + 1
        #dendrogram = com.generate_dendrogram(graph)
        self.ids_in_clusters = [[e for e in self.classes.keys() if self.classes[e]==cl] for cl in range(self.nb_clusters)]
        print '\n >>> Graph Clustered <<<\n Found %d clusters'%self.nb_clusters
        
    @staticmethod
    def nearest_neighbors(similarity_matrix, idx, k):
        distances = []
        for x in range(len(similarity_matrix)):
            distances.append((x,similarity_matrix[idx][x]))
        distances.sort(key=operator.itemgetter(1), reverse=True)
        return [d[0] for d in distances[0:k]]
    
    def create_knn_graph(self, similarity_matrix, k):
        """ Returns a knn graph from a similarity matrix - NetworkX module """
        threshold = 0.1
        np.fill_diagonal(similarity_matrix, 0) # for removing the 1 from diagonal
        g = nx.Graph()
        g.add_nodes_from(range(len(similarity_matrix)))
        for idx in range(len(similarity_matrix)):
            #g.add_edges_from([(idx, i) for i in self.nearest_neighbors(similarity_matrix, idx, k) if similarity_matrix[idx][i] > threshold])
            #g.add_weighted_edges_from([(idx, i[0], i[1]) for i in zip(range(len(similarity_matrix)), similarity_matrix[idx]) if                 i[0] != idx and i[1] > threshold])
            g.add_weighted_edges_from([(idx, i, similarity_matrix[idx][i]) for i in self.nearest_neighbors(similarity_matrix, idx, k) if similarity_matrix[idx][i] > threshold])
            
            #print idx, self.nearest_neighbors(similarity_matrix, idx, k)
        return g
    
    # __________________ DISPLAY __________________ #
    def create_cluster_baskets(self):
        list_baskets = [self.basket.parent_client.new_basket() for i in range(self.nb_clusters)]
        for cl in range(len(self.ids_in_clusters)):
            for s in self.ids_in_clusters[cl]:
                list_baskets[cl].push(self.basket.sounds[s])
        self.cluster_baskets = list_baskets
        print '\n >>> Basket for each clusters created <<< '
        
    def display_clusters(self):
        tags_occurrences = [basket.tags_occurrences() for basket in self.cluster_baskets]
        normalized_tags_occurrences = []
        for idx, tag_occurrence in enumerate(tags_occurrences):
            normalized_tags_occurrences.append([(t_o[0], float(t_o[1])/len(self.cluster_baskets[idx].sounds)) for t_o in tag_occurrence])
        self.tags_oc = normalized_tags_occurrences        

        def print_basket(list_baskets, normalized_tags_occurrences, num_basket, max_tag = 20):
            """Print tag occurrences"""
            print '\n Cluster %s, containing %s sounds' % (num_basket, len(list_baskets[num_basket])) 
            for idx, tag in enumerate(normalized_tags_occurrences[num_basket]):
                if idx < max_tag:
                    print tag[0].ljust(30) + str(tag[1])[0:5]
                else:
                    break
        
        print '\n\n'
        print '\n ___________________________________________________________'
        print '|_________________________RESULTS___________________________|'
        print '\n Cluster tags occurrences (normalized):'
            
        for i in range(len(self.ids_in_clusters)):
                print_basket(self.cluster_baskets, normalized_tags_occurrences, i, 20)

    def get_labels(self):
        return [str(self.classes[k]) for k in range(len(self.classes.keys()))]
    
    def get_labels_true(self):
        return [str(e) for e in self.basket.clas]

    def plot(self):
        # create colormap
        #self.color_clusters = plt.get_cmap('jet')
        cm = plt.get_cmap('jet')
        cNorm  = colors.Normalize(vmin=0, vmax=self.nb_clusters-1)
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        self.color_clusters = cm
        
        # create legend
        patches = []
        for k in range(self.nb_clusters):
            label = 'Cluster ' + str(k)
            patches.append(mpatches.Patch(color=scalarMap.to_rgba(k), label=label))
            
        nx.draw_spring(self.graph, cmap=self.color_clusters, node_color=self.get_labels(), node_size=200, with_labels=True, alpha=0.7, width=0.3, font_size=8)
        
        plt.legend(handles=patches)
        plt.show()

    def add_color_data(self):
        cm = plt.get_cmap('jet')
        cNorm  = colors.Normalize(vmin=0, vmax=self.nb_clusters-1)
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        labels = self.get_labels()
        for idx in range(len(labels)):
            self.graph.node[idx]['viz'] = self.get_dict_color(scalarMap.to_rgba(labels[idx]))
            
    def get_dict_color(self, tuple_rgba):
        return {'color':{'r':int(tuple_rgba[0]*255), 'g':int(tuple_rgba[1]*255), 'b':int(tuple_rgba[2]*255), 'a':int(tuple_rgba[3]*255)}}
        
    def write_gexf(self, filename):
        nx.write_gexf(self.graph, filename + '.gexf')
        
    def evaluate(self):
        # the basket needs the hidden clusters information
        # basket.clas = [clas_sound_1, clas_sound_2, ...]
        all_clusters, all_hidden_clusters = construct(self, self.basket)
        self.my_homogeneity_score = homogeneity(all_clusters, all_hidden_clusters)
        
        labels_true = self.get_labels_true()
        labels = self.get_labels()
        self.homogeneity_score = homogeneity_score(labels_true, labels)
        self.nmi_score = normalized_mutual_info_score(labels_true, labels)
        self.f1_score = f1_score(labels_true, labels)
        self.scores = [self.homogeneity_score, self.nmi_score, self.f1_score]
        print '\n\n' 
        print 'Homogeneity = %s, k_nn = %s' %(self.my_homogeneity_score,self.k_nn)
        
        print 'Homogeneity = %s' %(self.homogeneity_score)
        print 'NMI = %s' %(self.nmi_score)
        print 'F1 = %s' %(self.f1_score)
        
          
    
# __________________ EVALUATION __________________ #
def construct(cluster, b):
    all_clusters = cluster.ids_in_clusters
    all_hidden_clusters = []
    for cl in range(int(max(flat_list(b.clas)))+1): 
        clust = []
        for idx, c in enumerate(b.clas):
            if int(c) == cl:
                clust.append(idx)
        all_hidden_clusters.append(clust)
    return all_clusters, all_hidden_clusters

def my_log(value):
    if value == 0:
        return 0
    else:
        return log10(value)

def purity(cluster, all_hidden_clusters):
    """ Calculate the purity of a cluster """
    purity = 0.
    for hidden_cluster in all_hidden_clusters:
        proba = prob(cluster, hidden_cluster)
        purity -= proba*my_log(proba)
    return purity

def prob(cluster, hidden_cluster):
    """ Calculate the probability of hidden_cluster knowing cluster """
    return len(intersec(cluster, hidden_cluster))/float(len(cluster))

def intersec(list1, list2):
    """ Intersection of two lists """
    return list(set(list1).intersection(set(list2)))

def flat_list(l):
    """ Convert a nested list to a flat list """
    try:
        return [item for sublist in l for item in sublist]
    except:
        return l
    
def homogeneity(all_clusters, all_hidden_clusters):
    """ Caculate the homogeneity of the found clusters with respect to the hidden clusters. Based on Entropy measure """
    total = 0.
    for cluster in all_clusters:
        total += len(cluster) * purity(cluster, all_hidden_clusters)
    total = total / (log10(len(all_hidden_clusters)) * len(flat_list(all_clusters)))
    total = 1. - total
    return total
    

##________________________________________________#                
## __________________ OLD CODE __________________ #
#
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
#
#
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

