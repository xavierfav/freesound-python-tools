manager.py
============

A library over freesound.py that helps managing sounds and analysis

The aim is to develop a tool that could help us using/analysing datas from freesound & local. Future work will focus on saving experiments with datas, such as classification.

Example usage:

```
import manager
c = manager.Client() 
```
The Client from lib.py is also a FreesoundClient object, it has all the methods describe in freesound.py

Method were created to facilitate the use of the one from freesound.py :
```
pager = c.my_text_search(query="dubstep")
sound = c.my_get_sound(23)
```
A Basket is used to store sounds and analysis :
```
b = manager.Basket()
b.load_sounds(pager)
b.update_analysis()

b.sounds
b.analysis
```

The library takes care of downloading datas from Freesound or local. It also saves sounds and analysis in local automatically.

freesound.py
============

A python client for the [Freesound](http://freesound.org) API.

Find the API documentation at http://www.freesound.org/docs/api/. Apply for an API key at http://www.freesound.org/api/apply/. 

The client automatically maps function arguments to http parameters of the API. JSON results are converted to python objects. The main object types (Sound, User, Pack) are augmented with the corresponding API calls.

Note that POST resources are not supported. Downloading full quality sounds requires Oauth2 authentication (see http://freesound.org/docs/api/authentication.html). Oauth2 authentication is supported, but you are expected to implement the workflow.


