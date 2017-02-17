"""
Upgrade of the python client for freesound

Find the API documentation at http://www.freesound.org/docs/api/.

This lib provides method for managing files and data with a local data storage
"""

import copy
import freesound
import os
import json
import ijson
import simplejson
from numpy import array
import numpy as np
from functools import reduce
import cPickle
from urllib2 import URLError
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import subprocess
import ast
from time import sleep, gmtime, strftime
import psycopg2
import requests
from math import ceil
import datetime
import csv
from sklearn import preprocessing
from scipy import spatial
import igraph as ig
import scipy
from sklearn.metrics.pairwise import cosine_similarity
import re
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from stop_words import get_stop_words
from sklearn.feature_extraction.text import TfidfVectorizer
from gensim.models.word2vec import Word2Vec
sys.path.append('/home/xavier/Documents/freesound-data/query flow') #this do not allow to 'run <script.py>' to run a script that is in the folder from ipython...
import pandas as pd
import operator
import networkx as nx

LENGTH_BAR = 30 # length of the progress bar


class SettingsSingleton(object):
    """
    Singleton object pattern to access/modify settings from everywhere
    """
    class __OnlyOne:
        def __init__(self):
            self.local_sounds = []
            self.local_analysis = []
            self.local_baskets = []
            self.local_baskets_pickle = []
            self.autoSave = True
    instance = None
    def __new__(cls): # __new__ always a classmethod
        if not SettingsSingleton.instance:
            SettingsSingleton.instance = SettingsSingleton.__OnlyOne()
        return SettingsSingleton.instance
    def __getattr__(self, name):
        return getattr(self.instance, name)
    def __setattr__(self, name):
        return setattr(self.instance, name)


