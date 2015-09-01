import os
import subprocess
import pickle
from nltk.corpus import wordnet as wn 

here=os.path.dirname(os.path.realpath(__file__))
resources=os.path.join(here,'resources')

#downloaded from: http://globalwordnet.org/wp-content/uploads/2013/07/5000_bc.zip
path_base_concepts=os.path.join(resources,'5000_bc.xml')

#clone repo if needed
wordnet_mapper_git='https://github.com/MartenPostma/WordNetMapper.git'
path_wordnet_mapper=os.path.join('WordNetMapper')

if not os.path.isdir(path_wordnet_mapper):
    clone='git clone '+wordnet_mapper_git
    print(subprocess.check_output(clone,shell=True))

from WordNetMapper import WordNetMapper
my_mapper = WordNetMapper()

#obtain base in wordnet 3.0
base=False
if base:
    base_concepts_30 = set()
    with open(path_base_concepts) as infile:
        for line in infile:
            offset_20 = line[18:26]
            try:
                offset_30,pos = my_mapper.map_offset_to_offset(offset_20, "20", "30")
                ili_30 = 'eng-30-{offset_30}-{pos}'.format(**locals())
                base_concepts_30.add(ili_30)
            except ValueError:
                pass

    with open(os.path.join(resources,'base_concepts_30.bin'),'wb') as outfile:
        pickle.dump(base_concepts_30,outfile)



#wordnet synonym dict
synonyms=False
if synonyms:
    synonym_dict = {}
    for synset in wn.all_synsets():
        offset = str(synset.offset())
        zeros  = (8-len(offset))* '0'

        pos = synset.pos()
        if pos in ['n','v']:
            ili = 'eng-30-{zeros}{offset}-{pos}'.format(**locals())
            lemmas = synset.lemma_names()
            synonym_dict[ili] = lemmas

    with open( os.path.join(resources,'synonym_dict.bin'),'wb') as outfile:
        pickle.dump(synonym_dict,outfile)

#create empty base level concepts dict
empty_synsets = set( pickle.load( open( os.path.join(resources,'empty_pwn_synsets.bin'),'rb')) )
base_concepts_30 = pickle.load( open( os.path.join(resources,'base_concepts_30.bin'),'rb'))
leave_pwn_synsets = pickle.load( open( os.path.join(resources,'leave_pwn_synsets.bin'),'rb'))

overlap = list ( base_concepts_30 & set(empty_synsets)  )
for sy_id in leave_pwn_synsets:
    if sy_id in overlap:
        overlap.remove(sy_id)

half    = int( len(overlap) / 2)
part1 = overlap[:half]
part2 = overlap[half:]

for basename,item in [('empty_base_synsets1.bin',part1),
                      ('empty_base_synsets2.bin',part2)]:
    with open( os.path.join(resources,basename),'wb') as outfile:
        pickle.dump(set(item),outfile)

