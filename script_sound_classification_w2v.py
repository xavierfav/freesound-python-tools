from tabulate import tabulate
#import matplotlib.pyplot as plt
#import seaborn as sns
#import pandas as pd
import numpy as np
from gensim.models.word2vec import Word2Vec
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.cross_validation import cross_val_score
from sklearn.cross_validation import StratifiedShuffleSplit
from sklearn.utils import shuffle
import random


import manager
c = manager.Client(False)

# loading baskets
b_UrbanSound8K = c.load_basket_pickle('UrbanSound8K') # This basket has been actualize (cleaning + added clas)
b_FreesoundDb = c.load_basket_pickle('FreesoundDb') # FreesoundDb exist only on devaraya node. In local use freesoundDb (from april 2016)

# preprocess text data and getting class
X = np.array(b_UrbanSound8K.preprocessing_tag_description())
y = np.array(b_UrbanSound8K.clas)
X_FreesoundDb = np.array(b_FreesoundDb.preprocessing_tag_description())

# Creating array of w2v size to test
size_w2v_array = range(5,100,1)
#size_w2v = 20

for size_w2v in size_w2v_array:

    # Try different ordering of data
    for _ in range(5):
        # randomize order
        X, y = shuffle(X, y, random_state=0)
        X_FreesoundDb = shuffle(X_FreesoundDb, random_state=0)

        # training word2vec models
        model_UrbanSound8K = Word2Vec(X, size=size_w2v, window = 1000, min_count = 5, workers = 4)
        model_FreesoundDb = Word2Vec(X_FreesoundDb, size=size_w2v, window = 1000, min_count = 5, workers = 4)

        w2v_UrbanSound8K = {w: vec for w, vec in zip(model_UrbanSound8K.index2word, model_UrbanSound8K.syn0)}
        w2v_FreesoundDb = {w: vec for w, vec in zip(model_FreesoundDb.index2word, model_FreesoundDb.syn0)}


        # class and methods for embedding sounds with w2v (cf: https://github.com/nadbordrozd/blog_stuff/blob/master/classification_w2v/benchmarking.ipynb)
        class MeanEmbeddingVectorizer(object):
            def __init__(self, word2vec):
                self.word2vec = word2vec
                self.dim = len(word2vec.itervalues().next())

            def fit(self, X, y):
                return self 

            def transform(self, X):
                return np.array([
                    np.mean([self.word2vec[w] for w in words if w in self.word2vec] 
                            or [np.zeros(self.dim)], axis=0)
                    for words in X
                ])

        # and a tf-idf version of the same
        class TfidfEmbeddingVectorizer(object):
            def __init__(self, word2vec):
                self.word2vec = word2vec
                self.word2weight = None
                self.dim = len(word2vec.itervalues().next())

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


        # Model definition
        svc = Pipeline([("count_vectorizer", CountVectorizer(analyzer=lambda x: x)), ("linear svc", SVC(kernel="linear"))])
        svc_tfidf = Pipeline([("tfidf_vectorizer", TfidfVectorizer(analyzer=lambda x: x)), ("linear svc", SVC(kernel="linear"))])
        svc_w2v_UrbanSound8K = Pipeline([("word2vec vectorizer", MeanEmbeddingVectorizer(w2v_UrbanSound8K)), 
                                ("linear svc", SVC(kernel="linear"))])
        svc_w2v_tfidf_UrbanSound8K = Pipeline([("word2vec vectorizer", TfidfEmbeddingVectorizer(w2v_UrbanSound8K)), 
                                ("linear svc", SVC(kernel="linear"))])
        svc_w2v_FreesoundDb = Pipeline([("word2vec vectorizer", MeanEmbeddingVectorizer(w2v_FreesoundDb)), 
                                ("linear svc", SVC(kernel="linear"))])
        svc_w2v_tfidf_FreesoundDb = Pipeline([("word2vec vectorizer", TfidfEmbeddingVectorizer(w2v_FreesoundDb)), 
                                ("linear svc", SVC(kernel="linear"))])

        # benchmark all the things
        all_models = [
            ("svc", svc),
            ("svc_tdidf", svc),
            ("svc_w2v_UrbanSound8K", svc_w2v_UrbanSound8K),
            ("svc_w2v_tfidf_UrbanSound8K", svc_w2v_tfidf_UrbanSound8K),
            ("svc_w2v_FreesoundDb", svc_w2v_FreesoundDb),
            ("svc_w2v_tfidf_FreesoundDb", svc_w2v_tfidf_FreesoundDb),
        ]

        scores = sorted([(name, cross_val_score(model, X, y, cv=5).mean()) 
                         for name, model in all_models], 
                        key=lambda (_, x): -x)
	
        result = ''
        result += 'size_w2vec = ' + str(size_w2v)
        result += '\n'
        result += tabulate(scores, floatfmt=".4f", headers=("model", 'score'))
        result += '\n'
        result += '________________________________________________'
        result += '\n'
        with open('results_w2v', 'a') as f:
            f.write(result)

#plt.figure(figsize=(15, 6))
#sns.barplot(x=[name for name, _ in scores], y=[score for _, score in scores])
#
#def benchmark(model, X, y, n):
#    test_size = 1 - (n / float(len(y)))
#    scores = []
#    for train, test in StratifiedShuffleSplit(y, n_iter=5, test_size=test_size):
#        X_train, X_test = X[train], X[test]
#        y_train, y_test = y[train], y[test]
#        scores.append(accuracy_score(model.fit(X_train, y_train).predict(X_test), y_test))
#    return np.mean(scores)
#
#train_sizes = [10, 40, 160, 640]
#table = []
#for name, model in all_models:
#    for n in train_sizes:
#        table.append({'model': name, 
#                      'accuracy': benchmark(model, X, y, n), 
#                      'train_size': n})
#df = pd.DataFrame(table)
#
#plt.figure(figsize=(15, 6))
#fig = sns.pointplot(x='train_size', y='accuracy', hue='model', 
#                    data=df[df.model.map(lambda x: x in ["svc", "svc_tdidf", "svc_w2v_UrbanSound8K", 
#                                                         "svc_w2v_tfidf_UrbanSound8K", "svc_w2v_FreesoundDb", "svc_w2v_tfidf_FreesoundDb",
#                                                        ])])
##sns.set_context("notebook", font_scale=1.5)
#fig.set(ylabel="accuracy")
#fig.set(xlabel="labeled training examples")
#fig.set(title="R8 benchmark")
#fig.set(ylabel="accuracy")




"""
w2v size = 30
model                         score
--------------------------  -------
svc                          0.9791
svc_tdidf                    0.9791
svc_w2v_tfidf_FreesoundDb    0.8353
svc_w2v_tfidf_UrbanSound8K   0.8166
svc_w2v_FreesoundDb          0.6262
svc_w2v_UrbanSound8K         0.5439

w2v size = 100
model                         score
--------------------------  -------
svc                          0.9791
svc_tdidf                    0.9791
svc_w2v_tfidf_FreesoundDb    0.8298
svc_w2v_tfidf_UrbanSound8K   0.8251
svc_w2v_FreesoundDb          0.6231
svc_w2v_UrbanSound8K         0.5308

w2v size = 20
model                         score
--------------------------  -------
svc                          0.9791
svc_tdidf                    0.9791
svc_w2v_tfidf_UrbanSound8K   0.8436
svc_w2v_tfidf_FreesoundDb    0.8360
svc_w2v_FreesoundDb          0.6426
svc_w2v_UrbanSound8K         0.6364




"""
