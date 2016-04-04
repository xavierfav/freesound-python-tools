lib.py
============

A library over freesound.py that helps managing sounds and analysis

The aim is to develop a tool that could help us using/analysing datas from freesound & local.

Example usage:

```
import lib
c = lib.Client() 

```
The Client from lib.py is also a FreesoundClient object, it has all the methods describe in freesound.py

```
results = c.text_search(query="dubstep",fields="id,name,previews")
c.load_sounds(results)
c.load_analysis()

```

freesound.py
============

A python client for the [Freesound](http://freesound.org) API.

Find the API documentation at http://www.freesound.org/docs/api/. Apply for an API key at http://www.freesound.org/api/apply/. 

The client automatically maps function arguments to http parameters of the API. JSON results are converted to python objects. The main object types (Sound, User, Pack) are augmented with the corresponding API calls.

Note that POST resources are not supported. Downloading full quality sounds requires Oauth2 authentication (see http://freesound.org/docs/api/authentication.html). Oauth2 authentication is supported, but you are expected to implement the workflow.


