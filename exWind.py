# HMM with mfcc
# hmmlearn from scikit learn
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import scale


means = []
vars = []
hiddens = []
count = 0
nbAnalysis = len(b.ids)

for analysis in b.analysis.lowlevel.mfcc:
    if analysis is not None:
        try:
            obs = np.array(analysis)
            obs = obs.T
            obs = obs[1:]
            obs = obs.T
            obs = scale(obs)

            model = GaussianHMM(algorithm='map', covariance_type='diag', covars_prior=0.01,
                  covars_weight=1, init_params='mc', means_prior=0, means_weight=0,
                  min_covar=0.001, n_components=3, n_iter=1000, params='mc',
                  random_state=None, startprob_prior=1.0, tol=0.01, transmat_prior=1.0,
                  verbose=False)

            model.startprob_ = np.array([1., 0, 0])
            model.startprob_prior = model.startprob_
            model.transmat_ = np.array([[0.9, 0.1, 0], [0, 0.9, 0.1], [0, 0, 1]])
            model.transmat_prior = model.transmat_

            model.fit(obs)
            hidden_state = model.predict(obs)

            mean_sequence = obs
            var_sequence = obs
            for i in range(len(obs)):
                mean_sequence[i] = model.means_[hidden_state[i]]
                var_sequence[i] = np.diag(model.covars_[hidden_state[i]])

            means.append(mean_sequence)
            vars.append(var_sequence)
            hiddens.append(hidden_state)
        except:
            means.append(None)
            vars.append(None)
            hiddens.append(None)
    else:
        means.append(None)
        vars.append(None)
        hiddens.append(None)
    count += 1
    print str(count) + '/' + str(nbAnalysis)




################################################################################################
import copy
import essentia
import freesound
import numpy as np
import matplotlib.pyplot as plt
c = freesound.FreesoundClient()
c.set_token("","token") #put your id here...

# Needed to remove non asci caracter in names
def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)


 
    
##########################################################################################################################################################

# search for sounds with "wind" query and tag, duration 0 to 30sec
# ask for analysis_frames in order to be ablet to use get_analysis_frames method
results_pager = c.text_search(query="wind",filter="tag:wind duration:[0 TO 30.0]",sort="rating_desc",fields="id,name,previews,username,analysis_frames",page_size=150)
results_pager_last = copy.deepcopy(results_pager)

# recup all sounds in a list
nbSound = results_pager.count
numSound = 0
sounds = [None]*nbSound

# 1st iteration
for i in results_pager:
    i.name = strip_non_ascii(i.name)
    sounds[numSound] = copy.deepcopy(i)
    numSound = numSound+1
    print '\n' + str(numSound) + '/' + str(nbSound) + '\n' + str(i.name)
        
# next iteration
while (numSound<nbSound):
    results_pager = copy.deepcopy(results_pager_last.next_page())
    for i in results_pager:
        i.name = strip_non_ascii(i.name)
        sounds[numSound] = copy.deepcopy(i)
        numSound = numSound+1
        print '\n' + str(numSound) + '/' + str(nbSound) + '\n' + str(i.name)
    results_pager_last = copy.deepcopy(results_pager)
    print ' \n CHANGE PAGE \n '


# recup mfcc in a list of array
allMfcc = [None]*nbSound
numSound = 0

# again the limitation can stop the loop
while (numSound<nbSound):
    try:    
        allMfcc[numSound] = essentia.array(sounds[numSound].get_analysis_frames().lowlevel.mfcc)
    except ValueError:
        print "Oops! JSON files not found !"
    numSound = numSound+1
    print '\n' + str(numSound) + '/' + str(nbSound) + '\n'

    
    
# recup all analysis frames 
allAnalysisFrames = [None]*nbSound
numSound = 0
while (numSound<nbSound):
    try:    
        allAnalysisFrames[numSound] = sounds[numSound].get_analysis_frames()
    except ValueError:
        print "Oops! JSON files not found !"
    numSound = numSound+1
    print '\n' + str(numSound) + '/' + str(nbSound) + '\n'

    
    
# save all analysis frames in json files
import os
if not os.path.exists('analysis'):
    os.makedirs('analysis')
numSound = 0
while (numSound<nbSound):
    nameFile = 'analysis/' + str(sounds[numSound].id) + '.json'
    if allAnalysisFrames[numSound]:
        with open(nameFile, 'w') as outfile:
            json.dump(allAnalysisFrames[numSound].as_json(), outfile)
    numSound = numSound+1
    print '\n' + str(numSound) + '/' + str(nbSound) + '\n'
    

