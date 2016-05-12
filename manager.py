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
from numpy import array
from functools import reduce
import cPickle
from urllib2 import URLError
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import subprocess
import ast

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
    The first time you authenticate, it will ask for your Freesound api key

    >>> import manager
    >>> c = manager.Client()
    Enter your api key: xxx
    Your api key as been stored in api_key.txt file
    """
    def __init__(self):
        self.oauth = ''
        self._scan_folder()
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
        results_pager = self.text_search(fields="id",page_size=150,**param)
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

    def save_pickle_basket(self, name):
        """
        Use this method to save a basket in a pickle file
        TODO : generalize this method for all cain of object...
        """
        settings = SettingsSingleton()
        if name and not (name in settings.local_baskets_pickle):
            nameFile = 'baskets_pickle/' + name
            with open(nameFile, 'w') as outfile:
                cPickle.dump(self, outfile)
            settings.local_baskets_pickle.append(name)
        else:
            overwrite = raw_input(name + ' basket already exists. Do you want to replace it ? (y/n)')
            if overwrite == 'y':
                settings.local_baskets_pickle.remove(name)
                self.save_pickle_basket(name)
            else:
                print 'Basket was not saved'

    def load_pickle_basket(self, name):
        """
        Use thise method to load a basket from a pickle (faster than recreating from json)
        TODO : generalize this method for all cain of object...
        """
        settings = SettingsSingleton()
        if name and name in settings.local_baskets_pickle:
            nameFile = 'baskets_pickle/' + name
            with open(nameFile) as infile:
                obj = cPickle.load(infile)
            return obj
        else:
            print '%s basket does not exist' % name

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
                sound = freesound.Sound(json.load(infile), self)
            return sound
        else:
            return None

    def _load_sound_freesound(self, idToLoad):
        try:
            sound = self.get_sound(idToLoad)
            return sound
        except ValueError:
            return None

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
                analysis = freesound.FreesoundObject(json.load(infile),self)
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
            os.mkdir('baskets_pickle')
        if not os.path.exists('previews'):
            os.mkdir('previews')

        # create variable with present local sounds & analysis
        # (reduce time consumption for function loading json files)
        files_sounds = os.listdir('./sounds/')
        files_analysis = os.listdir('./analysis/')
        files_baskets = os.listdir('./baskets/')
        files_baskets_pickle = os.listdir('./baskets_pickle/')

        settings = SettingsSingleton()
        settings.local_sounds = []
        settings.local_analysis = []
        settings.local_baskets = []
        settings.local_baskets_pickle = []

        for i in files_sounds:
            settings.local_sounds.append(int(i[:-5]))
        for j in files_analysis:
            settings.local_analysis.append(int(j[:-5]))
        for m in files_baskets:
            settings.local_baskets.append(m[:-5])
        for n in files_baskets_pickle:
            settings.local_baskets_pickle.append(n)
        settings.local_sounds.sort()
        settings.local_analysis.sort()

    def _init_oauth(self):
        try:
            import api_key
            client_id = api_key.client_id
            token = api_key.token
            refresh_oauth = api_key.refresh_oauth

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

        except:
            client_id = raw_input('Enter your client id: ')
            token = raw_input('Enter your api key: ')
            code = raw_input('Please go to: https://www.freesound.org/apiv2/oauth2/authorize/?client_id=' + client_id + \
                  '&response_type=code&state=xyz and enter the ginve code: ')

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
        self.set_token(self.oauth, auth_type='oauth')

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
                json_dict = json.load(infile)

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
class Basket(Client):
    """
    A basket where sounds and analysis can be loaded
    >>> b = manager.Basket()
    TODO : add comments attribute, title...
    """
    def __init__(self):
        self.sounds = []
        self.analysis = Analysis()
        self.ids = []
        self.analysis_names = []
        Client.__init__(self)

    def __add__(self, other):
        """
        Concatenate two baskets
        TODO : adapt it to new changes & make sure the order is not broken
        """
        sumBasket = self
        for i in range(len(other.sounds)):
            sumBasket.ids.append(other.ids[i])
            sumBasket.sounds.append(other.sounds[i])
        sumBasket._remove_duplicate()
        return sumBasket

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
    def push(self, sound):
        """
        >>> sound = c.my_get_sound(query='wind')
        >>> b.push(sound)

        """
        #sound.name = strip_non_ascii(sound.name)
        self.sounds.append(sound)
        self.ids.append(sound.id)

    def remove(self, index_list):
        for i in index_list:
            del self.ids[i]
            del self.sounds[i]
            for descriptor in self.analysis_names:
                self.analysis.remove(i, descriptor)

    def update_sounds(self):
        """
        Use this method to load the sounds which ids are in the basket
        """
        nbSound = len(self.ids)
        Bar = ProgressBar(nbSound, LENGTH_BAR, 'Loading sounds')
        Bar.update(0)
        for i in range(nbSound):
            self.sounds.append(self.my_get_sound(self.ids[i]))
            Bar.update(i + 1)

    def add_analysis(self, descriptor):
        """
        Use this method to update the analysis.
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
                allFrames.append(self.my_get_analysis(self.ids[i], descriptor))
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
                allFrames.append(self.my_get_analysis(self.ids[i+nbAnalysis], nameAnalysis))

    def remove_analysis(self, descriptor):
        if descriptor in self.analysis_names:
            self.analysis.remove('all', descriptor)
            self.analysis_names.remove(descriptor)

    def load_sounds(self, results_pager):
        """
        Use this method to load all the sounds from a result pager int the basket
        this method does not take the objects from the pager but usgin my_get_sound() which return a sound with all the fields

        >>> results_pager = c.my_text_search(query='wind')
        >>> b.load_sounds(results_pager)
        """
        nbSound = results_pager.count
        numSound = 0 # for iteration
        results_pager_last = results_pager
        Bar = ProgressBar(nbSound,LENGTH_BAR,'Loading sounds')
        Bar.update(0)
        # 1st iteration                              # maybe there is a better way to iterate through pages...
        for i in results_pager:
            self.push(self.my_get_sound(i.id))
            numSound = numSound+1
            Bar.update(numSound+1)

        # next iteration
        while (numSound<nbSound):
            results_pager = results_pager_last.next_page()
            for i in results_pager:
                self.push(self.my_get_sound(i.id))
                numSound = numSound+1
                Bar.update(numSound+1)
            results_pager_last = results_pager

    def retrieve_previews(self):
        folder = './previews/'
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
        Use thise method to load a basket
        """
        self.sounds = []
        settings = SettingsSingleton()
        if name and name in settings.local_baskets:
            nameFile = 'baskets/' + name + '.json'
            with open(nameFile) as infile:
                basket = json.load(infile)
            ids = basket[0]
            nbSounds = len(ids)
            for i in range(nbSounds):
                self.ids.append(ids[i])
            self.update_sounds()
            self.analysis_names = basket[1]
            self.update_analysis()
        else:
            print '%s basket does not exist' % name


# TODO :    create a class for utilities
#
#_________________________________________________________________#
#                             UTILS                               #
#_________________________________________________________________#
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