#_________________________________________________________________#
#                         Client class                            #
#_________________________________________________________________#
class Client(freesound.FreesoundClient):
    """
    Create FreesoundClient and set authentication
    The first time you create a client, it will ask for your Freesound id, api key and set up authentication
    >>> import manager
    >>> c = manager.Client()
    Enter your client id: xxx
    Enter your api key: xxx
    ...

    If Freesound server is down, you can create a client without authentication:
    >>> c = manager.Client(authentication = False)
    """
    def __init__(self, authentication=True):
        self._scan_folder()
        if authentication:
            self._init_oauth()

    # ________________________________________________________________________#
    #____________________________ local folders ______________________________#

    def _local_(self, what):
        settings = SettingsSingleton()
        return getattr(settings, what)

    @property
    def local_baskets(self):
        return self._local_('local_baskets')

    @property
    def local_sounds(self):
        return self._local_('local_sounds')

    @property
    def local_analysis(self):
        return self._local_('local_analysis')

    @property
    def local_analysis_stats(self):
        return self._local_('local_analysis_stats')

    @property
    def local_baskets_pickle(self):
        return self._local_('local_baskets_pickle')

    #________________________________________________________________________#
    # __________________________ Users functions ____________________________#
    def my_text_search(self, **param):
        """
        Call text_search method from freesound.py and add all the defaults fields and page size parameters
        TODO : add default param more flexible (store in a param file - add the api_key in a .py file)

        >>> import manager
        >>> c = manager.Client()
        >>> result = c.my_text_search(query="wind")
        """
        
        fields = 'id,'
        try:
            fields += param['fields']
            param.pop('fields')
        except:
            pass
        results_pager = self.text_search(fields=fields, page_size=150, **param)
        #self.text_search(fields="id,name,url,tags,description,type,previews,filesize,bitrate,bitdepth,duration,samplerate,username,comments,num_comments,analysis_frames",page_size=150,**param)
        return results_pager

    def my_get_sound(self,idToLoad):
        """
        Use this method to get a sound from local or freesound if not in local
        >>> sound = c.my_get_sound(id)
        """
        settings = SettingsSingleton()
        if idToLoad not in settings.local_sounds:
            sound = self._load_sound_freesound(idToLoad)
            if settings.autoSave:
                self._save_sound_json(sound)  # save it
        else:
            sound = self._load_sound_json(idToLoad)

        return sound

    def my_get_sounds(self,idsToLoad):
        """
        Use this method to get many sounds from local or freesound
        """
        sounds = []
        nbSound = len(idsToLoad)
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading sounds')
        Bar.update(0)
        for i in range(nbSound):
            sounds.append(self.my_get_sound(idsToLoad[i]))
            Bar.update(i+1)

        return sounds

    def my_get_analysis(self, idToLoad, descriptor):
        """
        Use this method to get all frames from an analysis type 'descriptor'

        >>> analysis = c.my_get_analysis(id)
        """
        settings = SettingsSingleton()
        analysis = None
        if idToLoad not in settings.local_analysis:
            allAnalysis = self._load_analysis_freesound(idToLoad)
            if settings.autoSave:
                self._save_analysis_json(allAnalysis, idToLoad)
            if allAnalysis:
                splitDescriptors = descriptor.split(".")
                analysis = allAnalysis
                for desc in splitDescriptors:
                    analysis = getattr(analysis, desc)
        else:
            analysis = self._load_analysis_descriptor_json(idToLoad, descriptor)

        return analysis

    # TODO: this does not work
    def my_get_analysiss(self, idsToLoad):
        """
        TODO : adapt it to return an Analysis object
        Use this method to get many analysis from local or freesound
        """
        analysis = []
        nbAnalysis = len(idsToLoad)
        Bar = ProgressBar(nbAnalysis,LENGTH_BAR,'Loading sounds')
        Bar.update(0)
        for i in range(nbAnalysis):
            analysis.append(self.my_get_analysis(idsToLoad[i]))
            Bar.update(i+1)

        return analysis

    # TODO: dont load the sound is the sound is givent as arguement istead of the id
    def my_get_analysis_stats(self, idToLoad):
        settings = SettingsSingleton()
        analysis = None
        if idToLoad not in settings.local_analysis_stats:
            analysis = self._load_analysis_stats_freesound(idToLoad)
            if settings.autoSave:
                self._save_analysis_stats_json(analysis, idToLoad)
        else:
            analysis = self._load_analysis_stats_json(idToLoad)
        return analysis
	
    def my_get_one_analysis_stats(self, idToLoad, descriptor):
		settings = SettingsSingleton()
		analysis = None
		if idToLoad not in settings.local_analysis_stats:
			allAnalysis = self._load_analysis_stats_freesound(idToLoad)
			if settings.autoSave:
				self._save_analysis_stats_json(allAnalysis, idToLoad)
		else:
			allAnalysis = self._load_analysis_stats_json(idToLoad)
		if allAnalysis:
			splitDescriptors = descriptor.split(".")
			analysis = allAnalysis
			for desc in splitDescriptors:
				analysis = getattr(analysis, desc)
		return analysis

	
    def new_basket(self):
        """
        Create a new Basket
        """
        basket = Basket(self)
        return basket

    def load_basket_pickle(self, name):
        """
        Load a basket from pickle
        """
        settings = SettingsSingleton()
        if name and name in settings.local_baskets_pickle:
            nameFile = 'baskets_pickle/' + name
            with open(nameFile) as infile:
                obj = cPickle.load(infile)
            obj.parent_client = self
            obj._actualize()
            return obj
        else:
            print '%s basket does not exist' % name

    @staticmethod
    def save_pickle(obj, name, path=''):
        """
        Use this method to save an object with pickle
        """
        nameFile = path + name
        with open(nameFile, 'w') as outfile:
            cPickle.dump(obj, outfile)

    @staticmethod
    def load_pickle(nameFile):
        """
        Use thise method to load an object from pickle
        """
        with open(nameFile) as infile:
            obj = cPickle.load(infile)
        return obj

    @staticmethod
    def save_csv(obj, name, path='/csv/'):
        nameFile = path + name + '.csv'
        with open(nameFile, 'w') as out:
            csv_out = csv.writer(out)
            for row in obj:
                csv_out.writerow(row)


    # ________________________________________________________________________#
    # _______________________ Private functions ______________________________#
    # ____ save/load json local/Freesound, authentication, scan folder _______#

    def _save_sound_json(self, sound):
        """
        sSve a sound into a json file
        TODO : add overwrite option...
        """
        settings = SettingsSingleton()
        if sound and not(sound.id in settings.local_sounds):
            nameFile = 'sounds/' + str(sound.id) + '.json'
            with open(nameFile, 'w') as outfile:
                json.dump(sound.as_dict(), outfile)
            settings.local_sounds.append(int(sound.id))
            settings.local_sounds.sort()

    def _load_sound_json(self, idToLoad):
        """
        Load a sound from local json
        """
        settings = SettingsSingleton()
        if idToLoad in settings.local_sounds:
            nameFile = 'sounds/' + str(idToLoad) + '.json'
            with open(nameFile) as infile:
                sound = freesound.Sound(simplejson.load(infile), self)
            return sound
        else:
            return None

    def _load_sound_freesound(self, idToLoad):
        count = 0
        while 1: # maybe use decorator to add this to all function that can fail sometimes...
            count += 1
            if count > 4:
                print 'sound ' + str(idToLoad) + ' not found (tried 4 times)'
                return None
            try:
                sound = self.get_sound(idToLoad)
                return sound
            except ValueError:
                return None
            except URLError as e:
                sleep(0.5)
                print e, 'id ' + str(idToLoad)
            except freesound.FreesoundException as e:
                sleep(0.5)
                print e, 'id ' + str(idToLoad)

    def _save_analysis_json(self, analysis, idSound):
        """
        Save an analysis into a json file
        TODO : add overwrite option...
        """
        settings = SettingsSingleton()
        if analysis and not(idSound in settings.local_analysis):
            nameFile = 'analysis/' + str(idSound) + '.json'
            with open(nameFile, 'w') as outfile:
                json.dump(analysis.as_dict(), outfile)
            settings.local_analysis.append(int(idSound))
            settings.local_analysis.sort()

    def _load_analysis_json(self, idToLoad):
        """
        Load analysis from local json file
        """
        settings = SettingsSingleton()
        if idToLoad in settings.local_analysis:
            nameFile = 'analysis/' + str(idToLoad) + '.json'
            with open(nameFile) as infile:
                analysis = freesound.FreesoundObject(simplejson.load(infile),self)
            return analysis
        else:
            return None

    def _load_analysis_freesound(self, idToLoad):
        """
        Load an analysis file from Freesound database
        """
        sound = self.my_get_sound(idToLoad)
        try:
            allAnalysis = sound.get_analysis_frames()
            return allAnalysis
        except ValueError:
            return None
        except freesound.FreesoundException:
            return None
        except URLError:
            return None

    def _load_analysis_descriptor_json(self, idToLoad, descriptor):
        """
        load analysis frames of a descriptor
        TODO : add possible descriptors
        """
        analysis = []
        settings = SettingsSingleton()
        if idToLoad in settings.local_analysis:
            nameFile = 'analysis/' + str(idToLoad) + '.json'
            with open(nameFile) as infile:
                parser = ijson.items(infile, descriptor)
                analysis = []
                for i in parser:
                    analysis.append(i)
                analysis = array(analysis[0],float)
            return analysis
        else:
            return None

    def _save_analysis_stats_json(self, analysis, idSound):
        settings = SettingsSingleton()
        if analysis and not (idSound in settings.local_analysis_stats):
            nameFile = 'analysis_stats/' + str(idSound) + '.json'
            with open(nameFile, 'w') as outfile:
                json.dump(analysis.as_dict(), outfile)
            settings.local_analysis_stats.append(int(idSound))
            settings.local_analysis_stats.sort()

    def _load_analysis_stats_freesound(self, idToLoad):
        """
        Load analysis stats from Freesound
        """
        sound = self.my_get_sound(idToLoad)
        try:
            analysis = sound.get_analysis()
            return analysis
        except ValueError:
            return None
        except freesound.FreesoundException:
            return None
        except URLError:
            return None

    def _load_analysis_stats_json(self, idToLoad):
        """
        Load analysis from local json file
        """
        settings = SettingsSingleton()
        if idToLoad in settings.local_analysis_stats:
            nameFile = 'analysis_stats/' + str(idToLoad) + '.json'
            with open(nameFile) as infile:
                analysis = freesound.FreesoundObject(json.load(infile), self)
            return analysis
        else:
            return None

    @staticmethod
    def _scan_folder():
        """
        This method is used to scan all content folders
        """
        settings = SettingsSingleton()

        # Check if the storing folder are here
        if not os.path.exists('sounds'):
            os.makedirs('sounds')
        if not os.path.exists('analysis'):
            os.makedirs('analysis')
        if not os.path.exists('baskets'):
            os.makedirs('baskets')
        if not os.path.exists('baskets_pickle'):
            os.makedirs('baskets_pickle')
        if not os.path.exists('previews'):
            os.makedirs('previews')
        if not os.path.exists('analysis_stats'):
            os.makedirs('analysis_stats')

        # create variable with present local sounds & analysis
        # (reduce time consumption for function loading json files)
        files_sounds = os.listdir('./sounds/')
        files_analysis = os.listdir('./analysis/')
        files_baskets = os.listdir('./baskets/')
        files_baskets_pickle = os.listdir('./baskets_pickle/')
        files_analysis_stats = os.listdir('./analysis_stats/')

        settings = SettingsSingleton()
        settings.local_sounds = []
        settings.local_analysis = []
        settings.local_baskets = []
        settings.local_baskets_pickle = []
        settings.local_analysis_stats = []

        for i in files_sounds:
            settings.local_sounds.append(int(i[:-5]))
        for j in files_analysis:
            settings.local_analysis.append(int(j[:-5]))
        for m in files_baskets:
            settings.local_baskets.append(m[:-5])
        for n in files_baskets_pickle:
            settings.local_baskets_pickle.append(n)
        for k in files_analysis_stats:
            settings.local_analysis_stats.append(int(k[:-5]))
        settings.local_sounds.sort()
        settings.local_analysis.sort()
        settings.local_analysis_stats.sort()

    def _init_oauth(self):
        try:
            import api_key
            reload(api_key)
            client_id = api_key.client_id
            token = api_key.token
            refresh_oauth = api_key.refresh_oauth

            print ' Authenticating:\n'

            req = 'curl -X POST -d "client_id=' + client_id + '&client_secret=' + token + \
                  '&grant_type=refresh_token&refresh_token=' + refresh_oauth + '" ' + \
                  '"https://www.freesound.org/apiv2/oauth2/access_token/"'

            output = subprocess.check_output(req, shell=True)
            output = ast.literal_eval(output)
            access_oauth = output['access_token']
            refresh_oauth = output['refresh_token']

            self._write_api_key(client_id, token, access_oauth, refresh_oauth)
            self.token = token
            self.client_id = client_id
            self.access_oauth = access_oauth

        except ImportError:
            client_id = raw_input('Enter your client id: ')
            token = raw_input('Enter your api key: ')
            code = raw_input('Please go to: https://www.freesound.org/apiv2/oauth2/authorize/?client_id=' + client_id + \
                  '&response_type=code&state=xyz and enter the ginve code: ')

            print '\n Authenticating:\n'

            req = 'curl -X POST -d "client_id=' + client_id + '&client_secret=' + token + \
                  '&grant_type=authorization_code&code=' + code + '" ' + \
                  '"https://www.freesound.org/apiv2/oauth2/access_token/"'

            output = subprocess.check_output(req, shell=True)
            output = ast.literal_eval(output)
            access_oauth = output['access_token']
            refresh_oauth = output['refresh_token']

            self._write_api_key(client_id, token, access_oauth, refresh_oauth)
            self.token = token
            self.client_id = client_id
            self.access_oauth = access_oauth

        except:
            print 'Could not authenticate'
            return

        self._set_oauth()
        print '\n Congrats ! Your are now authenticated \n'
        print freesound_rocks_ascii_art

    @staticmethod
    def _write_api_key(client_id, token, access_oauth, refresh_oauth):
        file = open('api_key.py', 'w')
        file.write('client_id = "' + client_id + '"')
        file.write('\n')
        file.write('token = "' + token + '"')
        file.write('\n')
        file.write('access_oauth = "' + access_oauth + '"')
        file.write('\n')
        file.write('refresh_oauth = "' + refresh_oauth + '"')
        file.close()

    def _set_oauth(self):
        self.set_token(self.access_oauth, auth_type='oauth')

    def _set_token(self):
        self.set_token(self.token)
