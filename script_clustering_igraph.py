import manager
from scipy.spatial.distance import pdist
from sklearn.metrics.pairwise import euclidean_distances
import webbrowser

c = manager.Client()
b = c.load_basket_pickle('UrbanSound8K') # Can load a basket from a search result instead

k_nn = 10 # param for k-nn graph creation


# __________________ FEATURE __________________ #
# Extract features and create similarity matrix from:
# Acoustic descriptors
b.analysis_stats = [None] * len(b) # this is because the basket is old and now analysis_stats contains None values initialy
b.add_analysis_stats()
b.remove_sounds_with_no_analysis()
d = b.extract_descriptor_stats(scale=True)
sound_similarity_matrix_d = euclidean_distances(d)
sound_similarity_matrix_d = sound_similarity_matrix_d/sound_similarity_matrix_d.max()
sound_similarity_matrix_d = 1 - sound_similarity_matrix_d

# Tags
t = b.preprocessing_tag()
for idx, tt in enumerate(t):
    b.sounds[idx].tags = tt
nlp = manager.Nlp(b)
nlp.create_sound_tag_matrix()
sound_similarity_matrix_t = nlp.return_similarity_matrix_tags(nlp.sound_tag_matrix)


# __________________ GRAPH __________________ #
# Create k-nn graphs
g_t = nlp.create_knn_graph_igraph(sound_similarity_matrix_t, k_nn)
g_d = nlp.create_knn_graph_igraph(sound_similarity_matrix_d, k_nn)

# extract undirected graphs
g_u_t = g_t.as_undirected()
g_u_d = g_d.as_undirected()

# community detection
com_t = g_u_t.community_fastgreedy()
com_d = g_u_d.community_fastgreedy()

# extract flat clustering
cc_t = com_t.as_clustering()
cc_d = com_d.as_clustering()

# extract clusters (list of ids for each cluster)
clas_t = [cc_t[i] for i in range(len(cc_t))]
clas_d = [cc_d[i] for i in range(len(cc_d))]


# ________________ EVALUATION ________________ #
list_baskets_t = [c.new_basket() for i in range(len(cc_t))]
list_baskets_d = [c.new_basket() for i in range(len(cc_d))]

for cl in range(len(clas_t)):
    for s in clas_t[cl]:
        list_baskets_t[cl].push(b.sounds[s])
for cl in range(len(clas_d)):
    for s in clas_d[cl]:
        list_baskets_d[cl].push(b.sounds[s])
               
tags_occurrences_t = [basket.tags_occurrences() for basket in list_baskets_t]
tags_occurrences_d = [basket.tags_occurrences() for basket in list_baskets_d]

normalized_tags_occurrences_t = []
normalized_tags_occurrences_d = []
                
for idx, tag_occurrence in enumerate(tags_occurrences_t):
            normalized_tags_occurrences_t.append([(t_o[0], float(t_o[1])/len(list_baskets_t[idx].sounds)) for t_o in tag_occurrence])
for idx, tag_occurrence in enumerate(tags_occurrences_d):
            normalized_tags_occurrences_d.append([(t_o[0], float(t_o[1])/len(list_baskets_d[idx].sounds)) for t_o in tag_occurrence])

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
for i in range(len(clas_t)):
        print_basket(list_baskets_t, normalized_tags_occurrences_t, i, 10)
print '\n ____________________________________________________'
print '\n Cluster tags occurrences for Acoustic based method:'
for i in range(len(clas_d)):
        print_basket(list_baskets_d, normalized_tags_occurrences_d, i, 10)

# Create html pages with sound clustered
def create_html_for_cluster(list_baskets, num_cluster):
    """Create a html with the Freesound embed"""
    # This list contains the begining and the end of the embed
    # Need to insert the id of the sound
    embed_blocks = ['<iframe frameborder="0" scrolling="no" src="https://www.freesound.org/embed/sound/iframe/', '/simple/medium/" width="481" height="86"></iframe>']

    # Create the html string
    message = """
    <html>
        <head></head>
        <body>
    """
    for idx, ids in enumerate(list_baskets[num_cluster].ids):
        message += embed_blocks[0] + str(ids) + embed_blocks[1]
        if idx > 50:
            break
    message += """
        </body>
    </html>
    """

    # Create the file
    f = open('result_cluster'+ str(num_cluster) +'.html', 'w')
    f.write(message)
    f.close()

    # Open it im the browser
    webbrowser.open_new_tab('result_cluster'+ str(num_cluster) +'.html')

for i in range(len(clas_t)):
        create_html_for_cluster(list_baskets_t, i)
