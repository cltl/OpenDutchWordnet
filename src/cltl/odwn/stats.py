from collections import defaultdict 
from lxml import etree
import random   
import os
import pickle

class Stats():
    '''
    generate stats about resources
    '''
    def __init__(self):  
        pass 
    
    def stats_num_synsets(self):
        '''
        return number of synsets (length of self.syn_ids)
        
        @rtype: int
        @return: number of synsets
        '''
        return len(self.syn_ids)
    
    def stats_num_les(self):
        '''
        return number of lexical entries
        
        @rtype: int
        @return: number of lexical entries
        '''
        num_les = 0 
        for le_el in self.les_get_generator():
            num_les += 1
        
        return num_les
    
    def stats_rels(self):
        '''
        return number of synset relations
        
        @rtype: int
        @return: number of synset relations
        '''
        num_rels     = 0
        impossible   = []
        
        for sy_obj in self.synsets_get_generator():
            existing = []
            
            for rel_obj in sy_obj.get_all_relations():
                num_rels +=1 
                
                source   = sy_obj.get_id()
                reltype  = rel_obj.get_reltype() 
                target   = rel_obj.get_target()
                succes,message = self.validate_relation(source,reltype,target)
                if succes:
                    if (source,reltype,target) in existing:
                        impossible.append(rel_obj)
                    else:
                        existing.append((source,reltype,target))
                else:
                    impossible.append(rel_obj)
        
        return num_rels,impossible
    
    def empty_lemmas(self):
        '''
        return number of synoynyms that contain an empty lemma
        
        @rtype: int
        @return: number of synonym with an empty lemma
        '''
        empty_lemmas = 0
        
        for le_obj in self.les_get_generator():
            lemma = le_obj.get_lemma()
            if not lemma:
                empty_lemmas += 1
        
        return empty_lemmas
    
    def tops(self):
        '''
        return number of tops (synsets without hypernym relation)
        
        @rtype: int
        @return: number of synsets without hypernyms
        '''
        tops = []
        for sy_obj in self.synsets_get_generator():
            hyperonyms = sy_obj.get_relations('has_hyperonym')
            if not hyperonyms:
                tops.append(sy_obj.get_id())
        
        return tops

    def stats_empty_synsets(self):
        '''
        method to obtains the following stats:
        (1) number of empty synsets (no synonyms)
        (2) number of empty odwn synsets (+ of which leave nodes)
        (3) number of empty pwn  synsets (+ of which leave nodes)
        
        @rtype: tuple
        @return: (num_empty_synsets,
                  num_empty_odwn_synsets,
                  num_empty_pwn_synsets,
                  empty_odwn_leave_synsets)
        '''
        non_empty_synsets = set()

        for le_obj in self.les_get_generator():
            target = le_obj.get_synset_id()
            non_empty_synsets.update([target])
        
        empty_synsets = set(self.syn_ids.keys()) - non_empty_synsets
        
        empty_odwn_synsets = [sy_id for sy_id in empty_synsets if sy_id.startswith("odwn")]
        empty_pwn_synsets  = [sy_id for sy_id in empty_synsets if sy_id.startswith("eng")]
        
        leave_empty_odwn_synsets = set() 
        leave_pwn_synsets = set()

        for sy_obj in self.synsets_get_generator():
            sy_id    = sy_obj.get_id()
            hyponyms = sy_obj.get_relations('has_hyponym')
            if not hyponyms:
                if sy_id in empty_odwn_synsets:
                    leave_empty_odwn_synsets.add(sy_id)
                if sy_id.startswith('eng-30'):
                    leave_pwn_synsets.add(sy_id)


        with open( os.path.join(self.cwd,'resources','leave_pwn_synsets.bin'),'wb') as outfile:
            pickle.dump(leave_pwn_synsets,outfile)

        with open( os.path.join(self.cwd,'resources','empty_pwn_synsets.bin'),'wb') as outfile:
            pickle.dump(empty_pwn_synsets,outfile)

        return  { 'num_empty_synsets'       : len(empty_synsets),
                  'num_empty_odwn_synsets'  : len(empty_odwn_synsets),
                  'num_empty_pwn_synsets'   : len(empty_pwn_synsets),
                  'leave_empty_odwn_synsets' : leave_empty_odwn_synsets}

    def no_gloss(self):
        '''
        return number of 
        synsets without gloss + number of empty glosses + number of one word
        glosses
                
        @rtype: tuple
        @return: sy_no_gloss,empty_glosses,one_word
        '''
        sy_no_gloss   = 0
        empty_glosses = 0
        one_word      = 0
         
        for sy_obj in self.synsets_get_generator():
            
            glosses = sy_obj.get_glosses()
            
            if not glosses:
                sy_no_gloss += 1
            
            for gloss in glosses:
                if not gloss:
                    empty_glosses += 1
                
                split = gloss.split()
                if len(split) == 1:
                    one_word += 1
                    
        
        return sy_no_gloss,empty_glosses,one_word
        
        
    def count_pos(self):
        '''
        return number of nouns and verbs
        
        @rtype: tuple
        @return: list of tuples (pos,count)
        '''
        pos = defaultdict(int)
        
        for sy_obj in self.synsets_get_generator():
            
            part_of_speech = sy_obj.get_pos()
            pos[part_of_speech] += 1
        
        return [(key,value) for key,value in sorted(pos.items())]
    
    
    def resources_check(self):
        '''
        count provenances
        
        @rtype: dict
        @return: list of tuples (resource,count)
        '''
        resources_dict = defaultdict(int)
        
        for le_el in self.les_get_generator():
            
            resource_tag = le_el.get_provenance()
            
            if resource_tag is None:
                resources_dict['None'] += 1
            
            else:
                resources = resource_tag.split("+")
                for resource in resources:
                    resources_dict[resource] += 1
        
        return  [(key,value) for key,value in sorted(resources_dict.items())]
            

    def missing_bidirectional_relations(self,rel1,rel2):
        '''
        given two relations that imply each other,
        for example has_hyponym and has_hyperonym,
        this method returns the relations to add
        
        @type  rel1: str
        @param rel1: relation, for example 'has_hyponym'
        
        @type  rel2: str
        @param rel2: relation, for example 'has_hyperonym'
        
        @rtype: list
        @return: list of 3-tuples (source synset, target synset, relation)
        '''
        rels = {}
        
        for sy_obj in self.synsets_get_generator():
            source_synset = sy_obj.get_id()
            
            for rel_el in sy_obj.get_all_relations():
                reltype = rel_el.get_reltype()
                
                if reltype in [rel1,rel2]:
                    target_synset = rel_el.get_target()
                    rel  = (source_synset,target_synset,reltype)
                    key  = tuple(sorted([source_synset,target_synset]))
                    if key not in rels:
                        rels[key] = defaultdict(list)
                    rels[key]['reltypes'].append(reltype)
                    rels[key]['rels'].append(rel)
        
        rels_to_add = []
        goal        = set([rel1,rel2])
        for value in rels.values():
            if  set(value['reltypes']) != goal:
                
                source,target,reltype = value['rels'][0]
                miss_reltypes = goal.difference(set(value['reltypes']))
                for rel_to_add in miss_reltypes: 
                    rels_to_add.append((target,source,rel_to_add))
        
        
        return rels_to_add
        
    
    def polysemy_dict(self):
        '''
        return polysemy dict
        mapping polysemy to list of lemmas
        
        @rtype: dict
        @return: mapping polysemy to list of lemmas
        '''
        polysemy_dict = defaultdict(list)
        
        for lemma,polysemy in self.lemmas_generator().items():
            polysemy_dict[polysemy].append(lemma)
        
        total    = 0.0
        instance = 0.0
        for polysemy,list_lemmas in polysemy_dict.items():
            total    += (polysemy * len(list_lemmas))
            instance += len(list_lemmas)
        average_polysemy = round(total/instance,1)

        return average_polysemy,polysemy_dict
             
            
            
        
    def sy_no_rels(self):
        '''
        find synsets without relations
        
        @rtype: set
        @return: set of synset identifiers
        '''
        no_rels = set()
        
        for sy_obj in self.synsets_get_generator():
            
            if not any([sy_obj.get_relations("has_hyponym"),
                        sy_obj.get_relations("has_hyperonym")]):
                no_rels.update([sy_obj.get_id()])
        
        return no_rels
    
    def contradicting_rels(self):
        '''
        method to identify different reltypes linking the same source
        and target
        
        @rtype: dict
        @return: mapping (source,target) -> list of rel_obj
        '''
        contradicting = defaultdict(list)
        
        for sy_obj in self.synsets_get_generator():
            source = sy_obj.get_id()
            
            for rel_obj in sy_obj.get_all_relations():
                
                reltype = rel_obj.get_reltype()
                target  = rel_obj.get_target()
                contradicting[(source,target)].append(reltype)
                
        keys_to_remove = [key 
                          for key,value in contradicting.items()
                          if len(value) <= 1]
        
        for key in keys_to_remove:
            del contradicting[key]
        
        return contradicting
                
    def stats_large_synsets(self):
        '''
        creates a dict mapping synset identifier to
        find large synsets
        '''
        freq = {}

        for le_obj in self.les_get_generator():
            target = le_obj.get_synset_id()
            annotated = le_obj.get_annotator() != ''
            if target in freq:
                freq[target]['polysemy'] += 1
                if not annotated:
                    freq[target]['annotated'] = annotated
            else:
                freq[target] = {'polysemy' : 1,
                                'annotated': annotated}

        minimum = 5
        maximum = 10
        min_max = range(minimum,maximum)
        large_synsets = []
        for key,value in freq.items():
            if all([value['polysemy'] in min_max,
                    not value['annotated'],
                    key not in large_synsets]):
                large_synsets.append(key)
        
        #print(len(large_synsets))
        
        with open( os.path.join(self.cwd,'resources','synsets_%s_%s.bin' % (minimum,maximum)),'wb') as outfile:
            pickle.dump(large_synsets,outfile)


    def stats_evaluate_resources(self):
        '''

        '''
        rootDir = os.path.join(self.cwd,'user_input')
        for dirName, subdirList, fileList in os.walk(rootDir):
            for fname in fileList:
                if fname.endswith('50.bin'):
                    user_bin = os.path.join(dirName,fname)
                    evaluation,d = pickle.load(open(user_bin,'rb'))
                    print(fname,evaluation)
                    
    
    def random_le_and_sy(self):
        '''
        '''
        from nltk.corpus import wordnet as wn
        
        start_at = random.choice( range( len(self.orbn_ids)))
        
        for counter,le_obj in enumerate(self.les_get_generator()):
            
            if counter >= start_at:
                print()
                print(etree.tostring(le_obj.le_el,
                                     pretty_print=True))
                answer = input('interesting? ')
                if answer == 'y':
                    target = le_obj.get_synset_id()
                    eng,version,offset,pos = target.split('-')
                    sy_obj = self.synsets_find_synset(target)
                    print()
                    print(etree.tostring(sy_obj.synset_el,
                                         pretty_print=True))
                    synset = wn._synset_from_pos_and_offset(pos,int(offset))
                    print(synset.lemmas())
                    print(synset.definition())
                    input('continue?')

    def stats_plot_depth(self,output_path):
        '''
        '''
        import matplotlib.pyplot as plt
        
        depth = {}
        keep_going = True
        cur_depth = 1
        total = 0
        tops = {top for top in self.tops()
                if not top.endswith('-a')}
        non_empty_synsets = {le_obj.get_synset_id()
                             for le_obj in self.les_get_generator()}
        
        current_layer = {sy_obj
                         for sy_obj in self.synsets_get_generator()
                         if sy_obj.get_id() in tops}
        
        while keep_going:
        
            next_layer_ids = set()
            total += len(current_layer)
            print(cur_depth,len(current_layer),total)
            for sy_obj in current_layer:
                sy_id = sy_obj.get_id()
                
                depth[sy_id] = cur_depth
        
                for relation_el in sy_obj.get_relations('has_hyponym'):
                    rel_target = relation_el.get_target()
                    if rel_target not in depth:
                        next_layer_ids.add(rel_target)
        
            current_layer = {sy_obj
                             for sy_obj in self.synsets_get_generator()
                             if sy_obj.get_id() in next_layer_ids}
        
            cur_depth +=1
        
            if not current_layer:
                keep_going = False
        
        y = range(1,cur_depth)
        x1 = []
        x2 = []
        depths = [depth_value for depth_value in set(depth.values())]
        
        for depth_value in sorted(depths):
            
            empty = []
            full = []
            for key,value in depth.items():
                if value == depth_value:
                    if key in non_empty_synsets:
                        full.append(key)
                    else:
                        empty.append(key)
            total = len(empty) + len(full)
        
            perc_empty = 0.0
            if empty:
                perc_empty = 100 * (len(empty)/total)
            perc_full = 0.0
            if full:
                perc_full = 100 * (len(full)/total)
        
            x1.append(perc_empty)
            x2.append(perc_full)
        
        states = [str(depth_value) for depth_value in depths]
        
        fig, axes = plt.subplots(ncols=2, sharey=True)
        axes[0].barh(y, x1, align='center', color='red')
        axes[0].set(title='% of synsets without synonyms')
        axes[1].barh(y, x2, align='center', color='green')
        axes[1].set(title='% of synsets with synonyms')
        axes[0].invert_xaxis()
        axes[0].set(yticks=y, yticklabels=states)

        axes[0].yaxis.tick_right()
        
        plt.xlim(0,100)
        
        fig.tight_layout()
        fig.subplots_adjust(wspace=0.09)
        plt.savefig(output_path)
                        
