#import built-in modules
import os 
import pickle
import gzip 

#import xml parser (lxml is preferred, else built-in module xml is used)
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

#import modules
from configuration import xml_paths
from synsets import Synsets
from les import Les
from stats import Stats
from lemma import Lemma
from clean import Clean
from orbn import Orbn
from user_input import User

class Wn_grid_parser(Synsets,Les,Stats,Lemma,Clean,User,Orbn):
    '''
    Parser for Global WordNet Grid LMF (inspection, stats, editing)
    
    @type  path_wn_grid_lmf: str
    @param path_wn_grid_lmf: path to wn grid lmf file

    @ivar  path_wn_grid_lmf: str
    @param path_wn_grid_lmf: path to wn grid lmf file
    
    @ivar  doc: lxml.etree._ElementTree
    @param doc: param path_wn_grid_lmf parsed with etree.parse
    
    >>> path="resources/odwn/odwn_orbn_gwg-LMF_1.2.xml.gz"
    >>> instance = Wn_grid_parser(path_wn_grid_lmf=path)
    
    >>> le_el = instance.les_find_le("havenplaats-n-1")
    >>> le_el.get_id()
    'havenplaats-n-1'
    >>> le_el.get_lemma()
    'havenplaats'
    >>> le_el.get_pos()
    'noun'
    >>> le_el.get_sense_id()
    'o_n-109910434'
    >>> le_el.get_provenance()
    'cdb2.2_Auto'
    >>> le_el.get_synset_id()
    'eng-30-08633957-n'
    
    >>> synset_el = instance.synsets_find_synset('eng-30-00324560-v')
    >>> synset_el.get_id()
    'eng-30-00324560-v'
    >>> synset_el.get_ili()
    'i23355'
    >>> relation_el = synset_el.get_relations("has_hyperonym")[0]
    >>> relation_el.get_provenance()
    'pwn'
    >>> relation_el.get_reltype()
    'has_hyperonym'
    >>> relation_el.get_target()
    'eng-30-00322847-v'
    
    >>> instance.lemma_num_senses("huis",pos="noun")
    6
    '''
    def __init__(self,path_wn_grid_lmf=None):
        self.path_wn_grid_lmf = path_wn_grid_lmf
        
        #read xml file and set general variables
        self.initialize()
        
    def initialize(self):
        '''
        (1) parse ivar path_wn_grid_lmf into ivar doc
        (2) set general class attributes
        '''
        infile        = gzip.GzipFile(self.path_wn_grid_lmf)
        self.doc      = etree.parse(infile,etree.XMLParser(remove_blank_text=True))
        self.lexicon_el = self.doc.find("Lexicon")
        self.reltypes = {}
        self.syn_ids  = {}
        self.cwd      = os.path.dirname(os.path.realpath(__file__))
             
        #make xml paths class attributes
        [setattr(self, key, value) for key,value in xml_paths.items()]
        
        #set of synset identifiers
        self.syn_ids = {sy_el.get_id():0
                        for sy_el in self.synsets_get_generator()}
        
        #relations
        self.reltypes = {rel_obj.get_reltype(): ""
                         for sy_obj in self.synsets_get_generator()
                         for rel_obj in sy_obj.get_all_relations()}
        
        self.orbn_ids = {le_obj.get_sense_id(): ""
                         for le_obj in self.les_get_generator()}
    
    def validate(self,dtd_path):
        '''
        validate against dtd
        
        @type  dtd_path: str
        @param dtd_path: full path to dtd
        
        @rtype: tuple
        @return: (succes,message)
        '''
        f       = open(dtd_path)
        dtd     = etree.DTD(f)
        message = ""
        
        succes = dtd.validate(self.doc)
        if not succes:
            message = dtd.error_log.filter_from_errors()[0]
        
        return (succes,message)
        
    def export(self,output_path):
        '''
        export resource to file.
        self.doc is first validated against dtd.
        if this fails, export will not be done
        
        @type  output_path: str
        @param output_path: output path
        '''
        self.clean()
        
        #validate it
        validation,message = self.validate(self.dtd)
        
        if validation:
            with open(output_path,"wb") as outfile:
                self.doc.write(outfile,
                               pretty_print=True,
                               xml_declaration=True,
                               encoding='utf-8')
        else:
            print("dtd validation was not succesful.")
            print(message)
        
    def get_stats(self,verbose=False):
        '''
        return most important stats into dict
        
        @type  verbose: bool
        @param verbose: [optional]. if set to True, general stats
        are send to stdout.
        '''
        Stats.__init__(self)
        
        num_rels,none_targets = self.stats_rels()
        tops                  = self.tops()
        with open( os.path.join(self.cwd,'resources','tops.bin'),'wb') as outfile:
            pickle.dump(tops,outfile)
        empty_synsets         = self.stats_empty_synsets() 
        average_polysemy, polysemy_dict = self.polysemy_dict()
        self.stats_large_synsets()

        self.stats = {'num_synsets'               : self.stats_num_synsets(),
                      'num_lexical_entries'       : self.stats_num_les(),
                      'num_empty_pwn_synsets'     : empty_synsets['num_empty_pwn_synsets'],
                      'num_empty_odwn_synsets'    : empty_synsets['num_empty_odwn_synsets'],
                      'empty_leave_odwn_synsets'  : empty_synsets['leave_empty_odwn_synsets'],
                      'num_relations'             : num_rels,
                      'impossible_rels'           : none_targets,
                      'empty_lemmas'              : self.empty_lemmas(),
                      'tops'                      : tops,
                      'sy_no_gloss,empty_glosses,one_word' : self.no_gloss(),
                      'pos_counts'                : self.count_pos(),
                      'provenance'                : self.resources_check(),
                      'polysemy_dict'             : polysemy_dict,
                      'average_polysemy'          : average_polysemy,
                      'bidirectional_relations'   : self.missing_bidirectional_relations("has_hyponym","has_hyperonym"),
                      'no_rels'                   : self.sy_no_rels(),
                      'contradicting'             : self.contradicting_rels()
                     }

        
        if verbose:
            print('general stats for:')
            print(os.path.basename(self.path_wn_grid_lmf))
            for key,value in sorted(self.stats.items()):

                if key in ["bidirectional_relations","polysemy_dict",'empty_leave_odwn_synsets',
                           "impossible_rels","tops","no_rels","contradicting"]:
                    print(key,len(value))     
                else:                
                    print(key,value)
    
    def set_ili_dict(self,file_object):
        '''
        given the path to mapping from ili to eng-30 synset identifiers
        this method returns the mapping itself
        
        <http://globalwordnet.org/ili/i117659> 
        <http://www.w3.org/2002/07/owl#sameAs> 
        <http://wordnet-rdf.princeton.edu/wn30/eng-15300051-n> 
        .
    
        @type  file_object: str
        @param file_object: file object or ili.nt.gz file containing mapping
        from ili to eng-30 synset identifiers
        
        @rtype: dict
        @return: mapping eng-30 synset identifier -> ili
        '''
        self.ili_dict = {}
        
        for line in file_object:
            if 'http://www.w3.org/2002/07/owl#sameAs>' in line:
                s,r,o,e = line.strip().split()
                ili = s.split('/ili/')[1][:-1]
                eng = o.split('/wn30/')[1][:-1]
                eng = eng.replace('eng-','eng-30-')
                self.ili_dict[eng] = ili

    def clean(self):
        '''
        clean resource
        '''
        self.clean_provenance_to_all_les()
        self.clean_impossible_relations()
        self.clean_bidirectional_relations()

    