#_________________________________________________________________#
#                       Analysis class                            #
#_________________________________________________________________#
class Analysis():
    """
    Analysis nested object. Holds all the analysis of many sounds

    """
    def __init__(self, json_dict = None):
        if not json_dict:
            with open('analysis_template.json') as infile:
                json_dict = simplejson.load(infile)

        self.json_dict = json_dict
        def replace_dashes(d):
            for k, v in d.items():
                if "-" in k:
                    d[k.replace("-", "_")] = d[k]
                    del d[k]
                if isinstance(v, dict): replace_dashes(v)

        replace_dashes(json_dict)
        self.__dict__.update(json_dict)
        for k, v in json_dict.items():
            if isinstance(v, dict):
                self.__dict__[k] = Analysis(v)

    def rsetattr(self, attr, val):
        pre, _, post = attr.rpartition('.')
        return setattr(self.rgetattr(pre) if pre else self, post, val)

    sentinel = object()
    def rgetattr(self, attr, default=sentinel):
        if default is self.sentinel:
            _getattr = getattr
        else:
            def _getattr(obj, name):
                return getattr(obj, name, default)
        return reduce(_getattr, [self] + attr.split('.'))

    def remove(self, index, descriptor):
        if index == 'all':
            self.rsetattr(descriptor, [])
        else:
            analysis = self.rgetattr(descriptor)
            del analysis[index]


