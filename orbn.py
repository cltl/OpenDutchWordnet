from lxml import etree
import pickle
import os 

class Orbn():
    '''
    '''

    def __init__(self):
        pass


    def orbn_definition_dict(self,path_orbn,set_of_orbn_ids=[]):
        '''
        given a path to the orbn xml file
        this method will return a mapping from c_lu_id ->
            'definition' -> definition
            'examples'   -> list of examples
            
        @type  path: str
        @param path: path to orbn xml
        
        @type  set_of_orbn_ids: set
        @param set_of_orbn_ids: set of orbn ids
        
        @rtype: dict
        @return: c_lu_id ->
            'definition' -> definition
            'examples'   -> list of examples
            'lemma'      -> lemma
        '''
        data = {}
        doc = etree.parse(path_orbn)
        
        sem_resumes = ['semantics_verb/sem-resume',
                       'semantics_noun/sem-resume',
                       'semantics_adj/sem-resume']
        path_example = 'examples/example/form_example/canonicalform'
        
        for cdblu_el in doc.iterfind('cdb_lu'):
            lu_id = cdblu_el.get('c_lu_id')
            lu_id = lu_id.replace('d_','o_')
       
            if all([set_of_orbn_ids,
                    lu_id not in set_of_orbn_ids]):
                continue
                     
            definition = ''
            examples = [ex_el.text if ex_el.text else ''
                        for ex_el in cdblu_el.iterfind(path_example)]
            for sem_resume in sem_resumes:
                sem_resume_el = cdblu_el.find(sem_resume)
                if sem_resume_el is not None:
                    definition = sem_resume_el.text
            
            lemma = ''
            form_el = cdblu_el.find('form')
            if form_el is not None:
                lemma = form_el.get('form-spelling')
            
            data[lu_id] = {'examples' : examples,
                           'definition' : definition,
                           'lemma'      : lemma,
                           'c_seq_nr'   : cdblu_el.get('c_seq_nr')}
    
        return data

    def orbn_search(self,load=True):
        '''
        this is an interactive method 
        that allows to enter a lemma and return the orbn ids 
        that are not yet in open source dutch wordnet.
        '''
        path_rbn_bin = os.path.join(self.cwd,'resources','rbn.bin')
        if load:
            le_ids_in_odwn,rbn_data = pickle.load(open(path_rbn_bin,'rb'))
        else:
            le_ids_in_odwn = set(le_obj.get_sense_id().split('_sub_')[0]
                                 for le_obj in self.les_get_generator())
            rbn_data      = self.orbn_definition_dict(self.rbn)
            rbn_keys      = set(key for key in rbn_data.keys())
            for key in rbn_keys:
                if any([key.startswith('t_'),
                        #key in le_ids_in_odwn,
                        '_sub_' in key]):
                    del rbn_data[key]
            with open(path_rbn_bin,'wb') as outfile:
                pickle.dump((le_ids_in_odwn,rbn_data),outfile)
        
        while True:
            print()
            lemma = input('enter lemma: ')
            for key,value in rbn_data.items():
                if value['lemma'] == lemma:
                    print()
                    print('c_lu_id: '+key,str(key in le_ids_in_odwn))
                    print('definition: '+value['definition'])
                    for example in value['examples']:
                        print('example: '+example)
                
        
