#import built-in modules
import os 
import pickle
import gzip 
import subprocess 
from collections import defaultdict

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

class Wn_grid_parser(Synsets,
                     Les,
                     Stats,
                     Lemma,
                     Clean,
                     User,
                     Orbn):
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
        
    def export(self,output_path,format='lmf'):
        '''
        export resource to file.
        self.doc is first validated against dtd.
        if this fails, export will not be done
        
        @type  output_path: str
        @param output_path: output path
        
        @type  format: str
        @param format: default is 'lmf', 
        
        others include: 'omw', which is the Open Multilingual Wordnet format
        (http://compling.hss.ntu.edu.sg/omw/).
        'ili': mapping between pwn and odwn in rdf
        The output will be stored in the 'resources' folder
        '''
        self.clean()
        
        #validate it
        validation,message = self.validate(self.dtd)
        
        if validation:
            if format == 'lmf':
                with open(output_path,"wb") as outfile:
                    self.doc.write(outfile,
                                   pretty_print=True,
                                   xml_declaration=True,
                                   encoding='utf-8')
            elif format == 'omw':
                self.omw_export()
            
            elif format == 'ili':
                self.ili_map_export()
                    
        else:
            print("dtd validation was not succesful.")
            print(message)
    
    
    def ili_map_export(self):
        '''
        creates export file in resources/ili-map-odwnVERSION.ttl
        based on the original English one at:
        https://raw.githubusercontent.com/globalwordnet/ili/master/ili-map.ttl
        '''
        version = self.__version__.replace('.','')
        output_path = os.path.join(self.cwd,
                                   'resources',
                                   'ili-map-odwn%s.ttl' % version)
        
        synonyms_dict = defaultdict(set)
        for le_obj in self.les_get_generator():
            synset_id = le_obj.get_synset_id()
            lemma = le_obj.get_lemma()
            synonyms_dict[synset_id].add(lemma)
        
        with open(output_path,'w') as outfile:
            
            outfile.write('\n')
            outfile.write('@prefix\towl:\t<http://www.w3.org/2002/07/owl#> .\n')
            outfile.write('\n')
            outfile.write('### Wordnets\n')
            outfile.write('@prefix\todwn13:\t<http://odwn-rdf.vu.nl/odwn13/> .\n')
            outfile.write('\n')
            outfile.write('### this file\n')
            outfile.write('\n')
            outfile.write('@prefix ili: <http://globalwordnet.org/ili/> .\n')
            outfile.write('@base <http://globalwordnet.org/ili/ili-map.ttl>.\n')
            outfile.write('\n')
            for synset_obj in self.synsets_get_generator():
                ili = synset_obj.get_ili()
                synset_id = synset_obj.get_id()
                if synset_id.startswith('eng-30'):
                    offset_pos = synset_id.replace('eng-30-','')
                    if synonyms_dict[synset_id]:
                        synonyms = ', '.join(synonyms_dict[synset_id])
                        outline = 'ili:{ili}\towl:sameAs\todwn13:{offset_pos} . # {synonyms}\n'.format(**locals())
                        outfile.write(outline)
            
    def omw_export(self):
        '''
        this method performs the following steps:
        (1) creates new folder in resources: resources/nld
        (2) copies LICENSE in it
        (3) copies reference in it
        (4) creates wn-data-nld.tab
        '''
        cwd = self.cwd
        out = os.path.join(self.cwd,'resources','nld')
        
        #(1) creates new folder in resources: resources/nld
        command = 'rm -rf {out} && mkdir {out}'.format(**locals())
        subprocess.call(command,shell=True)
        
        #(2) copies LICENSE in it
        command = 'cp {cwd}/LICENSE.md {out}/LICENSE'.format(**locals())
        subprocess.call(command,shell=True)
        
        #(3) copies reference in it
        command = 'cp {cwd}/citation.bib {out}/'.format(**locals())
        subprocess.call(command,shell=True)
        
        #(4) creates wn-data-nld.tab
        output_path = os.path.join(out,'wn-data-nld.tab')
        with open(output_path,'w') as outfile:
            
            #write header
            header = '\t'.join([
                                '# Open Dutch WordNet',
                                'nld',
                                'http://wordpress.let.vupr.nl/odwn/',
                                'CC BY SA 4.0'])
            outfile.write(header+'\n')
            for le_obj in self.les_get_generator():
                
                synset_id = le_obj.get_synset_id()
                lemma = le_obj.get_lemma()
                if not synset_id:
                    continue
                prov,version,offset,pos = synset_id.split('-')
                
                if all([prov == 'eng',
                        lemma]):
                    output = '{offset}-{pos}\tnld:lemma\t{lemma}\n'.format(**locals())
                    outfile.write(output)
                    
                
            
            
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
            print('general stats for input file:')
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


    def load_synonyms_dicts(self):
        '''
        load dicts to obtain synonyms of lemma
    
        :rtype: dict
        :return: mapping from lemma to set of synonyms
        '''
        self.synset2lemmas = defaultdict(set)
        self.lemma2synsets = defaultdict(set)
    
        for le_obj in self.les_get_generator():
    
            lemma = le_obj.get_lemma()
            synset_id = le_obj.get_synset_id()
    
            if lemma is not None:
                self.synset2lemmas[synset_id].add(lemma)
                self.lemma2synsets[lemma].add(synset_id)
    
    def lemma_synonyms(self,lemma):
        '''
        return the synonyms of a lemma 
    
        :param str lemma: a lemma (for example 'paard')
    
        :rtype: set
        :return: set of synonyms of the lemma according to odwn
        '''
        if not all([hasattr(self,'synset2lemmas'),
                    hasattr(self,'lemma2synsets')]):
            self.load_synonyms_dicts()
                
            
        synonyms = set()
        for synset_id in self.lemma2synsets[lemma]:
            synonyms.update(self.synset2lemmas[synset_id])
    
        return synonyms
