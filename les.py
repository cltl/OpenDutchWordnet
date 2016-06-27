from collections import defaultdict
from le import Le
from random import randint
#import xml parser (lxml is preferred, else built-in module xml is used)
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree
    
class Les():
    '''
    '''
    def __init__(self):
        pass 
    
    def les_get_generator(self,mw=False):
        '''
        create generator of LexicalEntry elements
        (based on xml path in self.path_to_lus_els)
        
        @type  mw: bool
        @param mw: default is False, multi-words will be ignored.
        if set to True, multi-words will be returned. 

        @rtype: generator
        @return: generator of LexicalEntry XML elements
        '''
        for le_el in self.doc.iterfind(self.path_to_le_els):
            instance = Le(le_el,self.lexicon_el)
            le_id    = instance.get_id()
            if mw:
                yield instance
            elif "mwe" not in le_id:
                yield instance


    def les_find_le(self,le_identifier):
        '''
        find lexical entry based on identifier
        
        @type  le_identifier: str
        @param le_identifier: lexical entry identifier 
        (for example havermout-n-1)
        
        @rtype: instance
        @return: if found, instance of class Le, else None
        '''
        for le_el in self.les_get_generator():
            if le_el.get_id() == le_identifier:
                return le_el
        else:
            return None
        
    def les_all_les_of_one_synset(self,synset_identifier):
        '''
        given a synset identifier, return list of class instances
        of all les that belong to that synset (for example 'eng-30-00324560-v')
        
        @rtype: list
        @return: list of class instances of Class Le
        '''
        return [le_el for le_el in self.les_get_generator()
                if le_el.get_synset_id() == synset_identifier]
        
    def les_add_le(self,lemma,
                        long_pos,
                        short_pos,
                        synset_identifier,
                        provenances,
                        definition="",
                        sense_id=None,
                        sense_number=None,
                        annotator=None):
        '''
        add lexical entry
        
        WARNING: if lemma,pos already occurs in synset, le will not be added
        but the provenance will be changed
        
        WARNING: if sense_id already exists for this lemma, le will not be added
        
        if sense_id and le_sense_id are not provided, new ones will be created
        
        @type  lemma: str
        @param lemma: lemma to be added (for example "leuningstoel")
        
        @type  long_pos: str
        @param long_pos: noun | verb (perhaps "adjective" in the future")
        
        @type  short_pos: str
        @param short_pos: n | v (perhaps "a" in the future")
        
        @type  synset_identifier: str
        @param synset_identifier: (for example 'eng-30-00324560-v')
        
        @type  provenances: list
        @param provenances: list of resources that were used
        to add this synonym (for example ['wikipedia','wiktionary'])
        
        @type  definition: str
        @param definition: definition (default empty string)
        
        @type  sense_id: str
        @param sense_id: [optional]: sense_id of le. will be created if not
        given. for example "1"
        
        @type  le_sense_id: str
        @param le_sense_id: sense id of le. will be created if not provided
        
        @type  annotator: str
        @param annotation: if there was any: name of annotator.
        (will be added to attr 'annotator' in child element 'Sense')
        
        <LexicalEntry id="leuningstoel-n-1" partOfSpeech="noun">
          <Lemma writtenForm="leuningstoel"/>
          <WordForms>
            <WordForm writtenForm="leuningstoel" grammaticalNumber="singular" article=""/>
          </WordForms>
          <Morphology/>
          <MorphoSyntax/>
          <Sense id="o_n-104340805" senseId="1" definition="" synset="eng-30-02738535-n" provenance="cdb2.2_Auto">
          <SenseRelations/>
          <Semantics-noun/>
          <Pragmatics/>
          </Sense>
        </LexicalEntry>
    
        @rtype: tuple
        @return: (succes,message)
        '''
        all_les_of_one_synset = [le_obj
              for le_obj in self.les_all_les_of_one_synset(synset_identifier)]
        
        #WARNING: if lemma,pos already occurs in synset, le will not be added
        #but provenance will be changed
        for le_obj in all_les_of_one_synset:
                l,p = le_obj.get_lemma(),le_obj.get_pos() 
                
                #change provenance
                if (lemma,long_pos) == (l,p):
                    provenance_tag = le_obj.get_provenance()
                    for provance in provenances:
                        if provenance not in provenance_tag:
                            provenance_tag += "+"+provenance
                    le_obj.sense_el.attrib['provenance'] = provenance_tag
                
                #change annotator tag if needed
                if annotator is not None:
                    annotator_tag = le_obj.get_annotator()
                    if annotator not in annotator_tag:
                        annotator_tag += '+'+annotator
                    le_obj.sense_el.attrib['annotator'] = annotator_tag 
                    
                
        #WARNING:if sense_id already exists for this lemma,le will not be added
        sense_ids = [le_obj.get_sense_id()
            for le_obj in all_les_of_one_synset ]
        
        if all([sense_id is not None,
                sense_id in sense_ids]):
            return (False,
                    "sense_id %s already in sense ids of synset" % sense_id)
        
        #create orbn_id
        if sense_id is None:
            sense_id = self.les_new_le_sense_id(short_pos)

        #create lexical entry
        if sense_number is None:
            sense_number = self.lemma_highest_sense_number(lemma,pos=long_pos)+1
        
        #<LexicalEntry id="leuningstoel-n-1" partOfSpeech="noun">
        le_att={'id': "{lemma}-{short_pos}-{sense_number}".format(**locals()),
                'partOfSpeech': long_pos}
        
        #<Lemma writtenForm="leuningstoel"/>
        lemma_att = {'writtenForm': lemma}
        
        #<Sense id="o_n-104340805" senseId="1" definition="" 
        # synset="eng-30-02738535-n" provenance="cdb2.2_Auto">
        sense_att = {'id':         sense_id,
                     'senseId':    str(sense_number),
                     'definition': definition,
                     'synset':     synset_identifier,
                     'provenance': "+".join(provenances)}
        
        #add manual annotator info
        if annotator is not None:
            sense_att['annotator'] = annotator
            
        new_le_el = etree.Element("LexicalEntry",attrib=le_att)
        children = ['Lemma','WordForms','Morphology','MorphoSyntax','Sense']
        sense_children = ["SenseRelations","Semantics-%s" % long_pos,
                          "Pragmatics"]
        
        for element_name in children:
            attrib = {}
            
            if element_name == "Lemma":
                attrib = lemma_att
            elif element_name == "Sense":
                attrib = sense_att
                
            new_sub_el = etree.Element(element_name,attrib)
            if element_name == "Sense":
                for sense_child in sense_children:
                    new_sub_sub_el = etree.Element(sense_child)
                    new_sub_el.append(new_sub_sub_el)
                    
            
            new_le_el.append(new_sub_el)
            
        self.lexicon_el.insert(0,new_le_el)
        self.orbn_ids[sense_id] = ""
        return (True,"")
        
    def les_remove_le(self,le_identifier):
        '''
        method tries to remove a LexicalEntry. for example
        
        <LexicalEntry id="-baron-n-1">
            <Lemma partOfSpeech="noun" writtenForm="-baron"/>
            <Sense id="o_n-106739250" provenance="cdb2.2_Manual" synset="eng-30-09840217-n"/>
        </LexicalEntry>
          
        [questionable due to orbn]: renumber le's
        
        @type  le_identifier: str
        @param le_identifier: lexicalentry identifier, which is the value of 
        the 'id' attribute of the LexicalEntry element
        '''
        le_obj = self.les_find_le(le_identifier)
        
        if le_obj is not None:
            le_obj.remove_me()

            #sy_id            = le_obj.get_synset_id()
            #all_les_of_sy_id = self.les_all_les_of_one_synset(sy_id)
            
            #TODO: decide if you want to remove empty synset
            #if len(all_les_of_sy_id) == 1:
            #    self.synsets_remove_synset(sy_id,remove_les=False)
    
    def les_remove_a_resource(self,resource):
        '''
        this method loop sover all LexicalEntry elements and checks
        the provenance tag of each LexicalEntry and:
        (1) if the tag does not contain the resource -> nothing happens
        (2) if the tag is only the resource -> le is removed
        (3) if the resource is in the resource, but not the only
        resource -> resource is removed from tag
        '''
        for le_obj in self.les_get_generator():
            
            provenance_tag = le_obj.get_provenance()
            resources      = provenance_tag.split("+")
            
            if resource in resources:

                #(2) if the tag is only the resource -> le is removed
                if len(resources) == 1:
                    le_obj.remove_me()
                    
                #(3) if the resource is in the resource, but not the only
                else:
                    resources.remove(resource)
                    provenance_tag = "+".join(resources)
                    le_obj.sense_el.attrib['provenance'] = provenance_tag
        
    def les_new_le_sense_id(self,short_pos):
        '''
        new le sense id.
        
        @type  short_pos: str
        @param short_pos: n | v (perhaps "a" in the future")
        
        @rtype: str
        @return: new identifier (for example "o_n-106739250").
        '''
        while True:
            number    = "".join([str(randint(0,9)) for x in range(9)])
            candidate = "o_n-%s" % number
            
            if candidate not in self.orbn_ids:
                self.orbn_ids[candidate] = ""
                return candidate


    def les_load_synonyms_dicts(self):
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


    def les_lemma_synonyms(self, lemma):
        '''
        return the synonyms of a lemma

        :param str lemma: a lemma (for example 'paard')

        :rtype: set
        :return: set of synonyms of the lemma according to odwn
        '''
        if not all([hasattr(self, 'synset2lemmas'),
                    hasattr(self, 'lemma2synsets')]):
            self.les_load_synonyms_dicts()

        synonyms = set()
        for synset_id in self.lemma2synsets[lemma]:
            synonyms.update(self.synset2lemmas[synset_id])

        return synonyms