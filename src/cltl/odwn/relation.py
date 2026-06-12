

class Relation():
    '''
    class for XML element Synset

    <SynsetRelation provenance="pwn" relType="has_hyperonym" target="eng-30-00322847-v"/>
    '''
    def __init__(self,relation_el): 
        self.relation_el = relation_el
    
    def get_provenance(self):
        '''
        return value provenance attribute
        
        @rtype: str
        @return: provenance tag
        '''
        return self.relation_el.get("provenance")
    
    def get_reltype(self):
        '''
        return value relType attribute
        
        @rtype: str
        @return: relType tag
        '''
        return self.relation_el.get("relType")
    
    def get_target(self):
        '''
        return value target attribute
        
        @rtype: str
        @return: synset target of relation
        '''
        return self.relation_el.get("target")
    
    def remove_me(self):
        '''
        remove relation element
        '''
        self.relation_el.getparent().remove(self.relation_el)
