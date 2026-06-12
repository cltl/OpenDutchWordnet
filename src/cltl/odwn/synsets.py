from synset import Synset
from collections import defaultdict
import os 
from lxml import etree 
import gzip

class Synsets():
    '''
    class to inspect and modify synsets objects
    '''
    def __init__(self):
        pass
        
    def synsets_get_generator(self):
        '''
        create generator of Synset elements
        (based on xml path in self.path_to_synset_els)
        
        @rtype: generator
        @return: generator of Synset XML elements
        '''
        for synset_el in self.doc.iterfind(self.path_to_synset_els):
            yield Synset(synset_el,
                         self.reltypes,
                         self.syn_ids) 
    
    
    def synsets_find_synset(self,synset_identifier):
        '''
        find synset based on identifier
        
        @type  synset_identifier: str
        @param synset_identifier: synset identifier 
        (for example eng-30-00325085-v)
        
        @rtype: instance
        @return: if found, instance of class Synset, else None
        '''
        for synset_el in self.synsets_get_generator():
            if synset_el.get_id() == synset_identifier:
                return synset_el
        else:
            return None
    
    def synsets_get_definition_dict(self):
        '''
        this method loops over all Synset elements and creates a dict
        mapping from sy_id ->
            'definition' -> definition

        @rtype: dict
        @return: mapping from sy_id ->
            'definition' -> definition
        '''
        synset_info = defaultdict(dict)
        for sy_obj in self.synsets_get_generator():
            sy_id = sy_obj.get_id()
            synset_info[sy_id]['definition'] = sy_obj.get_glosses()
        return synset_info



    
    def synsets_add_synset(self,
                           sy_id,
                           synset_provenance,
                           definition,
                           rels):
        '''
        synset is added if it has a hypernym relation to an existing 
        synset.
        
        WARNING not added if:
        (1) sy_id already exists
        (2) no succesful hypernym relation added (except for adjectives)
        
        @type  sy_id: str
        @param sy_id: synset identifier
        
        @type  synset_provenance: str
        @param synset_provenance: origin english synset: 'pwn', else 'odwn'
        
        @type  definition: str
        @param definition: definition
        
        @type  rels: list
        @param rels: list of tuples (reltype,target)
        
        @return: tuple
        @returun: (succes,message)
        '''    
        if not hasattr(self, 'ili_dict'):
            ili_nt_path = os.path.join(self.cwd,'resources','ili.nt.gz')  
            infile = gzip.GzipFile(ili_nt_path)
            self.set_ili_dict(infile)
        
        #get ili
        if sy_id not in self.ili_dict:
            return (False,'no ili identifier found for %s' % sy_id)
        
        ili = self.ili_dict[sy_id] 
        
        #check if sy_id already exists
        if sy_id in self.syn_ids:
            return (False,'synset exists already: %s' % sy_id)
        
        added_hypernym_rel = False
        
        base = '''<Synset id="{sy_id}" ili="{ili}">
<Definitions>
    <Definition gloss="{definition}" language="en" provenance="{synset_provenance}"/>
</Definitions>
<SynsetRelations/>
<MonolingualExternalRefs/>
</Synset>'''.format(**locals())
        synset_el = etree.fromstring(base)
        
        sy_obj = Synset(synset_el,self.reltypes,self.syn_ids)
        
        for reltype,target in rels:
            succes,message = sy_obj.add_relation(reltype,target)
            if all([reltype == 'has_hyperonym',
                    succes]):
                added_hypernym_rel = True
                
        if any([added_hypernym_rel,
                sy_id.endswith('a')]):
            self.lexicon_el.append(sy_obj.synset_el)
            return (True,'succes')
        else:
            return (False,'no hypernym rel added')
                
        
    def synsets_remove_synset(self,sy_identifier,remove_les=True,synset_el=None):
        '''
        (1) if removes_les: all lexical entries are removed from this synset
        (2) if no hyponyms: remove synset
        (3) if no hyponyms: remove all relations pointing to this synset
        
        @type  sy_identifier: str
        @param sy_identifier: synset identifier (i.e. eng-30-89405202-n)
        
        @type  remove_les: bool
        @param remove_les: remove les in synset (default is True)

        @type  synset_el: None | etree.Element
        @param synset_el: default is None, odwn will be searched for element.
        else, an Synset instance has to be provided
        '''
        #find synset
        if synset_el is None:
            synset_el = self.synsets_find_synset(sy_identifier)
        
        if synset_el is not None:
        
            #if wanted, remove les
            if remove_les:
                [le_obj.remove_me() 
                 for le_obj in self.les_all_les_of_one_synset(sy_identifier)]
            
            #remove synset if a leaf node
            hyponyms = synset_el.get_relations("has_hyponym")
            if not hyponyms:
                synset_el.remove_me()
                del self.syn_ids[sy_identifier]
                
                #remove all relations to this synset
                for sy_obj in self.synsets_get_generator():
                    for rel_obj in sy_obj.get_all_relations():
                        target = rel_obj.get_target()
                    
                        if target == sy_identifier:
                            rel_obj.remove_me()
            

    def validate_relation(self,source,reltype,target):
        '''
        this method check if a relation is valid or not. invalid if:
        (1) target does not exist
        (2) source does not exist
        (3) cross pos for has_hyponym has_hyperonym 
        (4) source == target
        (5) reltype not in existing list of reltypes
        (6) relation exists already
        
        @type  source: str
        @param source: source synset identifier
        
        @type  reltype: str
        @param reltype: relation type
        
        @type  target: str
        @param target: target synset identifier
        
        @rtype: tuple
        @return: (succes,message)
        '''
        #(1) target does not exist
        if target not in self.syn_ids:
            return (False,"target: %s not in existing synsets" % target)

        #(2) source does not exist
        elif source not in self.syn_ids:
            return (False,"source: %s not in existing synsets" % source)

        #(3) cross pos for has_hyponym has_hyperonym 
        elif all([source[-1] != target[-1],
                reltype in ['has_hyperonym','has_hyponym']
                ]):
            return (False,
                    "reltype: %s can not have cross pos relations" % reltype)
            
        #(4) source == target
        elif source == target:
            return (False,"source is same as target")
        
        #(5) reltype not in existing list of reltypes
        elif reltype not in self.reltypes:
            return (False,
                    'reltype: %s not in list of reltypes' % reltype)
        
        else:
            return (True,"")
            
    
        
