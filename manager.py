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
from time import sleep, gmtime, strftime
import psycopg2
import requests
from math import ceil
import datetime

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
            return obj
        else:
            print '%s basket does not exist' % name

    def save_pickle(self, obj, name, path):
        """
        Use this method to save an object with pickle
        """
        nameFile = path + name
        with open(nameFile, 'w') as outfile:
            cPickle.dump(obj, outfile)

    def load_pickle(self, nameFile):
        """
        Use thise method to load an object from pickle
        """
        with open(nameFile) as infile:
            obj = cPickle.load(infile)
        return obj

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
        count = 0
        while 1: # maybe use decorator to add this to all function that can fail sometimes...
            count += 1
            if count > 10:
                print 'sound ' + str(idToLoad) + ' not found (tried 10 times)'
                return None
            try:
                sound = self.get_sound(idToLoad)
                return sound
            except ValueError:
                return None
            except URLError as e:
                sleep(1)
                print e, 'id ' + str(idToLoad)
            except freesound.FreesoundException as e:
                sleep(1)
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
class Basket:
    """
    A basket where sounds and analysis can be loaded
    >>> c = manager.Client()
    >>> b = c.new_basket()
    TODO : add comments attribute, title...
    """
    def __init__(self, client):
        self.sounds = []
        self.analysis = Analysis()
        self.ids = []
        self.analysis_names = []

        self.parent_client = client

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
            self.sounds.append(self.parent_client.my_get_sound(self.ids[i]))
            Bar.update(i+1)

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

    def remove_analysis(self, descriptor):
        if descriptor in self.analysis_names:
            self.analysis.remove('all', descriptor)
            self.analysis_names.remove(descriptor)

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
            self.push(self.parent_client.my_get_sound(i.id))
            numSound = numSound+1
            Bar.update(numSound+1)

        # next iteration
        while (numSound<nbSound):
            while 1: # care with this infinite loop...
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
                self.push(self.parent_client.my_get_sound(i.id))
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
        Use thise method to load a basket from json files
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

    def tags_occurrences(self):
        """
        Returns a list of tuples (tag, nb_occurrences, [sound ids])
        The list is sorted by number of occurrences of tags
        """
        all_tags_occurrences = []
        tags = self.tags_extract_all()
        for idx, tag in enumerate(tags):
            tag_occurrences = self.tag_occurrences(tag)
            all_tags_occurrences.append((tag, tag_occurrences[0], tag_occurrences[1]))
            all_tags_occurrences = sorted(all_tags_occurrences, key=lambda oc: oc[1])
            all_tags_occurrences.reverse()
        return all_tags_occurrences

    def tag_occurrences(self, tag):
        ids = []
        for i, sound in enumerate(self.sounds):
            if sound is not None:
                if tag in sound.tags:
                    ids.append(i)
            number = len(ids)
        return number, ids

    def description_occurrences(self, str):
        ids = []
        for i in range(len(self.sounds)):
            if str in self.sounds[i].description:
                ids.append(i)
        number = len(ids)
        return number, ids

    def tags_extract_all(self):
        tags = []
        for sound in self.sounds:
            if sound is not None:
                for tag in sound.tags:
                    if tag not in tags:
                        tags.append(tag)
        return tags

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
                                            '&limit=' + str(int(self.limit_item)) + '&sort=timestamp%3Aasc'
        self.sql = SQLManager('freesound_queries')
        self.date_last_query_in_db = self._get_date_last_query_in_db()

    def restart(self):
        self.sql.disconnect()
        self.sql = SQLManager('freesound_queries')

    def _get_auth(self):
        import graylog_auth # you need to create a py file with variable auth = (user,password)
        return graylog_auth.auth

    def _get_date_last_query_in_db(self):
        last_date = self.sql.command('select timestamp from queries1 order by timestamp desc limit 1')
        try:
            last_date = last_date[0][0].isoformat()
            last_date = last_date[:-3]
            last_date = last_date[:-1] + str(int(last_date[-1])+1) + 'Z' # one milisec is added in order to not get the last query
        except IndexError:
            last_date = '2016-05-11T11:20:24.000Z'
        return last_date

    def _get_date_first_query_in_db(self):
        last_date = self.sql.command('select timestamp from queries1 order by timestamp asc limit 1')
        try:
            last_date = last_date[0][0].isoformat()
            last_date = last_date[:-3]
            last_date = last_date[:-1] + str(int(last_date[-1])) + 'Z'
        except IndexError:
            last_date = None
        return last_date

    def _get_last_index(self):
        try:
            last_idx = last_date = self.sql.command('select id from queries1 order by id desc limit 1')
            last_idx = last_idx[0][0]
        except IndexError:
            last_idx = -1
        return last_idx

    def _get_time(self):
        timetup = gmtime()
        return strftime('%Y-%m-%dT%H:%M:%S.000Z', timetup)

    @staticmethod
    def _request(u, auth):
        counter = 0
        while 1:  # Loop for trying 10 times the request with 1 sec delay
            counter += 1
            if counter > 10:
                r = None
                break
            try:
                r = requests.get(u, auth=auth)
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
                    cur.execute('insert into queries1 values(%s, %s, %s, %s)',
                            (idx, t, json.dumps(item[1]), item[2]))
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
            count = self.sql.command('select count(*) from queries1 where timestamp > %s and timestamp < %s',
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
"   ______                                       _     _____            _		\n \
 |  ____|                                     | |   |  __ \          | |\n \
 | |__ _ __ ___  ___ ___  ___  _   _ _ __   __| |   | |__) |___   ___| | _____	\n \
 |  __| '__/ _ \/ __/ __|/ _ \| | | | '_ \ / _` |   |  _  // _ \ / __| |/ / __|	\n \
 | |  | | |  __/\__ \__ \ (_) | |_| | | | | (_| |   | | \ \ (_) | (__|   <\__ \	\n \
 |_|  |_|  \___||___/___/\___/ \__,_|_| |_|\__,_|   |_|  \_\___/ \___|_|\_\___/	\n "
