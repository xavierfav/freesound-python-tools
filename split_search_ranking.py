import manager
import sys
from sklearn import cluster
import webbrowser

class SplitSearch():
    def __init__(self):
        self.c = manager.Client()

    def search(self, query):
        """Query to Freesound api, load sounds and analysis stats into a Basket"""
        self.rep = self.c.my_text_search(query=query, fields='id,name,tags,analysis', descriptors='lowlevel.mfcc.mean')
        self.b = self.c.new_basket()
        self.b.load_sounds_(self.rep)
        #self.b.add_analysis_stats()

    def extract_descriptors(self):
        # Create arrays of MFCC and Freesound sound ids ; remove sounds that do not have analysis stats
        # TODO : ADD ARGUMENT WITH DESCRIPTOR CHOICE
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

    def cluster(self, nb_cluster):
        """Aplly kmeans clustering"""
        self.kmeans = cluster.KMeans(n_clusters=nb_cluster)
        self.kmeans.fit(self.MFCCs)
        self.clas = self.kmeans.fit_predict(self.MFCCs) 
        
        # Get Freesound sound ids in relevance order and create the cluster Baskets
        self.list_baskets = [self.c.new_basket() for i in range(nb_cluster)]
        self.list_clas_ids = [[] for i in range(nb_cluster)]
        for idx, item in enumerate(self.clas):
            self.list_baskets[item].push(self.b_refined.sounds[idx])
            self.list_clas_ids[item].append(self.sound_ids[idx])
        
    def get_tags(self):
        """Get the normalized tag number of occurrences"""
        # TODO : COUNT OCCURRENCES OF TAGS IN DESCRIPTIONS ALSO
        tags_occurrences = [basket.tags_occurrences() for basket in self.list_baskets]
        self.normalized_tags_occurrences = []
        for idx, tag_occurrence in enumerate(tags_occurrences):
            self.normalized_tags_occurrences.append([(t_o[0], float(t_o[1])/len(self.list_baskets[idx].sounds)) for t_o in tag_occurrence])
    
    def print_basket(self, num_basket, max_tag = 100):
        """Print tag occurrences"""
        print '\n'
        for idx, tag in enumerate(self.normalized_tags_occurrences[num_basket]):
            if idx < max_tag:
                print tag[0].ljust(30) + str(tag[1])[0:5]
            else:
                break
    
    def create_html_for_cluster(self, num_cluster):
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
        for idx, ids in enumerate(self.list_baskets[num_cluster].ids):
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
    
    
if __name__ == '__main__':
    query = sys.argv[1]
    nb_cluster = int(sys.argv[2])
    Search = SplitSearch()
    Search.search(query)
    Search.extract_descriptors()
    Search.cluster(nb_cluster)
    Search.get_tags()
    for i in range(nb_cluster):
        Search.print_basket(i, 20)
        Search.create_html_for_cluster(i)