#_________________________________________________________________#
#                        Basket class                             #
#_________________________________________________________________#
class Basket:
    """
    A basket where sounds and analysis can be loaded
    >>> c = manager.Client()
    >>> b = c.new_basket()
    TODO : add comments attribute, title...
    """

    def __init__(self, client):
        self.sounds = []
        self.analysis = Analysis() # the use of the nested object is not rly good...
        self.analysis_stats = []
        self.analysis_stats_names = []
        self.ids = []
        self.analysis_names = []

        self.parent_client = client
        self._update_sound_client()

    def __add__(self, other):
        """
        Concatenate two baskets
        TODO : adapt it to new changes & make sure the order is not broken
        """
        sumBasket = copy.deepcopy(self)
        for i in range(len(other.sounds)):
            sumBasket.ids.append(other.ids[i])
            sumBasket.sounds.append(other.sounds[i])
        sumBasket._remove_duplicate()
        return sumBasket

    def __sub__(self, other):
        """
        Return a basket with elements of self that are not in other
        """
        subBasket = copy.deepcopy(self)
        idx_to_remove = [x[0] for x in enumerate(self.ids) if x[1] in other.ids]
        subBasket.remove(idx_to_remove)
        return subBasket
        
    def __len__(self):
        return len(self.ids)
         
    def _actualize(self): # used when an old basket is loaded from pickle
        if not hasattr(self, 'analysis_stats'):
            self.analysis_stats = []

    def _update_sound_client(self):
        for i, sound in enumerate(self.sounds):
            if sound is not None:
                sound.client = self.parent_client

    def _remove_duplicate(self):
        # TODO : add method to concatenate analysis in Analysis() (won't have to reload json...)
        ids_old = self.ids
        sounds_old = self.sounds
        self.ids = []
        self.sounds = []
        nbSounds = len(ids_old)
        for i in range(nbSounds):
            if ids_old[i] not in self.ids:
                self.ids.append(ids_old[i])
                self.sounds.append(sounds_old[i])
        self.update_analysis()
    
    #________________________________________________________________________#
    # __________________________ Users functions ____________________________#
    def push(self, sound, analysis_stat=None):
        """
        >>> sound = c.my_get_sound(query='wind')
        >>> b.push(sound)

        """
        #sound.name = strip_non_ascii(sound.name)
        self.sounds.append(sound)
        self.analysis_stats.append(analysis_stat)
        if sound is not None:
            self.ids.append(sound.id)      
        else:
            self.ids.append(None)

    def push_list_id(self, sounds_id):
        Bar = ProgressBar(len(sounds_id), LENGTH_BAR, 'Loading sounds')
        Bar.update(0)
        for idx, id in enumerate(sounds_id):
            sound = self.parent_client.my_get_sound(id)
            self.push(sound)
            Bar.update(idx+1)

    def remove(self, index_list):
        index_list = sorted(index_list, reverse=True)
        for i in index_list:
            del self.ids[i]
            del self.sounds[i]
            try:
                del self.analysis_stats[i]
            except IndexError:
                pass
            for descriptor in self.analysis_names:
                self.analysis.remove(i, descriptor)

    def remove_sounds_with_no_analysis(self):
        list_idx_to_remove = []
        for idx, analysis in enumerate(self.analysis_stats):
            if analysis is None:
                list_idx_to_remove.append(idx)
        self.remove(list_idx_to_remove)
                
    def update_sounds(self):
        """
        Use this method to load the sounds which ids are in the basket
        """
        nbSound = len(self.ids)
        Bar = ProgressBar(nbSound, LENGTH_BAR, 'Loading sounds')
        Bar.update(0)
        for i in range(nbSound):
            self.sounds.append(self.parent_client.my_get_sound(self.ids[i]))
            Bar.update(i+1)

    def add_analysis(self, descriptor):
        """
        Use this method to add the analysis.
        All the current loaded analysis will be erased
        All the analysis of the loaded sound ids will be loaded

        >>> results_pager = c.my_text_search(query='wind')
        >>> b.load_sounds(results_pager)
        >>> b.add_analysis('lowlevel.mfcc')
        """
        if descriptor in self.analysis_names:
            print 'The %s analysis are already loaded' % descriptor
        else:
            nbSound = len(self.ids)
            allFrames = []
            Bar = ProgressBar(nbSound,LENGTH_BAR, 'Loading ' + descriptor + ' analysis')
            Bar.update(0)
            for i in range(nbSound):
                allFrames.append(self.parent_client.my_get_analysis(self.ids[i], descriptor))
                Bar.update(i+1)
            self.analysis_names.append(descriptor)
            self.analysis.rsetattr(descriptor, allFrames)

    def update_analysis(self):
        for nameAnalysis in self.analysis_names:
            allFrames = self.analysis.rgetattr(nameAnalysis)
            nbAnalysis = len(allFrames)
            nbAnalysisToLoad = len(self.ids) - nbAnalysis
            Bar = ProgressBar(nbAnalysisToLoad, LENGTH_BAR, 'Loading ' + nameAnalysis + ' analysis')
            Bar.update(0)
            for i in range(nbAnalysisToLoad):
                Bar.update(i + 1)
                allFrames.append(self.parent_client.my_get_analysis(self.ids[i+nbAnalysis], nameAnalysis))

    def add_analysis_stats(self):
        """
        Use this method to add all analysis stats to all sounds in the basket
        (means and var of descriptors)
        """
        #self.analysis_stats = []
        nbSounds = len(self.sounds)
        Bar = ProgressBar(nbSounds, LENGTH_BAR, 'Loading analysis stats')
        Bar.update(0)
        for i, sound in enumerate(self.sounds):
            Bar.update(i + 1)
            if sound is not None:
                analysis = self.parent_client.my_get_analysis_stats(sound.id)
                self.analysis_stats[i] = analysis
            else:
                self.analysis_stats[i] = None # HERE CHANGED APPEND TO I, is it ok ?
                # try:
                #     self.analysis_stats.append(sound.get_analysis())
                # except freesound.FreesoundException:
                #     pass

	# FUNCTION FOR ADDING STATS OF ONLY ONE ANALYSIS
    def add_one_analysis_stats(self, descriptor):
        nbSounds = len(self.sounds)
        Bar = ProgressBar(nbSounds, LENGTH_BAR, 'Loading analysis stats')
        Bar.update(0)
        for i, sound in enumerate(self.sounds):
            Bar.update(i + 1)
            if sound is not None:
                analysis = self.parent_client.my_get_one_analysis_stats(sound.id, descriptor)
                self.analysis_stats[i] = analysis
            else:
                self.analysis_stats[i] = None
		
		
    def remove_analysis(self, descriptor):
        if descriptor in self.analysis_names:
            self.analysis.remove('all', descriptor)
            self.analysis_names.remove(descriptor)

    def load_sounds_(self, results_pager, begin_idx=0, debugger=None):
        """ 
        IN PROGRESS
        This function is used when the data to load in the basket is in the pager (and not just the id like for the next function)
        """
        nbSound = results_pager.count
        numSound = begin_idx # for iteration
        results_pager_last = results_pager
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading sounds')
        Bar.update(0)
        # 1st iteration                              # maybe there is a better way to iterate through pages...
        for sound in results_pager:
            self.push(sound, sound.analysis)
            numSound = numSound+1
            Bar.update(numSound+1)

        # next iteration
        while (numSound<nbSound):
            count = 0
            while 1: # care with this infinite loop...
                count += 1
                if count>10: # MAYBE SOME BUG HERE
                    print 'could not get more sounds'
                    break
                try:
                    results_pager = results_pager_last.next_page()
                    if debugger:
                        debugger.append(results_pager)
                    break
                except:
                    exc_info = sys.exc_info()
                    sleep(1)
                    print exc_info
            for sound in results_pager:
                self.push(sound, sound.analysis)
                numSound = numSound+1
                Bar.update(numSound+1)
            results_pager_last = results_pager

    def extract_descriptor_stats(self, scale=False):
        """
        Returns a list of the scaled and concatenated descriptor stats - mean and var (all the one that are loaded in the Basket) for all sounds in the Basket.
        """
        feature_vector = []
        for analysis_stats in self.analysis_stats:
            feature_vector_single_sound = []
            for k, v in analysis_stats.as_dict().iteritems():
                if k == 'lowlevel':
                    for k_, v_ in v.iteritems():
                        try: # some lowlevel descriptors do not have 'mean' 'var' field (eg average_loudness)    
                            # barkbands_kurtosis has 0 variance and that bring dvar and dvar2 to be None...
                            if isinstance(v_['mean'], list):
                                feature_vector_single_sound += v_['mean'] # take the mean
                                feature_vector_single_sound += v_['dmean']
                                feature_vector_single_sound += v_['dmean2']
                                feature_vector_single_sound += v_['var'] # var
                                feature_vector_single_sound += v_['dvar']
                                feature_vector_single_sound += v_['dvar2']                                
                            elif isinstance(v_['mean'], float):
                                feature_vector_single_sound.append(v_['mean']) # for non array
                                feature_vector_single_sound.append(v_['dmean'])
                                feature_vector_single_sound.append(v_['dmean2'])
                                feature_vector_single_sound.append(v_['var'])
                                if k_ != 'barkbands_kurtosis': # this descriptor has variance = 0 => produce None values for dvar and dvar2
                                    feature_vector_single_sound.append(v_['dvar'])
                                    feature_vector_single_sound.append(v_['dvar2'])
                        except: # here we suppose that v_ is already a number to be stored 
                            if isinstance(v_, list):
                                feature_vector_single_sound += v_
                            elif isinstance(v_, float):
                                feature_vector_single_sound.append(v_)
                elif k == 'other cat of descriptors':
                    # sfx, tonal, rhythm
                    pass
            feature_vector.append(feature_vector_single_sound)
        if scale:  
            return preprocessing.scale(feature_vector)
        else:
            return feature_vector
        
    def extract_one_descriptor_stats(self, scale=False):
        """
        A bit dirty. Maybe review de concept of analysis_stat and analysis objects
        """
        feature_vector = []
        for analysis_stats in self.analysis_stats:
            feature_vector_single_sound = []
            if isinstance(getattr(analysis_stats,'mean'), list):
                feature_vector_single_sound += getattr(analysis_stats,'mean') # take the mean
                feature_vector_single_sound += getattr(analysis_stats,'dmean')
                feature_vector_single_sound += getattr(analysis_stats,'dmean2')
                feature_vector_single_sound += getattr(analysis_stats,'var') # var
                feature_vector_single_sound += getattr(analysis_stats,'dvar')
                feature_vector_single_sound += getattr(analysis_stats,'dvar2')                                
            elif isinstance(getattr(analysis_stats,'mean'), float):
                feature_vector_single_sound.append(getattr(analysis_stats,'mean')) # for non array
                feature_vector_single_sound.append(getattr(analysis_stats,'dmean'))
                feature_vector_single_sound.append(getattr(analysis_stats,'dmean2'))
                feature_vector_single_sound.append(getattr(analysis_stats,'var'))
                if k_ != 'barkbands_kurtosis': # this descriptor has variance = 0 => produce None values for dvar and dvar2
                    feature_vector_single_sound.append(getattr(analysis_stats,'dvar'))
                    feature_vector_single_sound.append(getattr(analysis_stats,'dvar2'))
            feature_vector.append(feature_vector_single_sound)
        if scale:  
            return preprocessing.scale(feature_vector)
        else:
            return feature_vector
        
    
    def load_sounds(self, results_pager, begin_idx=0, debugger=None):
        """
        Use this method to load all the sounds from a result pager int the basket
        this method does not take the objects from the pager but usgin my_get_sound() which return a sound with all the fields

        >>> results_pager = c.my_text_search(query='wind')
        >>> b.load_sounds(results_pager)
        """
        nbSound = results_pager.count
        numSound = begin_idx # for iteration
        results_pager_last = results_pager
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading sounds')
        Bar.update(0)
        # 1st iteration                              # maybe there is a better way to iterate through pages...
        for i in results_pager:
            self.push(self.parent_client.my_get_sound(i.id),analysis_stat=None)
            numSound = numSound+1
            Bar.update(numSound+1)

        # next iteration
        while (numSound<nbSound):
            count = 0
            while 1: # care with this infinite loop...
                count += 1
                if count>10: # MAYBE SOME BUG HERE
                    print 'could not get more sounds'
                    break
                try:
                    results_pager = results_pager_last.next_page()
                    if debugger:
                        debugger.append(results_pager)
                    break
                except:
                    exc_info = sys.exc_info()
                    sleep(1)
                    print exc_info
            for i in results_pager:
                self.push(self.parent_client.my_get_sound(i.id),analysis_stat=None)
                numSound = numSound+1
                Bar.update(numSound+1)
            results_pager_last = results_pager

    def retrieve_previews(self, new_folder = None):
        folder = './previews/'
        if new_folder is not None:
            folder += new_folder
            if not os.path.exists(folder):
                os.makedirs(folder) 
        nbSounds = len(self.sounds)
        Bar = ProgressBar(nbSounds, LENGTH_BAR, 'Downloading previews')
        Bar.update(0)
        for i in range(nbSounds):
            Bar.update(i+1)
            self.sounds[i].retrieve_preview(folder)

    def save(self, name):
        """
        Use this method to save a basket
        Only ids and analysis name(s) are saved in a list [ [id1,...idn], [analysis, ...] ]
        TODO : change it and save it as a dict (more flexible and stable regarding changes)
        """
        settings = SettingsSingleton()
        if name and not (name in settings.local_baskets):
            basket = [self.ids]
            basket.append(self.analysis_names)
            nameFile = 'baskets/' + name + '.json'
            with open(nameFile, 'w') as outfile:
                json.dump(basket, outfile)
            settings.local_baskets.append(name)
        else:
            overwrite = raw_input(name + ' basket already exists. Do you want to replace it ? (y/n)')
            if overwrite == 'y':
                settings.local_baskets.remove(name)
                self.save(name)
            else:
                print 'Basket was not saved'

    def load(self,name):
        """
        Use thise method to load a basket from json files
        """
        self.sounds = []
        settings = SettingsSingleton()
        if name and name in settings.local_baskets:
            nameFile = 'baskets/' + name + '.json'
            with open(nameFile) as infile:
                basket = simplejson.load(infile)
            ids = basket[0]
            nbSounds = len(ids)
            for i in range(nbSounds):
                self.ids.append(ids[i])
            self.update_sounds()
            self.analysis_names = basket[1]
            self.update_analysis()
        else:
            print '%s basket does not exist' % name

    def save_pickle(self, name):
        settings = SettingsSingleton()
        if name and not (name in settings.local_baskets_pickle):
            self.parent_client.save_pickle(self, name, 'baskets_pickle/')
            settings.local_baskets_pickle.append(name)
        else:
            overwrite = raw_input(name + ' basket already exists. Do you want to replace it ? (y/n)')
            if overwrite == 'y':
                self.parent_client.save_pickle(self, name, 'baskets_pickle/')
            else:
                print 'Basket was not saved'

    #________________________________________________________________________#
    # __________________________ Language tools _____________________________#
    # TODO: CREATE A CLASS FOR THIS TOOLS, AND SEPARATE FROM BASKET 
    
    def tags_occurrences(self):
        """
        Returns a list of tuples (tag, nb_occurrences, [sound ids])
        The list is sorted by number of occurrences of tags
        """
        all_tags_occurrences = []
        tags = self.tags_extract_all()
        Bar = ProgressBar(len(tags), LENGTH_BAR, 'Thinking ...')
        Bar.update(0)
        for idx, tag in enumerate(tags):
            Bar.update(idx+1)
            tag_occurrences = self.tag_occurrences(tag)
            all_tags_occurrences.append((tag, tag_occurrences[0], tag_occurrences[1]))
        all_tags_occurrences = sorted(all_tags_occurrences, key=lambda oc: oc[1])
        all_tags_occurrences.reverse()
        return all_tags_occurrences

    def terms_occurrences(self, terms_sounds):
        """
        Input: list of list of terms for each sound
        Returns a list of tuples (terms, nb_occurrences, [sound ids])
        The list is sorted by number of occurrences of tags
        Typicaly:   t = basket.preprocessing_tag_description()
                    t_o = basket.terms_occurrences(t)
                    nlp(basket, t_o) 
                    WARNING: nlp check the tags only... !!!!!!!!!!
        """
        all_terms_occurrences = []
        terms = list(set([item for sublist in terms_sounds for item in sublist]))
        Bar = ProgressBar(len(terms), LENGTH_BAR, 'Thinking ...')
        Bar.update(0)
        for idx, term in enumerate(terms):
            Bar.update(idx+1)
            term_occurrences = self.term_occurrences(terms_sounds, term)
            all_terms_occurrences.append((term, term_occurrences[0], term_occurrences[1]))
        all_terms_occurrences = sorted(all_terms_occurrences, key=lambda oc: oc[1])
        all_terms_occurrences.reverse()
        return all_terms_occurrences

    def term_occurrences(self, l, term):
        ids = []
        for i, sound_terms in enumerate(l):
            if term in sound_terms:
                ids.append(i)
        number = len(ids)
        return number, ids
        
    def tag_occurrences(self, tag):
        ids = []
        for i, sound in enumerate(self.sounds):
            if sound is not None:
                if tag in sound.tags:
                    ids.append(i)
            number = len(ids)
        return number, ids

    def description_occurrences(self, stri):
        ids = []
        for i in range(len(self.sounds)):
            if stri in self.sounds[i].description:
                ids.append(i)
        number = len(ids)
        return number, ids

    def tags_extract_all(self):
        tags = []
        Bar = ProgressBar(len(self.sounds), LENGTH_BAR, 'Extracting tags')
        Bar.update(0)
        for idx, sound in enumerate(self.sounds):
            Bar.update(idx + 1)
            if sound is not None:
                for tag in sound.tags:
                    if tag not in tags:
                        tags.append(tag)
        return tags
    
    def create_sound_tag_dict(self):
        """
        Returns a dictionary with sound id in keys and tags in values
        """
        sound_tag_dict = {}
        for sound in self.sounds:
            sound_tag_dict[sound.id] = sound.tags
        return sound_tag_dict
    
    def get_preprocessed_descriptions_word2vec(self):
        """
        Returns a list of sentences from sound descriptions in the basket.
        Preprocessing is done (remove special characters, Porter Stemming, lower case)
        """
        stemmer = PorterStemmer()
        delimiters = '.', '?', '!', ':'
        def split(delimiters, string, maxsplit=0):
            regexPattern = '|'.join(map(re.escape, delimiters))
            return re.split(regexPattern, string, maxsplit)
        
        all_descriptions = [a.description.lower() for a in self.sounds]
        sentences = []
        
        for description in all_descriptions:
            string = description.replace('\r\n', ' ')
            string = string.replace('(', ' ')
            string = string.replace(')', ' ')
            string = string.replace('*', '')
            string = string.replace('-', '')
            string = string.replace('#', '')
            string = string.replace(',', '')
            string = string.replace('/', '')
            string = re.sub('<a href(.)+>', ' ', string)
            string = split(delimiters, string)
            for string_sentence in string:
                if string_sentence is not u'':
                    terms_to_append = [stemmer.stem(a) for a in string_sentence.split()]
                    sentences.append(terms_to_append)
    
        return sentences
    
    def word2vec(self, sentences, size=50):
        from gensim.models import Word2Vec
        return Word2Vec(sentences, size=size, window=500, min_count=10, workers=8)
    
    def doc2vec(self, documents, size=50):
        """ 
        This method seems to give worse result on returning most similar terms for violin, bright
        """
        from gensim.models import Doc2Vec
        return Doc2Vec(documents, size=size, window=500, min_count=10, workers=8)
    
    def preprocessing_tag_description(self):
        """
        Preprocessing tags and descriptions
        Returns an array containing arrays of terms for each sound
        Steps for descriptions : Lower case, remove urls, Tokenization, remove stop words, Stemming (Porter)
                    tags       : Lower case, Stemming
        """
        stemmer = PorterStemmer()
        en_stop = get_stop_words('en') + ['freesound', 'org']
        
        all_descriptions = [[stemmer.stem(word) for word in CountVectorizer().build_tokenizer()(re.sub('<a href(.)+/a>', ' ', sound.description.lower())) if word not in en_stop] for sound in self.sounds]
        all_tags = [[stemmer.stem(tag.lower()) for tag in sound.tags] for sound in self.sounds]
        
        return [tag + description for tag, description in zip(all_tags, all_descriptions)]
    
    def preprocessing_tag(self):
        stemmer = PorterStemmer()
        return [[stemmer.stem(tag.lower()) for tag in sound.tags] for sound in self.sounds]
    
    def preprocessing_doc2vec(self):
        from gensim.models.doc2vec import TaggedDocument
        stemmer = PorterStemmer()
        en_stop = get_stop_words('en') + ['freesound', 'org']
        
        all_descriptions = [[stemmer.stem(word) for word in CountVectorizer().build_tokenizer()(re.sub('<a href(.)+/a>', ' ', sound.description.lower())) if word not in en_stop] for sound in self.sounds]
        all_tags = [[stemmer.stem(tag.lower()) for tag in sound.tags] for sound in self.sounds]
        
        return [TaggedDocument(words, tags) for words, tags in zip(all_descriptions, all_tags)]
        
    class TfidfEmbeddingVectorizer(object):
        def __init__(self, w2v_model):
            self.word2vec = dict(zip(w2v_model.index2word, w2v_model.syn0))
            self.word2weight = None
            self.dim = len(w2v_model.syn0[0])

        def fit(self, X, y):
            tfidf = TfidfVectorizer(analyzer=lambda x: x)
            tfidf.fit(X)
            # if a word was never seen - it must be at least as infrequent
            # as any of the known words - so the default idf is the max of 
            # known idf's
            max_idf = max(tfidf.idf_)
            self.word2weight = defaultdict(
                lambda: max_idf,
                [(w, tfidf.idf_[i]) for w, i in tfidf.vocabulary_.items()])

            return self

        def transform(self, X):
            return np.array([
                    np.mean([self.word2vec[w] * self.word2weight[w]
                             for w in words if w in self.word2vec] or
                            [np.zeros(self.dim)], axis=0)
                    for words in X
                ])

