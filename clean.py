


class Clean():
    '''
    method to clean resource
    '''
    def __init__(self):
        pass
    
    def clean_impossible_relations(self):
        '''
        all relations in 
        self.stats['impossible_rels'] are removed
        '''
        self.get_stats()
        for rel_el in self.stats['impossible_rels']:
            rel_el.remove_me()
        print
        print("number of impossible relations removed:")
        print(len(self.stats['impossible_rels']))
    
    def clean_bidirectional_relations(self):
        '''
        all proposed relations in self.stats['bidirectional_relations']
        are added
        '''
        self.get_stats()
        for source,target,reltype in self.stats['bidirectional_relations']:
            sy_obj = self.synsets_find_synset(source)
            if sy_obj is not None:
                print('adding %s %s %s' % (source,reltype,target))
                sy_obj.add_relation(reltype,target)
            
        print
        print("number of bidirectional links fixed")
        print(len(self.stats['bidirectional_relations']))
        
    
    def clean_provenance_to_all_les(self):
        '''
        some LexicalEntry elements do not have a provenance tag.
        this method adds the "cdb2.2_Auto" tag as provenance
        '''
        default = "cdb2.2_Auto"
        added   = 0 
        for le_obj in self.les_get_generator():
            
            provenance_tag = le_obj.get_provenance()
            
            if provenance_tag is None:
                added += 1
                le_obj.sense_el.attrib["provenance"] = default
        
        print("number of Lexical Entries that receiced a default tag:")
        print(added)
                
    def clean_remove_synsets_without_relations(self,list_of_synsets):
        '''
        '''
        pass 
    
    def clean_synsets_without_synonyms(self):
        '''
        '''
        pass
    