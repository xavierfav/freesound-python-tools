import manager
from knn_graph_clustering import Cluster

c = manager.Client(False)
b = c.load_basket_pickle('UrbanSound8K')
b2 = c.load_basket_pickle('ESC-50.pkl')

#cluster1 = Cluster(basket=b, k_nn=20)
#cluster1.run(feature='fusion')
#cluster1.plot()

#cluster1 = Cluster(basket=b, k_nn=20)
#scores_text = []
#for k in [5,6,7,8,9,10,12,14,15,20]:
#    cluster1.run(feature='text', k_nn=k)
#    scores_text.append(cluster1.scores)
#
#scores_acoustic = []
#for k in [5,6,7,8,9,10,12,14,15,20]:
#    cluster1.run(feature='acoustic', k_nn=k)
#    scores_acoustic.append(cluster1.scores)
#    
#scores_fusion = []
#for k in [5,6,7,8,9,10,12,14,15,20]:
#    cluster1.run(feature='fusion', k_nn=k)
#    scores_fusion.append(cluster1.scores)
#
#
#print scores_text
#print scores_acoustic
#print scores_fusion
#
#cluster1.plot()


cluster2 = Cluster(basket=b2, k_nn=8)

scores_text = []
for k in [5,6,7,8,9,10,12,14,15,20]:
    cluster2.run(feature='text', k_nn=k)
    scores_text.append(cluster2.scores)

#scores_acoustic = []
#for k in [5,6,7,8,9,10,12,14,15,20]:
#    cluster2.run(feature='acoustic', k_nn=k)
#    scores_acoustic.append(cluster2.scores)
#    
scores_fusion = []
for k in [5,6,7,8,9,10,12,14,15,20]:
    cluster2.run(feature='fusion', k_nn=k)
    scores_fusion.append(cluster2.scores)


print scores_text
print scores_acoustic
print scores_fusion