#_________________________________________________________________#
#                           NLP class                             #
#_________________________________________________________________#
class Nlp:
    """ 
    Methods for creating sparse occurrences matrix, similarity, graphs, etc...
    """
    def __init__(self, basket, tags_occurrences = None):
        if tags_occurrences:
            self.tags_occurrences = tags_occurrences
        else:
            self.tags_occurrences = basket.tags_occurrences()
        self.set_tags = [tag[0] for tag in self.tags_occurrences]
        self.freesound_sound_id = [sound.id for sound in basket.sounds]
        self.sound_tags = [sound.tags for sound in basket.sounds]
        self.inverted_tag_index = self._inverted_tag_index(self.set_tags)
        self.nb_sound = len(self.freesound_sound_id)
        self.nb_tag = len(self.set_tags)
    
    def _inverted_tag_index(self, set_tags):
        inverted_tag_index = dict()
        for idx, tag in enumerate(set_tags):
            inverted_tag_index[tag] = idx
        return inverted_tag_index   
    
    def create_sound_tag_matrix(self):
        """
        Returns scipy sparse matrix sound id / tag (2d array) - lil_matrix 
        Sounds are ordered like in the Basket (=self object)
        Tags are ordered like in the tags_occurrences list
        """
        Bar = ProgressBar(self.nb_sound, LENGTH_BAR, 'Creating matrix...')
        Bar.update(0)
        self.sound_tag_matrix = scipy.sparse.lil_matrix((self.nb_sound,self.nb_tag), dtype=int)
        for idx_sound, tags in enumerate(self.sound_tags):
            Bar.update(idx_sound+1)
            for tag in tags:
                self.sound_tag_matrix[idx_sound, self.inverted_tag_index[tag]] = 1
    
    def return_tag_cooccurrences_matrix(self):
        """
        Returns the tag to tag cooccurrences matrix by doing A_transpose * A where A is the sound to tag matrix occurrences
        """
        try:
            return self.sound_tag_matrix.transpose() * self.sound_tag_matrix      
        except:
            print 'Create fist the sound tag matrix using create_sound_tag_matrix method'
            
    @staticmethod
    def return_similarity_matrix_tags(tag_something_matrix):
        """
        Returns a tag similarity matrix computed with cosine distance from the given matrix
        MemoryError problem
        """
        tag_similarity_matrix = cosine_similarity(tag_something_matrix)
        return tag_similarity_matrix
    
    def return_my_similarity_matrix_tags(self, tag_something_matrix):
        """
        TOO SLOW !!!
        Returns a tag similarity matrix computed with cosine distance from the given matrix
        """
        size_matrix = tag_something_matrix.shape[0]
        tag_similarity_matrix = np.zeros(shape=(size_matrix,size_matrix), dtype='float32')
        Bar = ProgressBar(size_matrix*size_matrix/2, LENGTH_BAR, 'Calculating similarities...')
        Bar.update(0)
        for i0 in range(size_matrix):
            row0 = tag_something_matrix.getrow(i0).toarray()
            for i1 in range(i0):
                Bar.update(i0*size_matrix + i1 + 1)
                row1 = tag_something_matrix.getrow(i1).toarray()
                tag_similarity_matrix[i0][i1] = 1 - spatial.distance.cosine(row0, row1)
                tag_similarity_matrix[i1][i0] = tag_similarity_matrix[i0][i1]
        return tag_similarity_matrix
    
    """
    PRINT SOME SIMILARITIES BTW TAGS:
    for i in range(200):
        print str(i).ljust(10) + set_tags[i].ljust(30) + str(sim[67,i])
    """
     
    def create_tag_sound_matrix(self, tags_occurrences):
        """
        DO NOT USE THIS - TODO: implement it like sound_tag_matrix. Or just call create_sound_tag_matrix and transpose it...
        Returns a matrix tag / sound id 
        Ordered like in tags_occurrences and in the Basket (=self)
        """
        tag_sound_matrix = []
        for tag in tags_occurrences:
            sound_vect = [0] * len(self.nb_sounds)
            for sound_id_in_basket in tag[2]:
                sound_vect[sound_id_in_basket] = 1
            tag_sound_matrix.append(sound_vect)
        return tag_sound_matrix    
    
    @staticmethod
    def nearest_neighbors(similarity_matrix, idx, k):
        distances = []
        for x in range(len(similarity_matrix)):
            distances.append((x,similarity_matrix[idx][x]))
        distances.sort(key=operator.itemgetter(1), reverse=True)
        return [d[0] for d in distances[0:k]]
    
    def knn(self, similarity_matrix, idx, k, freesound_ids):
        distances = zip(freesound_ids, similarity_matrix[idx]) # zip together ids and similarity
        distances.sort(key=operator.itemgetter(1), reverse=True)
        return [d for d in distances[0:k]]
    
    def compute_knn_similarities(self, feature_matrix):
        """ 
        Created to compute all the 10000th most similar pairwise cosine similarity for FreesoundDB, text features
        Takes to much memory. Store result in db during...
        """
        sql = SQLManager('freesound_similarities')
        #dict_nn = {}
        Bar = ProgressBar(feature_matrix.shape[0], LENGTH_BAR, 'Computing similarities')
        Bar.update(0)
        bar_k = 0
        for k in range(int(np.ceil(feature_matrix.shape[0]/1000.0))):
            pairwise = cosine_similarity(feature_matrix[1000*k:1000*(k+1)], feature_matrix)
            for idx in range(pairwise.shape[0]):
                #dict_nn[self.freesound_sound_id[idx+k*1000]] = self.knn(pairwise,idx,10000)
                sql.cur.execute('insert into nearest2(freesound_id, data) values(%s, %s)', (self.freesound_sound_id[idx+k*1000], json.dumps(self.knn(pairwise,idx,10000, self.freesound_sound_id))))
                bar_k +=1
                Bar.update(bar_k)
            sql.conn.commit()
        #return dict_nn
    
    # __________________ GRAPH __________________ #
    def create_knn_graph_igraph(self, similarity_matrix, k):
        """ Returns a knn graph from a similarity matrix - igraph module """
        np.fill_diagonal(similarity_matrix, 0) # for removing the 1 from diagonal
        g = ig.Graph(directed=True)
        g.add_vertices(len(similarity_matrix))
        g.vs["b_id"] = range(len(similarity_matrix))
        for idx in range(len(similarity_matrix)):
            g.add_edges([(idx, i) for i in self.nearest_neighbors(similarity_matrix, idx, k)])
            print idx, self.nearest_neighbors(similarity_matrix, idx, k)
        return g
    
    def create_knn_graph(self, similarity_matrix, k):
        """ Returns a knn graph from a similarity matrix - NetworkX module """
        np.fill_diagonal(similarity_matrix, 0) # for removing the 1 from diagonal
        g = nx.Graph()
        g.add_nodes_from(range(len(similarity_matrix)))
        for idx in range(len(similarity_matrix)):
            g.add_edges_from([(idx, i) for i in self.nearest_neighbors(similarity_matrix, idx, k)])
            print idx, self.nearest_neighbors(similarity_matrix, idx, k)
        return g
    
    # OLD
    def create_tag_similarity_graph(self, tag_similarity_matrix, tag_names, threshold):
        """
        TODO : ADAPT IT FOR NetworkX package
        Returns the tag similarity graph (unweighted) from the tag similarity matrix
        """
        g = Graph()
        g.add_vertices(len(tag_names))
        g.vs["name"] = tag_names
        g.vs["label"] = g.vs["name"]
        for tag_i in range(len(tag_similarity_matrix)):
            for tag_j in range(len(tag_similarity_matrix)):
                if tag_i < tag_j:
                    if tag_similarity_matrix[tag_i][tag_j] > threshold:
                        g.add_edge(tag_i, tag_j)
        return g
    
    def get_centrality_from_graph(self, graph):
        return g.evcent()
    
    # TODO : ORDER TAG BY CENTRALITY
    # name_cent = [ (t[i], cent[i]) for i in range(len(t))]
    # name_cent.sort(key=lambda x: x[1], reverse=True)

    # TODO : CREATE FUNCTION FOR CREATION OF TAXONOMY
