
import math
import requests
import json
from time import sleep

def remove_control_chars(text):
    return ''.join(c for c in text if (ord(c) >= 32 or ord(c) in [9,10,13]))


def convert_to_solr_document(sound):
    #logger.info("creating solr XML from sound %d" % sound.id)
    document = dict()
    document["name"] = remove_control_chars(sound.name)
    document["id"] = sound.id
    document["username"] = sound.username
    document["created"] = sound.created + 'Z'
    #document["original_filename"] = remove_control_chars(sound.original_filename)
    document["description"] = remove_control_chars(sound.description)
    document["tag"] = sound.tags #list(sound.tags.select_related("tag").values_list('tag__name', flat=True))
    document["license"] = sound.license
    document["is_remix"] = False #bool(sound.sources.count())
    document["was_remixed"] = False #bool(sound.remixes.count())
    if False:#sound.pack:
        document["pack"] = remove_control_chars(sound.pack.name)
        document["grouping_pack"] = str(sound.pack.id) + "_" + remove_control_chars(sound.pack.name)
    else:
        document["grouping_pack"] = str(sound.id)
    #document["is_geotagged"] = sound.geotag_id is not None
    # if sound.geotag_id is not None:
    #     if not math.isnan(sound.geotag.lon) and not math.isnan(sound.geotag.lat):
    #         document["geotag"] = str(sound.geotag.lon) + " " + str(sound.geotag.lat)
    document["geotag"] = sound.geotag
    document["type"] = sound.type
    document["duration"] = sound.duration
    document["bitdepth"] = sound.bitdepth if sound.bitdepth != None else 0
    document["bitrate"] = sound.bitrate if sound.bitrate != None else 0
    document["samplerate"] = int(sound.samplerate)
    document["filesize"] = sound.filesize
    #document["channels"] = sound.channels
    #document["md5"] = sound.md5
    document["num_downloads"] = sound.num_downloads
    document["avg_rating"] = sound.avg_rating
    document["num_ratings"] = sound.num_ratings
    #document["comment"] = sound.comments#[remove_control_chars(comment_text) for comment_text in
                           #sound.comments.values_list('comment', flat=True)]
    document["comments"] = sound.num_comments
    # document["waveform_path_m"] = sound.locations()["display"]["wave"]["M"]["path"]
    # document["waveform_path_l"] = sound.locations()["display"]["wave"]["L"]["path"]
    # document["spectral_path_m"] = sound.locations()["display"]["spectral"]["M"]["path"]
    # document["spectral_path_l"] = sound.locations()["display"]["spectral"]["L"]["path"]
    # document["preview_path"] = sound.locations()["preview"]["LQ"]["mp3"]["path"]
    return json.dumps([document])

SOLR_URL = "http://localhost:8080/"

def add_sounds_to_solr(sounds):
    #creating XML
    documents = map(convert_to_solr_document, sounds)
    #posting to Solr
    url = SOLR_URL + 'fs2/update'
    headers = {'Content-type': 'application/json'}
    params = {'commit': 'false'}
    Bar = ProgressBar(len(documents), 50, 'Indexing')
    Bar.update(0)
    for idx, sound in enumerate(documents):
        _request(url, sound, params, headers)
        Bar.update(idx+1)
        #print r
    params = {'commit': 'true'}
    r = requests.post(url, headers=headers, params=params)
    return r
#curl 'http://localhost:8983/solr/techproducts/update?commit=true' --data-binary @example/exampledocs/books.json -H 'Content-type:application/json'


def _request(url, data, params, headers):
    counter = 0
    while 1:  # Loop for trying 10 times the request with 0.5 sec delay
        counter += 1
        if counter > 10:
            r = None
            break
        try:
            r = requests.post(url, data=data, params=params, headers=headers)
            break
        except Exception as e:
            print e
            sleep(0.5)
    return r


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


# def add_all_sounds_to_solr(sound_queryset, slice_size=4000, mark_index_clean=False):
#     # Pass in a queryset to avoid needing a reference to
#     # the Sound class, it causes circular imports.
#     num_sounds = sound_queryset.count()
#     num_correctly_indexed_sounds = 0
#     for i in range(0, num_sounds, slice_size):
#         print "Adding %i sounds to solr, slice %i"%(slice_size,i)
#         try:
#             sounds_to_update = sound_queryset[i:i+slice_size]
#             add_sounds_to_solr(sounds_to_update)
#             if mark_index_clean:
#                 logger.info("Marking sounds as clean.")
#                 sounds.models.Sound.objects.filter(pk__in=[snd.id for snd in sounds_to_update])\
#                     .update(is_index_dirty=False)
#                 num_correctly_indexed_sounds += len(sounds_to_update)
#         except SolrException, e:
#             logger.error("failed to add sound batch to solr index, reason: %s" % str(e))
#     return num_correctly_indexed_sounds

