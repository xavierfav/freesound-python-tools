import essentia
import freesound
c = freesound.FreesoundClient()
c.set_token("a226905c14719e5bbfaa258cbcf135423b98035c","token") #put your id here...

# search for sounds with "wind" query and tag, duration 0 to 30sec
# ask for analysis_frames in order to be ablet to use get_analysis_frames method
results_pager = c.text_search(query="wind",filter="tag:wind duration:[0 TO 30.0]",sort="rating_desc",fields="id,name,previews,username,analysis_frames")


# recup all sounds in a list
nbSound = results_pager.count
numSound = 0
sounds = [None]*nbSound

# need to repeat this because of the request limitation...
while (numSound<nbSound+1):
    for i in results_pager:
        sounds[numSound] = i
        numSound = numSound+1
        print str(numSound ) + str(i.name)
    if (numSound<nbSound):
        results_pager.next_page()
    print ' \n CHANGE PAGE \n '


# recup mfcc in a list of array
allMfcc = [None]*nbSound
numSound = 0

# again the limitation can stop the loop
while (numSound<nbSound):
    allMfcc[numSound] = essentia.array(sounds[numSound].get_analysis_frames().lowlevel.mfcc)
    numSound = numSound+1
    print '\n' + str(numSound) + '/' + str(nbSound) + '\n'
    
    
# save variables
import pickle
with open('windSounds.pickle', 'w') as f: 
    pickle.dump(sounds,f)
with open('windSoundsMfcc.pickle', 'w') as f: 
    pickle.dump(allMfcc,f)

# load
with open('windSounds.pickle') as f:
    sounds = pickle.load(f)  
with open('windSoundsMfcc.pickle') as f:
    allMfcc = pickle.load(f)    
    
# some plots...


# kmeans