#    g2 = Graph.Tree(2,1)
#    g2.add_vertices(58978)
#    g2.vs["name"] = names
#    g2.vs["label"] = g2.vs["name"]
#    list_tags_in_tax = [0]
#
#    for idx in range(58978):
#            idx = idx + 1
#            maxCandidateVal = 0
#            for tag_1 in list_tags_in_tax:
#                    if not tag_1 == idx:
#                            if s_m_t[idx][tag_1] > maxCandidateVal:
#                                    maxCandidateVal = s_m_t[idx][tag_1]
#                                    maxCandidate = tag_1
#            if maxCandidateVal > 0.5:
#                    g2.add_edge(tag_1+1,idx+1)
#                    print 'added edge'
#                    print maxCandidateVal
#            else:
#                    g2.add_edge(0,idx+1)
#                    print 'added edge to root'
#            list_tags_in_tax.append(idx)
    
    # TODO : PUT THIS GRAPH THINGS IN AN OTHER CLASS
    
    
    
# _________________________________________________________________#
#                           SQL class                              #
# _________________________________________________________________#
class SQLManager:
    """
    This class uses psycopg2 to access psql database
    """
    def __init__(self, db_name ='freesound'):
        self.db_name = db_name          # the db had been previously imported with psql
        self.conn_text = 'dbname=' + self.db_name + ' user=xavier' # the user has been created and has access to the db
        self.connect()

    def connect(self):
        self.conn = psycopg2.connect(self.conn_text)
        self.cur = self.conn.cursor()

    def disconnect(self):
        self.cur.close()
        self.conn.close()

    def command(self, command, option = None):
        self.cur.execute(command,option)
        return self.cur.fetchall()


