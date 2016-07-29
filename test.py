import wikipedia


# set_of_tags : set of tags to be used to compute the sparse vector of tags occurences in wiki page content
# set_of_tags = c.load_pickle('set_of_tags')

# set_of_terms : a set of terms to compare (queries, tags, ...)
# set_of_queries = c.load_pickle('set_of_queries')

def extract_wiki(term):
    result = wikipedia.page(term)
    return result.content

def createVector(wiki_content, set_of_tags):
    u = [0]*len(set_of_tags)
    for idx, term in enumerate(set_of_tags):
        u[idx] = wiki_content.count(term)
    return u
    
def run(set_of_terms, set_of_tags):
    bar = ProgressBar(len(set_of_terms), 50, '...')
    L = [] # list of all sparse vector
    for idx, term in enumerate(set_of_terms):
        bar.update(idx)
        try:
            wiki_content = extract_wiki(term)
            u = createVector(wiki_content, set_of_tags)
            L.append(u)
        except:
            L.append(None)
    return L

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


    
    
