"""
Upgrade of the python client for freesound

Find the API documentation at http://www.freesound.org/docs/api/.

This lib provides method for managing files and data with a local data storage
"""

import copy
import freesound
import os
import json

LENGTH_BAR = 30

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
            
    def my_text_search(self, **param):
        """
        Call text_search and add all the fields and page size and load the sounds in a variable
        
        >>> import lib
        >>> c = lib.Client()
        >>> c.my_text_search(query="wind")
        
        """
        
        results_pager = self.text_search(fields="id,name,url,tags,description,type,filesize,bitrate,bitdepth,duration,samplerate,username,comments,num_comments,analysis_frames",page_size=150,**param)
        self.load_sounds(results_pager)
        
        
    def load_sounds(self, results_pager):
        """
        Use this method to load the sounds from a result pager in the loaded_sounds variable 
        
        >>> results_pager = c.text_search(query="wind", filter="tag:wind duration:[0 TO 30.0]", sort="rating_desc", fields="id,name,previews,analysis_frames", page_size=50)
        >>> c.load_sounds(results_pager)
        
        """
        
        nbSound = results_pager.count
        numSound = 0 # for iteration
        results_pager_last = results_pager
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading sounds')
           
        # 1st iteration
        for i in results_pager:
            i.name = strip_non_ascii(i.name)
            self.loaded_sounds.append(copy.copy(i))
            numSound = numSound+1
            Bar.update(numSound+1)
            
        # next iteration
        while (numSound<nbSound):
            blockPrint()
            results_pager = results_pager_last.next_page()
            enablePrint()    
            for i in results_pager:
                i.name = strip_non_ascii(i.name)
                self.loaded_sounds.append(copy.copy(i))
                numSound = numSound+1
                Bar.update(numSound+1)
            results_pager_last = results_pager
            #print ' \n CHANGE PAGE \n '

        
    def save_sounds_json(self):
        """
        Use this method to save loaded sounds into json files
        """
        
        if not os.path.exists('sounds'):
            os.makedirs('sounds')
       
        numSound = 0
        nbSound = len(self.loaded_sounds)
        
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Saving sounds')
        
        while (numSound<nbSound):
            nameFile = 'sounds/' + str(self.loaded_sounds[numSound].id) + '.json'
            if self.loaded_sounds[numSound]:
                with open(nameFile, 'w') as outfile:
                    json.dump(self.loaded_sounds[numSound].as_dict(), outfile)
            numSound = numSound+1
            Bar.update(numSound+1)
        
    def load_sounds_json(self,idToLoad):
        """ 
        Use this method to load sounds from json files
        TODO : add param to load only certain sounds
        ADD A GENERAL JSON WHERE ALL TITLES/TAGS/ID ARE IN ORDER TO BE ABLE TO SEARCH TEXT, ...
        """
        
        if (idToLoad == 'all') :
            files = os.listdir('./sounds/')
            nbSound = len(files)
            Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading sounds')
            self.loaded_sounds = [None]*nbSound
            for numSound in range(nbSound):
                with open('sounds/'+files[numSound]) as infile:
                    self.loaded_sounds[numSound] = freesound.Sound(json.load(infile),self)
                Bar.update(numSound+1)
        else:
            nbSound = len(idToLoad)
            Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading sounds')
            self.loaded_sounds = [None]*nbSound
            for numSound in range(nbSound):
                with open('sounds/'+str(idToLoad[numSound])+'.json') as infile:
                    self.loaded_sounds[numSound] = freesound.Sound(json.load(infile),self)
                Bar.update(numSound+1)
                print ""
        
        
    def load_analysis(self):
        """
        Use this method to load the analysis frames of the sounds previously loaded
        
        >>> c.load_analysis()
        
        TODO : load analysis frames from freesound or from local directory when possible
        
        """
        
        nbSound = len(self.loaded_sounds)
        numSound = 0 # for iteration
        self.loaded_analysis = [None]*nbSound
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading analysis')
        
        while (numSound<nbSound):
            blockPrint()
            try:    
                self.loaded_analysis[numSound] = self.loaded_sounds[numSound].get_analysis_frames()
            except ValueError:
                #print "Oops! JSON files not found !"
                print ""
            enablePrint()
            numSound = numSound+1
            Bar.update(numSound+1)
        
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
        
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Saving analysis')
        
        while (numSound<nbSound):
            nameFile = 'analysis/' + str(self.loaded_sounds[numSound].id) + '.json'
            if self.loaded_analysis[numSound]:
                with open(nameFile, 'w') as outfile:
                    json.dump(self.loaded_analysis[numSound].as_dict(), outfile)
            numSound = numSound+1
            Bar.update(numSound+1)
        
    def load_analysis_json(self,idToLoad):
        """
        Use this method to load all analysis in a FreesoundObject from all json files
        idToLoad : list of sound id or 'all'
        
        """
         
        if (idToLoad == 'all'):
            files = os.listdir('./analysis/')
            nbSound = len(files)
            Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading analysis')
            self.loaded_analysis = [None]*nbSound

            for numSound in range(nbSound):
                with open('analysis/'+files[numSound]) as infile:
                    self.loaded_analysis[numSound] = freesound.FreesoundObject(json.load(infile),self)
                Bar.update(numSound+1)
            
        else:    
            nbSound = len(idToLoad)
            Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading analysis')
            self.loaded_analysis = [None]*nbSound
            for numSound in range(nbSound):
                with open('analysis/'+str(idToLoad[numSound])+'.json' ) as infile:
                    self.loaded_analysis[numSound] = freesound.FreesoundObject(json.load(infile),self)
                Bar.update(numSound+1)
            
            

    def save_json(self):
        self.save_sounds_json()
        self.save_analysis_json()
            
    def load_json(self, idToLoad):
        self.load_sounds_json(idToLoad)
        self.load_analysis_json(idToLoad)
            
            
#_________________________________________________________________#
#                             UTILS                               #
#_________________________________________________________________#
class ProgressBar:
    '''
    Progress bar
    '''
    def __init__ (self, valmax, maxbar, title):
        if valmax == 0:  valmax = 1
        if maxbar > 200: maxbar = 200
        self.valmax = valmax
        self.maxbar = maxbar
        self.title  = title
    
    def update(self, val):
        import sys
        # format
        if val > self.valmax: val = self.valmax
        
        # process
        perc  = round((float(val) / float(self.valmax)) * 100)
        scale = 100.0 / float(self.maxbar)
        bar   = int(perc / scale)
  
        # render 
        out = '\r %20s [%s%s] %3d / %3d' % (self.title, '=' * bar, ' ' * (self.maxbar - bar), val, self.valmax)
        sys.stdout.write(out)
        
# disable logging         
import sys, os
# Disable
def blockPrint():
    sys.stdout = open(os.devnull, 'w')
# Restore
def enablePrint():
    sys.stdout = sys.__stdout__


# Needed to remove non asci caracter in names
def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)
