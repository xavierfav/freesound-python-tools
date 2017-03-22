if __name__ == '__main__':
    import sys
    query = sys.argv[1]
    from knn_graph_clustering import *
    c = manager.Client()
    res = c.my_text_search(query=query, fields='tags')
    b = c.new_basket()
    b.load_sounds_(res)
    cluster = Cluster(basket=b, k_nn=100)
    cluster.run(feature='fusion')
    #cluster.plot()