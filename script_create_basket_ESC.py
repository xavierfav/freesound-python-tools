d = c.load_pickle('pickles/datasets/freesound_ids_classes_ESC-50.pkl')

ids = []

for k in d.keys():
    ids = ids + d[k]
    
b.push_list_id(ids)

ids_remove = []
for idx in range(2000):
    if b.sounds[idx] is None:
        ids_remove.append(idx)
        
b.remove(ids_remove)
