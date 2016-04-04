"""
Upgrage of the python client for freesound

Find the API documentation at http://www.freesound.org/docs/api/.

This lib provides method for managing files and data with a local data storage
"""

import copy
import freesound
import os
import json

# Needed to remove non asci caracter in names
def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)


class Client(freesound.FreesoundClient):
    """
    Create FreesoundClient and set authentification
    
    >>> c = FreesoundClient()
    >>> c.init()
    
    """
    loaded_sounds = []
    loaded_analysis = []
    
    def __init__(self):
        try :
            temp = open('api_key.txt').read().splitlines()
            self.set_token(temp[0],"token") 
        except IOError:
            api_key = raw_input("Enter your api key: ")
            temp = open('api_key.txt', 'w')
            temp.write(api_key)
            temp.close()
            print "Your api key as been stored to api_key.txt file"
            self.__init__()
            
        
    def load_sounds(self,results_pager):
        """
        Use this method to load the sounds from a result pager in the loaded_sounds variable 
        
        >>> results_pager = c.text_search(query="wind", filter="tag:wind duration:[0 TO 30.0]", sort="rating_desc", fields="id,name,previews,analysis_frames", page_size=50)
        >>> c.load_sounds(results_pager)
        
        """
        nbSound = results_pager.count
        numSound = 0 # for iteration
        results_pager_last = results_pager
        
        # 1st iteration
        for i in results_pager:
            i.name = strip_non_ascii(i.name)
            self.loaded_sounds.append(copy.deepcopy(i))
            numSound = numSound+1
            print '\n' + str(numSound) + '/' + str(nbSound) + '\n' + str(i.name)

        # next iteration
        while (numSound<nbSound):
            results_pager = results_pager_last.next_page()
            for i in results_pager:
                i.name = strip_non_ascii(i.name)
                self.loaded_sounds.append(copy.deepcopy(i))
                numSound = numSound+1
                print '\n' + str(numSound) + '/' + str(nbSound) + '\n' + str(i.name)
            results_pager_last = results_pager
            print ' \n CHANGE PAGE \n '

    def load_analysis(self):
        """
        Use this method to load the analysis frames of the sounds previously loaded
        
        >>> c.load_analysis()
        
        TODO : load analysis frames from freesound or from local directory when possible
        
        """
        nbSound = len(self.loaded_sounds)
        numSound = 0 # for iteration
        self.loaded_analysis = [None]*nbSound
        
        while (numSound<nbSound):
            try:    
                self.loaded_analysis[numSound] = self.loaded_sounds[numSound].get_analysis_frames()
            except ValueError:
                print "Oops! JSON files not found !"
            numSound = numSound+1
            print '\n' + str(numSound) + '/' + str(nbSound) + '\n'
        
    def save_analysis_json(self):
        """
        Use this method to save previoulsy loaded analysis to json files (name:sound_id)
        Care : if the loaded sounds are not corresponding with the loaded analysis, wrong name will be given to json files...
        
        TODO : fix it to remove the care problem...
        """
        if not os.path.exists('analysis'):
            os.makedirs('analysis')
            
        numSound = 0
        nbSound = len(self.loaded_sounds)
        
        while (numSound<nbSound):
            nameFile = 'analysis/' + str(self.loaded_sounds[numSound].id) + '.json'
            if self.loaded_analysis[numSound]:
                with open(nameFile, 'w') as outfile:
                    json.dump(self.loaded_analysis[numSound].as_dict(), outfile)
            numSound = numSound+1
            print '\n' + str(numSound) + '/' + str(nbSound) + '\n'
        
    def load_analysis_json(self):
        """
        Use this method to load all analysis in a FreesoundObject from all json files
        
        TODO : add an option to also load sounds 
        """
        files = os.listdir('./analysis/')
        nbSound = len(files)
        self.loaded_analysis = [None]*nbSound
        for numSound in range(nbSound):
            with open('analysis/'+files[numSound]) as infile:
                self.loaded_analysis[numSound] = freesound.FreesoundObject(json.load(infile),self)
            print '\n' + str(numSound) + '/' + str(nbSound)  
        
        
        