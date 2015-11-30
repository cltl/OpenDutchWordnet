#import parser
import logging
from __init__ import Wn_grid_parser
import os 
import pickle

path_v_12 = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'resources',
                         'odwn',
                         'odwn_orbn_gwg-LMF_1.2.xml.gz')
my_parser = Wn_grid_parser(path_v_12)
output_path = path_v_12.replace('1.2','1.3')
output_path = output_path.strip('.gz')

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

#STEP X: LOGGER
logger = start_logger()

#STEP X: load annotations anneleen
cwd = os.path.dirname(os.path.realpath(__file__))
annotation_path = os.path.join(cwd,
                               'user_input',
                               'Anneleen',
                               'synsets_5_10.bin')

with open(annotation_path,'rb') as infile:
    annotation = pickle.load(infile)


#STEP X: remove le_objs
to_remove = set()
[to_remove.update(value['le_ids_to_remove']) 
 for value in annotation.values()
 if 'le_ids_to_remove' in value]

num_to_remove = len(to_remove)
logger.info('%s le ids found to remove' % num_to_remove)

for le_obj in my_parser.les_get_generator():
    le_id = le_obj.get_id()
    if le_id in to_remove:
        le_obj.remove_me()
    

#STEP X: RUN STATS
my_parser.get_stats(verbose=True)

#STEP X: export it to version 1.2
my_parser.export(output_path)

logger.info('finished conversion')