# _________________________________________________________________#
#                        Graylog API class                         #
# _________________________________________________________________#
class GraylogManager:

    def __init__(self):
        self.limit_item = 5000
        self.auth = self._get_auth()
        self.url = 'http://logserver.mtg.upf.edu/graylog-api/'
        self.url_search_query = '/search/universal/absolute?query=query&' \
                                            '&limit=' + str(int(self.limit_item)) + '&sort=timestamp%3Aasc&fields=message'
        self.sql = SQLManager('freesound_queries')
        self.date_last_query_in_db = self._get_date_last_query_in_db()

    def restart(self):
        self.sql.disconnect()
        self.sql = SQLManager('freesound_queries')

    def _get_auth(self):
        import graylog_auth # you need to create a py file with variable auth = (user,password)
        return graylog_auth.auth

    def _get_date_last_query_in_db(self):
        last_date = self.sql.command('select timestamp from queries3 order by id desc limit 1')
        try:
            last_date = last_date[0][0].isoformat()
            last_date = last_date[:-3]
            last_date = last_date[:-1] + str(int(last_date[-1])+1) + 'Z' # one milisec is added in order to not get the last query
        except IndexError:
            last_date = '2016-05-11T11:20:24.000Z'
        return last_date

    def _get_date_first_query_in_db(self):
        last_date = self.sql.command('select timestamp from queries3 order by timestamp asc limit 1')
        try:
            last_date = last_date[0][0].isoformat()
            last_date = last_date[:-3]
            last_date = last_date[:-1] + str(int(last_date[-1])) + 'Z'
        except IndexError:
            last_date = None
        return last_date

    def _get_last_index(self):
        try:
            last_idx = last_date = self.sql.command('select id from queries3 order by id desc limit 1')
            last_idx = last_idx[0][0]
        except IndexError:
            last_idx = -1
        return last_idx

    def _get_time(self):
        timetup = gmtime()
        return strftime('%Y-%m-%dT%H:%M:%S.000Z', timetup)

    @staticmethod
    def _request(u, auth):
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        counter = 0
        while 1:  # Loop for trying 10 times the request with 1 sec delay
            counter += 1
            if counter > 10:
                r = None
                break
            try:
                r = requests.get(u, auth=auth, headers = headers)
                break
            except Exception as e:
                print e
                sleep(1)
        return r

    def get_users_search_queries(self, from_date, to_date, offset=0):
        u = self.url + self.url_search_query + '&offset=' + str(offset) + '&'\
                                + 'from=' + str(from_date) + '&to=' \
                                + str(to_date)
        r = self._request(u, self.auth)

        # some manipulation of the data (the dict given with the graylog api request
        #                                   is really nested, it makes it a bit dirty)
        if r is not None:
            try:
                r = r.json()
            except ValueError as e:
                print 'No JSON object could be decoded'
                return [], 0
            
            total_results = r['total_results']
            r = r['messages']
            nb = len(r)
            list_queries = [(r[i]['message']['timestamp'],
                             r[i]['message']['message']) for i in range(nb)]
        else:
            list_queries = []
            total_results = 0
        return list_queries, total_results

    def get_all_search_queries(self):
        from_date = '2014-01-23T15:34:49.000Z'
        to_date = self._get_time()
        list_queries, total_results = self.get_users_search_queries(from_date, to_date)
        all_queries = list_queries
        nb_pages = int(ceil(total_results / float(self.limit_item)))
        Bar = ProgressBar(nb_pages, LENGTH_BAR, 'Requests on Graylog')
        Bar.update(0)
        for i in range(nb_pages-1):
            Bar.update(i+1)
            list_queries, total_results = self.get_users_search_queries(from_date, to_date, (i+1)*self.limit_item)
            all_queries = all_queries + list_queries
        return all_queries

    def get_new_users_search_queries(self, offset=0):
        from_date = self._get_date_last_query_in_db()
        to_date = self._get_time()
        print from_date, to_date
        list_queries, total_results = self.get_users_search_queries(from_date, to_date, offset)
        return list_queries, total_results

    def get_all_new_search_queries(self):
        list_queries, total_results = self.get_new_users_search_queries()
        all_queries = list_queries
        nb_pages = int(ceil(total_results / float(self.limit_item)))
        Bar = ProgressBar(nb_pages, LENGTH_BAR, 'Requests on Graylog')
        Bar.update(1)
        for i in range(nb_pages-1):
            list_queries, total_results = self.get_new_users_search_queries((i+1)*self.limit_item)
            all_queries = all_queries + list_queries
            Bar.update(i + 2)
        return all_queries

    @staticmethod
    def organize_all_queries(all_queries, progressbar=None):
        # there is a bug for the api queries in this fuction, return None in this case...
        # TODO USE RE HERE AND MAKE IT SIMPLE .....
        if progressbar:
            Bar = ProgressBar(len(all_queries), LENGTH_BAR, 'Organizing queries')
            Bar.update(0)
        all_queries_organized = []
        for i, item in enumerate(all_queries):
            search = item[1]
            if len(search) > 7:         # str too short means that the log is not from a search query
                if search[8] == '!':    # when it is a query from the API, there is a '!' in position 8
                    search_split = search.split(' #!# ')
                    if search_split[2] == '':   # there are two cases : One with options and one without
                        search = json.loads(search_split[1])
                    else:
                        search = json.loads(search_split[1]).update(json.loads(search_split[2]))
                    all_queries_organized.append((item[0], search, 'api'))
                elif search[:6] == 'Search':    # a query from web send a log with 'Search' (upper S)
                    search_split = json.loads(search.split('Search (')[1][:-1])
                    all_queries_organized.append((item[0], search_split, 'web'))
            if progressbar:
                Bar.update(i+1)
        return all_queries_organized

    def fill_freesound_queries_db(self, all_queries, progressbar=None):
        # db has been previously build with a 'queries' table : (id int, timestamp timestamp, data jsonb, api char(50))
        if progressbar:
            Bar = ProgressBar(len(all_queries), LENGTH_BAR, 'Filling psql db')
            Bar.update(0)
        last_idx = self._get_last_index()
        cur = self.sql.cur
        for i, item in enumerate(all_queries):
            if item[1] is not None:
                t = item[0].replace('T', ' ')
                t = t.replace('Z', '')
                idx = i + last_idx + 1
                try:
                    cur.execute('insert into queries3(timestamp, data, api) values(%s, %s, %s)',
                            (t, json.dumps(item[1]), item[2]))
                except Exception as e:
                    print e
                    self.restart()
                    cur = self.sql.cur
                    print ' One query is dropped %s' % item[1]
                    idx = idx - 1
            if progressbar:
                Bar.update(i+1)
        #self.sql.conn.commit()

    def update_freesound_queries_db(self):
        self.date_last_query_in_db = self._get_date_last_query_in_db()
        all_queries = self.get_all_new_search_queries()
        all_queries = self.organize_all_queries(all_queries)
        self.fill_freesound_queries_db(all_queries, True)

    def update_freesound_queries_db_page_by_page(self): # for big amount of data
        from_date = self._get_date_last_query_in_db()
        to_date = self._get_time()

        list_queries, total_results = self.get_users_search_queries(from_date, to_date)
        nb_pages = int(ceil(total_results / float(self.limit_item)))
        Bar = ProgressBar(nb_pages, LENGTH_BAR, 'Updating the DB')

        all_queries = self.organize_all_queries(list_queries)
        self.fill_freesound_queries_db(all_queries)
        self.sql.conn.commit()
        
        Bar.update(1)
        for i in range(nb_pages - 1):
            list_queries, total_results = self.get_users_search_queries(from_date, to_date, (i + 1) * self.limit_item)
            all_queries = self.organize_all_queries(list_queries)
            self.fill_freesound_queries_db(all_queries)
            self.sql.conn.commit()
            Bar.update(i + 2)

    def _grayDate_to_psqlDate(self, date):
        new_date = date.replace('T', ' ').replace('Z', '')
        return new_date

    def _psqlDate_to_grayDate(self, date):
        new_date = date
        new_date = new_date[:-3]
        new_date = new_date[:-1] + new_date[-1] + 'Z'
        return new_date

    def query_number_by_day(self, start_date = '2016-05-01', end_date = None):
        """
        Returns the number of queries per day
        WARNING: THE PAGE CONDITION MAY FAIL FOR OLD LOGS
        """
        if end_date == None:
            end_date = self._get_time()
        dates = np.array(pd.date_range(start = start_date, end = end_date , freq = 'D'))
        Bar = ProgressBar(len(dates)-1, LENGTH_BAR, 'Requesting DB')
        Bar.update(0)
        count_per_days = []
        for idx, d in enumerate(dates[:-1]):
            Bar.update(idx+1)
            count_per_days.append(self.sql.command("select count(*) from (select data from queries3 where timestamp > %s and timestamp < %s) as foo where data->>'page'='1'", (str(d), str(dates[idx+1]))))
        return [int(ss[0][0]) for ss in count_per_days]
    
    def query_profile_per_week(self):
        first_date = self._grayDate_to_psqlDate(self._get_date_first_query_in_db())
        last_date = self._grayDate_to_psqlDate(self._get_date_last_query_in_db())
        first_year = first_date[:4] + '-W' + '1'
        last_year = last_date[:4] + '-W' + '52'
        diff_years = int(last_year[:4]) - int(first_year[:4])
        list_weeks = []
        for i in range(diff_years+1):
            for j in range(52):
                if i == diff_years and j > int(last_year[6:]):
                    break
                list_weeks.append(str(int(first_year[:4]) + i) + '-W' + str(j+1))
        nb_query_per_week = []
        for i in range(len(list_weeks)-1):
            count = self.sql.command('select count(*) from queries3 where timestamp > %s and timestamp < %s',
                        (datetime.datetime.strptime(list_weeks[i] + '-0', "%Y-W%W-%w"),
                         datetime.datetime.strptime(list_weeks[i+1] + '-0', "%Y-W%W-%w")))
            nb_query_per_week.append(int(count[0][0]))
        return nb_query_per_week



        # TODO :    create a class for utilities
