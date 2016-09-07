import manager
import sys
from sklearn import cluster


class SplitSearch():
    def __init__(self):
        self.c = manager.Client()

    def search(self, query, nb_clusters = 2):
        # Query to Freesound api, load sounds and analysis stats into a Basket
        self.rep = self.c.my_text_search(query=query)
        self.b = self.c.new_basket()
        self.b.load_sounds(self.rep)
        self.b.add_analysis_stats()

        # Create arrays of MFCC and Freesound sound ids ; remove sounds that do not have analysis stats
        self.MFCCs = []
        self.sound_ids = []
        self.sound_ids_no_stats = []
        self.sound_ids_to_remove = []
        for idx, item in enumerate(self.b.analysis_stats):
            if item:
                self.MFCCs.append(item.lowlevel.mfcc.mean)
                self.sound_ids.append(self.b.sounds[idx].id)
            else:
                self.sound_ids_no_stats.append(self.b.sounds[idx].id)
                self.sound_ids_to_remove.append(idx)
        
        # Create a Basket with only sounds that have analysis stats 
        self.b_refined = self.b
        self.b_refined.remove(self.sound_ids_to_remove)

    def cluster(self):
        # Aplly kmeans clustering - k=2
        self.kmeans = cluster.KMeans(n_clusters=2)
        self.kmeans.fit(self.MFCCs)
        self.clas = self.kmeans.fit_predict(self.MFCCs) 
        
        # Get Freesound sound ids in relevance order and create the 2 cluster Baskets
        # TODO : Generalize for k clusters => Create an array of Baskets and iterate through clas items
        self.b0 = self.c.new_basket()
        self.b1 = self.c.new_basket()
        self.ids_0 = []
        self.ids_1 = []
        for idx, item in enumerate(self.clas):
            if item == 0:
                self.ids_0.append(self.sound_ids[idx])
                self.b0.push(self.b_refined.sounds[idx])
            elif item == 1:
                self.ids_1.append(self.sound_ids[idx])   
                self.b1.push(self.b_refined.sounds[idx])             
#        self.b0.push_list_id(self.ids_0)
#        self.b1.push_list_id(self.ids_1)
        
    def tags(self):
        # Get the normalized tag number of occurrences
        # TODO : Some for k clusters
        self.t0 = self.b0.tags_occurrences()
        self.t1 = self.b1.tags_occurrences()
        
        # Print tag occurrences
        print '\n'
        for i in range(100):
            print (self.t0[i][0].ljust(30) + str(float(self.t0[i][1])/len(self.t0))).ljust(80) + self.t1[i][0].ljust(30) + str(float(self.t1[i][1])/len(self.t1))
    
    
if __name__ == '__main__':
    query = sys.argv[1]
    Search = SplitSearch()
    Search.search(query)
    Search.cluster()
    Search.tags()
    