"""
import manager
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from script_hierar_cluster_tag import *
import numpy as np

c  = manager.Client(False)
b = c.load_basket_pickle('freesoundDb') 
r = b.preprocessing_tag_description()
#r = b.preprocessing_doc2vec()

# load tags occurrences to know which are the tags most used
tags = c.load_pickle('pickles/tags_occurrences_stem.pkl')
voc = [t[0] for t in tags]

model = run_word2vec(b, r, 30)
docs = create_doc_vec(model, r)
"""

def run_word2vec(b, r, size_space):
    #learning Word2Vec
    # around 10 - 50 dimension seems to produce better results
    model = b.word2vec(r, size=size_space) # some param are hardcoded inside the function for now
    return model

def run_doc2vec(b, r, size_space):
    model = b.doc2vec(r, size=size_space)
    return model

def create_doc_vec(model, r):
    import numpy as np
    docs = []
    for d in r:
        v = np.zeros(model.vector_size)
        count = 0
        for w in d:
            try:
                v +=  model[w]
                count += 1
            except KeyError:
                pass
        v = v / count
        docs.append(v)
    return docs
                
def cluster(model, voc, nb_tags = 50):
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import dendrogram, linkage

    # constructing the data
    voc_to_test = voc[:nb_tags]
    vec_to_test = []
    for i in voc_to_test:
        vec_to_test.append(model[i])

    # Hierarchichal clustering
    # TESTED WITH single, complete, average, weighted, centroid, median, ward
    # Ward seems to give better result
    #methods = ['single', 'complete', 'average', 'weighted', 'centroid', 'median', 'ward']
    methods = ['ward']
    for method in methods:
        plt.figure()
        plt.title('Hierarchical Clustering Dendrogram %s' % method)
        Z = linkage(vec_to_test, method)
        dendrogram(
            Z,
            orientation='right',
            color_threshold=50,
            leaf_rotation=0.,
            leaf_font_size=8.,
            show_contracted=True,  # to get a distribution impression in truncated branche
            labels=voc_to_test)

    plt.show()

# k-means
def cluster2(model, voc, nb_tags = 50):
    # kmeans from : http://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_digits.html
    from sklearn import metrics
    from sklearn.cluster import KMeans
    from sklearn.datasets import load_digits
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import scale
    from time import time
    import numpy as np
    import matplotlib.pyplot as plt
    
    # constructing the data
    voc_to_test = voc[:nb_tags]
    vec_to_test = []
    for i in voc_to_test:
        vec_to_test.append(model[i])
    
    vec_to_test = np.array(vec_to_test)
    
    data = vec_to_test
    n_samples, n_features = data.shape
    n_digits = 8
    labels = [0]*n_samples
    sample_size = 300


    def bench_k_means(estimator, name, data):
        t0 = time()
        estimator.fit(data)
        print('% 9s   %.2fs    %i   %.3f   %.3f   %.3f   %.3f   %.3f    %.3f'
              % (name, (time() - t0), estimator.inertia_,
                 metrics.homogeneity_score(labels, estimator.labels_),
                 metrics.completeness_score(labels, estimator.labels_),
                 metrics.v_measure_score(labels, estimator.labels_),
                 metrics.adjusted_rand_score(labels, estimator.labels_),
                 metrics.adjusted_mutual_info_score(labels,  estimator.labels_),
                 metrics.silhouette_score(data, estimator.labels_,
                                          metric='euclidean',
                                          sample_size=sample_size)))

    bench_k_means(KMeans(init='k-means++', n_clusters=n_digits, n_init=10),
                  name="k-means++", data=data)

    bench_k_means(KMeans(init='random', n_clusters=n_digits, n_init=10),
                  name="random", data=data)

    # in this case the seeding of the centers is deterministic, hence we run the
    # kmeans algorithm only once with n_init=1
    pca = PCA(n_components=n_digits).fit(data)
    bench_k_means(KMeans(init=pca.components_, n_clusters=n_digits, n_init=1),
                  name="PCA-based",
                  data=data)
    print(79 * '_')

    ###############################################################################
    # Visualize the results on PCA-reduced data

    reduced_data = PCA(n_components=2).fit_transform(data)
    kmeans = KMeans(init='k-means++', n_clusters=n_digits, n_init=10)
    kmeans.fit(reduced_data)

    # Step size of the mesh. Decrease to increase the quality of the VQ.
    h = .02     # point in the mesh [x_min, m_max]x[y_min, y_max].

    # Plot the decision boundary. For that, we will assign a color to each
    x_min, x_max = reduced_data[:, 0].min() - 1, reduced_data[:, 0].max() + 1
    y_min, y_max = reduced_data[:, 1].min() - 1, reduced_data[:, 1].max() + 1
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))

    # Obtain labels for each point in mesh. Use last trained model.
    Z = kmeans.predict(np.c_[xx.ravel(), yy.ravel()])

    # Put the result into a color plot
    Z = Z.reshape(xx.shape)
    plt.figure(1)
    plt.clf()
    plt.imshow(Z, interpolation='nearest',
               extent=(xx.min(), xx.max(), yy.min(), yy.max()),
               cmap=plt.cm.Paired,
               aspect='auto', origin='lower')

    plt.plot(reduced_data[:, 0], reduced_data[:, 1], 'k.', markersize=4)
    # Plot the centroids as a white X
    centroids = kmeans.cluster_centers_
    plt.scatter(centroids[:, 0], centroids[:, 1],
                marker='x', s=169, linewidths=3,
                color='w', zorder=10)
    plt.title('K-means clustering on the digits dataset (PCA-reduced data)\n'
              'Centroids are marked with white cross')
    plt.xlim(x_min, x_max)
    plt.ylim(y_min, y_max)
    plt.xticks(())
    plt.yticks(())
    plt.show()