#
#_________________________________________________________________#
#                             UTILS                               #
#_________________________________________________________________#
class DictObject:
    def __init__(self, json_dict=None):
        if not json_dict:
            with open('analysis_template.json') as infile:
                json_dict = simplejson.load(infile)

        self.json_dict = json_dict

        def replace_dashes(d):
            for k, v in d.items():
                if "-" in k:
                    d[k.replace("-", "_")] = d[k]
                    del d[k]
                if isinstance(v, dict): replace_dashes(v)

        replace_dashes(json_dict)
        self.__dict__.update(json_dict)
        for k, v in json_dict.items():
            if isinstance(v, dict):
                self.__dict__[k] = DictObject(v)


class ProgressBar:
    """
    Progress bar
    """
    def __init__ (self, valmax, maxbar, title):
        if valmax == 0:  valmax = 1
        if maxbar > 200: maxbar = 200
        self.valmax = valmax
        self.maxbar = maxbar
        self.title  = title
        print ''

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
        sys.stdout.flush()


# Needed to remove non asci characters in names
def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)

freesound_rocks_ascii_art = \
"   ______                                        _   _____            _       \n \
 |  ____|                                      | | |  __ \          | |       \n \
 | |__ _ __ ___  ___  ___  ___  _   _ _ __   __| | | |__) |___   ___| | _____ \n \
 |  __| '__/ _ \/ _ \/ __|/ _ \| | | | '_ \ / _` | |  _  // _ \ / __| |/ / __| \n \
 | |  | | |  __/  __/\__ \ (_) | |_| | | | | (_| | | | \ \ (_) | (__|   <\__ \ \n \
 |_|  |_|  \___|\___||___/\___/ \__,_|_| |_|\__,_| |_|  \_\___/ \___|_|\_\___/ \n"
