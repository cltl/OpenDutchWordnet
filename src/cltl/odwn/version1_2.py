#import parser
import logging
from odwn import Wn_grid_parser
from collections import defaultdict 
import os 
import pickle

my_parser = Wn_grid_parser(Wn_grid_parser.odwn)
output_path = Wn_grid_parser.odwn.replace('1.1','1.2')

def start_logger():
    '''
    start logger
    '''
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

# create a file handler
    handler = logging.FileHandler(output_path+'.log',mode="w")
    handler.setLevel(logging.DEBUG)

# create a logging format
    formatter = logging.Formatter('%(filename)s - %(asctime)s - %(levelname)s - %(name)s  - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)
    
    logger.info('started creating version 1.2')
    return logger

def bin_generator(basename):
    '''
    given a particular basename, this method yields all .bin files
    that have been created by users
    
    @type  basename: str
    @param basename: _sub_.bin | tops.bin | empty_base_synsets1.bin | empty_base_synsets2 | large_synsets | resolve_sub_

    @type: generator
    @param: generator of full paths to .bin files
    '''
    rootDir = os.path.join(my_parser.cwd,'user_input')
    for dirName, subdirList, fileList in os.walk(rootDir):
        for fname in fileList:
            if fname == basename:
                user_bin = os.path.join(dirName,fname)
                yield os.path.join(dirName,fname)

def remove_sub_ids():
    '''
    this method remove le_objs from odwn as
    indicated by user input tasks:
    sub_
    '''
    le_ids_to_remove = set()
    
    user_bin_path = os.path.join(my_parser.cwd,
                                 'user_input',
                                 'anneleen',
                                 '_sub_.bin')
    user_info = pickle.load( open(user_bin_path,'rb'))

    correct_pairs = defaultdict(list)
    for key,value in user_info.items():
        for counter,sy_id in enumerate(value['synsets']):
            if value['checked']:
                if counter in value['answers']:
                    correct_pairs[key].append(sy_id)
            else:
                correct_pairs[key].append(sy_id)
            
    
    le_objs = { le_obj.get_sense_id(): le_obj
                for le_obj in my_parser.les_get_generator()
                if '_sub_' in le_obj.get_sense_id()}

    removed = 0 

    for sense_id,le_obj in le_objs.items():
        base = sense_id.split('_sub_')[0]
        target = le_obj.get_synset_id()

        remove = True
        if base in correct_pairs:
            if target in correct_pairs[base]:
                remove=False
                le_obj.sense_el.attrib['annotator'] = 'anneleen'
        
        if remove:
            removed +=1
            le_obj.remove_me()
 
    logger.info('removed %s _sub_ le_ids' % removed)

def remove_le_ids():
    '''
    this method remove le_objs from odwn as
    indicated by user input tasks:
    tops | empty_base_synsets1 | empty_base_synsets2 | large_synsets
    '''
    le_ids_to_remove = set()
    checked_synsets = {}

    for annotator,basename in [('marten','large_synsets1.bin'),
                               ('roxane','large_synsets2.bin')
                               ]:
        for user_bin_path in bin_generator(basename):
            user_info = pickle.load( open(user_bin_path,'rb'))
            for key,value in user_info.items():
                if value['done']:
                    le_ids_to_remove.update(value['le_ids_to_remove'])
                    checked_synsets[key] = annotator
    
    logger.info('found %s le_ids to remove' % len(le_ids_to_remove))
   
    for le_obj in my_parser.les_get_generator():
        target = le_obj.get_synset_id()
        if target in checked_synsets:
            le_obj.sense_el.attrib['annotator'] = checked_synsets[target]

        if le_obj.get_id() in le_ids_to_remove:
            le_obj.remove_me()

    logger.info('removed %s le_ids' % len(le_ids_to_remove))

def remove_empty_leave_odwn_synsets():
    '''
    remove empty leave odwn synsets from resource
    '''
    remove = True
    ronde  = 1
    logger.info('started removing empty leave odwn synsets')

    while remove:
        empty_synsets = my_parser.stats_empty_synsets()
        odwn_synsets_to_remove = empty_synsets['leave_empty_odwn_synsets']

        num_to_remove = len(odwn_synsets_to_remove)
        num_removed = 1

        if odwn_synsets_to_remove:
            for sy_obj in my_parser.synsets_get_generator():
                sy_identifier = sy_obj.get_id()
                if sy_identifier in odwn_synsets_to_remove:
                    my_parser.synsets_remove_synset(sy_identifier,
                                                    remove_les=False,
                                                    synset_el=sy_obj)
                    logger.debug('removed sy_id: %s round %s (%s of %s)' % (sy_identifier,
                                                                             ronde, 
                                                                             num_removed,
                                                                             num_to_remove))
                    num_removed +=1
            ronde+=1
    
        else:
            remove=False
            logger.info('finished removing empty leave odwn synsets')



 

def add_adjective_synsets():
    '''

    '''
    logger.info('started adding adjective synsets')
    paths = [os.path.join(my_parser.cwd,'resources','adjectives',basename)
             for basename in ['adjectives_monosemous_sp.csv',
                              'adjectives_monosemous.csv']]
    
    adj_sy_to_add = {}
    
    for path in paths:
        with open(path) as infile:
            for line in infile:
                if '\t' in line:
                    split = line.strip().split('\t')
                    sy_id = split[1]
                    definition = split[2]
                    adj_sy_to_add[sy_id] = definition
    
    num_added = 1
    num_to_add = len(adj_sy_to_add)
    
    #loop over them to add
    for sy_id,definition in adj_sy_to_add.items():
        succes,message = my_parser.synsets_add_synset(sy_id,
                                                      'pwn',
                                                      definition.replace('\"',''),
                                                      [])
        if succes:
            num_added+=1
        else:
            logger.debug('failed to add %s: %s' % (sy_id,message))
    
    
    logger.info('added %s (of %s) adjective synsets' % (num_added,
                                                       num_to_add))


def add_adjective_le_ids():
    '''
    '''
    logger.info('started adding adjective synonyms')
    paths = [os.path.join(my_parser.cwd,'resources','adjectives',basename)
             for basename in ['adjectives_monosemous_sp.csv',
                              'adjectives_monosemous.csv']]

    adj_syn_to_add = {}
    rbn_path = os.path.join(my_parser.cwd,'resources','odwn','cdb_lu.xml')
    rbn_dict = my_parser.orbn_definition_dict(rbn_path)

    for path in paths:
        with open(path) as infile:
            for line in infile:
                if '\t' in line:
                    split = line.strip().split('\t')
                    sense_id = split[3].replace('d_','o_')
                    if sense_id in rbn_dict:
                        
                        provenances = []
                        for source in ['google','bing','opus']:
                            if source in split[5]:
                                provenances.append(source)

                        info = {'lemma': split[4],
                                'sy_id': split[1],
                                'provenances': provenances,
                                'definition' : rbn_dict[sense_id]['definition'],
                                'sense_id'   : sense_id.replace('d_','o_'),
                                'sense_number' : rbn_dict[sense_id]['c_seq_nr']}
                        adj_syn_to_add[split[4]] = info
    
    num_added = 1
    num_to_add = len(adj_syn_to_add)
    
    #loop over them to add
    for le_id,info in adj_syn_to_add.items():

        my_parser.les_add_le(lemma=info['lemma'],
                             long_pos='adjective',
                             short_pos='a',
                             synset_identifier=info['sy_id'],
                             provenances=info['provenances'],
                             definition=info['definition'],
                             sense_id=info['sense_id'],
                             sense_number=info['sense_number'],
                             annotator=None)
    
        logger.debug('added adj le_id %s (%s of %s)' % (le_id,num_added,num_to_add))
        num_added += 1
    logger.info('added %s adj synonyms' % num_added)
    
def one_lemma_per_synset():
    '''
    try to have only one lemma per synset
    (1) if no definitions: remove all except lowest sense number
    (2) if one or more definitions: remove all but one
    
   sy_id,lemma-pos) ->  {'lowest_sense_number' -> lowest_sense_number,
                          'has_definition'      -> bool,
                          'le_objs'             -> [(le_obj,definition)]
    '''  
    sy_lemmas = defaultdict(dict)
    nones = 0
    
    for le_obj in my_parser.les_get_generator():
        le_id = le_obj.get_id()
        glosses = le_obj.get_definition()
        target = le_obj.get_synset_id()
        
        if target is None:
            continue
        
        lemma,pos,sense_number = le_id.rsplit('-',2)
        key = (target,lemma)
        has_def = False
        if glosses:
            has_def = True
        sense_number = int(sense_number)

        if key in sy_lemmas:
            if has_def:
                sy_lemmas[key]['has_definition'] = True
            if sense_number < sy_lemmas[key]['lowest_sense_number']:
                sy_lemmas[key]['lowest_sense_number'] = sense_number
            sy_lemmas[key]['le_objs'].append((le_obj,glosses,sense_number))
        
        else:
            sy_lemmas[key] = {'lowest_sense_number' : sense_number,
                              'has_definition'      : has_def,
                              'le_objs'             : [(le_obj,glosses,sense_number)]
                         }
    
    removed = 0

    for (target,lemma),value in sy_lemmas.items():
        
        if len(value['le_objs']) == 1:
            continue 
        
        if value['has_definition']:
            remove = True
            for le_obj,glosses,sense_number in value['le_objs']:
                if all([glosses,
                        remove]):
                    remove=False
                    continue
                succes,message = le_obj.remove_me()
                if not succes:
                    logger.debug(message)
                else:
                    removed +=1


        else:
            for le_obj,glosses,sense_number in value['le_objs']:
                if sense_number != value['lowest_sense_number']:
                    succes,message = le_obj.remove_me()
                    if not succes:
                        logger.debug(message)
                    else:
                        removed +=1
    logger.info('removed %s le_objs (same lemmas in synsets)' % removed)

        
            
    

    
    
        


#STEP X: LOGGER
logger = start_logger()

#STEP X: ADD ANNOTATOR ATTR TO ALL LE OBJS
for le_obj in my_parser.les_get_generator(mw=True):
    le_obj.sense_el.attrib['annotator'] = ''

#STEP X: CHANGE VERSION INFO
my_parser.lexicon_el.attrib['label'] = 'ODWN-ORBN-LMF-1.2'

#STEP X: REMOVE LE IDS
remove_le_ids()

#STEP X: REMOVE _SUB_
remove_sub_ids()

#STEP X:
one_lemma_per_synset()

#STEP X: REMOVE EMPTY LEAVE ODWN SYNSETS
remove_empty_leave_odwn_synsets()

#STEP X: ADD ADJECTIVE SYNSETS
add_adjective_synsets()

#STEP X: ADD LE_IDS IN ADJECTIVE SYNSETS
add_adjective_le_ids()

#STEP X: RUN STATS
#my_parser.get_stats(verbose=True)

#STEP X: export it to version 1.2
my_parser.export(output_path)

logger.info('finished conversion')
