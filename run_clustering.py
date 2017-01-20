from script_clustering import *
c = manager.Client()
b = c.load_basket_pickle('UrbanSound8K')
cluster = Cluster(basket=b)
cluster.compute_similarity_matrix()
cluster.generate_graph()
cluster.cluster_graph()
cluster.create_cluster_baskets()
cluster.display_clusters()