# load all analysis from json files
files = os.listdir('./analysis/')
nbSound = len(files)
allAnalysisFrames = [None]*nbSound
for numSound in range(nbSound):
    with open('analysis/'+files[numSound]) as infile:
        allAnalysisFrames[numSound] = json.load(infile)
    print '\n' + str(numSound) + '/' + str(nbSound)

    
# remove None items
allMfcc = [x for x in allMfcc if x is not None]
nbSound = len(allMfcc)
    
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

# compute mean
allMfccMean = [None]*nbSound
for i in range(nbSound):
    allMfccMean[i] = allMfcc[i].mean(axis=0)


# kmeans from : http://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_digits.html
from sklearn import metrics
from sklearn.cluster import KMeans
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA
from sklearn.preprocessing import scale
from time import time

data = scale(allMfccMean)
n_samples, n_features = data.shape
n_digits = 8
labels = [0]*nbSound
sample_size = 300


def bench_k_means(estimator, name, data):
    t0 = time()
    estimator.fit(data)
    print('% 9s   %.2fs    %i   %.3f   %.3f   %.3f   %.3f   %.3f    %.3f'
          % (name, (time() - t0), estimator.inertia_,
             metrics.homogeneity_score(labels, estimator.labels_),
             metrics.completeness_score(labels, estimator.labels_),
             metrics.v_measure_score(labels, estimator.labels_),
             metrics.adjusted_rand_score(labels, estimator.labels_),
             metrics.adjusted_mutual_info_score(labels,  estimator.labels_),
             metrics.silhouette_score(data, estimator.labels_,
                                      metric='euclidean',
                                      sample_size=sample_size)))

bench_k_means(KMeans(init='k-means++', n_clusters=n_digits, n_init=10),
              name="k-means++", data=data)

bench_k_means(KMeans(init='random', n_clusters=n_digits, n_init=10),
              name="random", data=data)

# in this case the seeding of the centers is deterministic, hence we run the
# kmeans algorithm only once with n_init=1
pca = PCA(n_components=n_digits).fit(data)
bench_k_means(KMeans(init=pca.components_, n_clusters=n_digits, n_init=1),
              name="PCA-based",
              data=data)
print(79 * '_')

###############################################################################
# Visualize the results on PCA-reduced data

reduced_data = PCA(n_components=2).fit_transform(data)
kmeans = KMeans(init='k-means++', n_clusters=n_digits, n_init=10)
kmeans.fit(reduced_data)

# Step size of the mesh. Decrease to increase the quality of the VQ.
h = .02     # point in the mesh [x_min, m_max]x[y_min, y_max].

# Plot the decision boundary. For that, we will assign a color to each
x_min, x_max = reduced_data[:, 0].min() - 1, reduced_data[:, 0].max() + 1
y_min, y_max = reduced_data[:, 1].min() - 1, reduced_data[:, 1].max() + 1
xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))

# Obtain labels for each point in mesh. Use last trained model.
Z = kmeans.predict(np.c_[xx.ravel(), yy.ravel()])

# Put the result into a color plot
Z = Z.reshape(xx.shape)
plt.figure(1)
plt.clf()
plt.imshow(Z, interpolation='nearest',
           extent=(xx.min(), xx.max(), yy.min(), yy.max()),
           cmap=plt.cm.Paired,
           aspect='auto', origin='lower')

plt.plot(reduced_data[:, 0], reduced_data[:, 1], 'k.', markersize=4)
# Plot the centroids as a white X
centroids = kmeans.cluster_centers_
plt.scatter(centroids[:, 0], centroids[:, 1],
            marker='x', s=169, linewidths=3,
            color='w', zorder=10)
plt.title('K-means clustering on the digits dataset (PCA-reduced data)\n'
          'Centroids are marked with white cross')
plt.xlim(x_min, x_max)
plt.ylim(y_min, y_max)
plt.xticks(())
plt.yticks(())
plt.show()













################### WORK IN PROGRESS
# JSON DUMP
def get_child_nodes(node_id):   
    request = urllib2.Request(ROOT_URL + node_id)
    response = json.loads(urllib2.urlopen(request).read())
    nodes = []
    for childnode in response['childNode']:
        temp_obj = {}
        temp_obj['id'] = childnode['id']
        temp_obj['name'] = childnode['name']
        temp_obj['children'] = get_child_nodes(temp_obj['id'])
        nodes.append(temp_obj)
    return nodes