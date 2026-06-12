import os
from collections import defaultdict
import pickle
import random 
from lxml import etree

class User():
    '''


    '''
    def __init__(self):
        pass


    def annotate(self):
        
        self.user       = input("what is your name?:")
        
        self.cwd        = os.path.dirname(os.path.realpath(__file__))
        self.out_folder = os.path.join(self.cwd, 'user_input', self.user)
        
        if os.path.isdir(self.out_folder) == False:
            os.mkdir(self.out_folder)
        
        #user input to decide which task they are going to do
        #refer to methods
        self.task = input('which task would you like to do: evaluate_resource \
| resolve_sub_ | empty_base_synsets1 | empty_base_synsets2 | tops | large_synsets \
large_synsets1 | large_synsets2 | synsets_5_10 ?  ')

        if self.task == 'evaluate_resource':
            self.evaluate_resource()
    
        if self.task == 'resolve_sub_':
            self.resolve_sub_les()
        
        if self.task in ['empty_base_synsets1','empty_base_synsets2','tops','large_synsets',
                         'large_synsets1','large_synsets2','synsets_5_10']:
            self.stats_synset_inspection()

    def evaluate_resource(self):
        '''
        randomly pick x examples and use user input 
        to evaluate if they are correct
        '''
        resource      = input('which resource do you want to evaluate?: ')
        num_instances = input('how many instances do you want to evaluate?: ')
        answer        = input('monosemous (m) or polysemous (p)?: ')
        monosemous    = answer == "m"

        average_polysemy,polysemy_dict = self.polysemy_dict()
        monosemy_set = set(polysemy_dict[1])
        all_le_objs = defaultdict(dict)

        #get all le_obj -> synset_identifier
        for le_obj in self.les_get_generator():
            provenance_tag = le_obj.get_provenance()
            lemma          = le_obj.get_lemma()
                
            #filter on number of senses
            lemma_is_monosemous = lemma in monosemy_set

            if all([lemma_is_monosemous == monosemous,
                    resource in provenance_tag]):
                target = le_obj.get_synset_id()
                if target is not None:
                    all_le_objs[le_obj] = target
           
        #randomly pick x instances
        random_pick = random.sample( all_le_objs.items(), int(num_instances) )     
        synsets     = set([ sy_id for le_obj,sy_id in random_pick])

        #obtain synset info
        synset_info = self.synsets_get_definition_dict()

        #user evaluation
        annotation = {}
        for counter,(le_obj,sy_id) in enumerate(random_pick):
            print(' ')
            print('item %s, to go: %s' % (counter,int(num_instances)-counter))
            le_id = le_obj.get_id()
            print(le_id)
            print
            sy_info = {}
            if sy_id in synset_info:
                sy_info = synset_info[sy_id]
            print(sy_id)
            definition = []
            if 'definition' in sy_info:
                definition = sy_info['definition']
            print(definition)
            answer = input('correct? (y|n):')
            annotation[le_id] = {'sy_id'  : sy_id,
                                 'sy_def' : definition,
                                 'answer' : answer == 'y'}
        
        correct = [info['answer'] for info in annotation.values()].count(True)
        perc_correct = correct/int(num_instances)

        #save results
        basename = "{resource}_monosemous_{monosemous}_instances_{num_instances}".format(**locals())
        output_path = os.path.join(self.out_folder,basename+'.bin')
        with open(output_path,'wb') as outfile:
            pickle.dump((perc_correct,annotation),outfile)
         
        print('done')
        print(perc_correct)
        print('for resource: %s' % resource)
        print('saved at %s' % output_path)

    def resolve_sub_les(self):
        '''
        there are LexicalEntry elements in the resource with _sub_ in it.
        this method provides a way to choose which one is correct
        '''
        annotation = {}
        synsets    = set()
        set_of_orbn_ids = set()
        for le_obj in self.les_get_generator():
            le_id = le_obj.get_sense_id()
            lemma = le_obj.get_lemma()
            target = le_obj.get_synset_id()

            if '_sub_' in le_id:
                base,rest = le_id.split('_sub_')

                if base not in annotation:
                    annotation[base] = {'lemma': lemma,
                                        'odwn_definition' : le_obj.get_definition(),
                                        'checked'         : False,
                                        'synsets'         : []}
                
                synsets.update([target])
                set_of_orbn_ids.update([base])
                annotation[base]['synsets'].append(target)

        synset_info = self.synsets_get_definition_dict()
        orbn_data = self.orbn_definition_dict(self.orbn,set_of_orbn_ids=set_of_orbn_ids)

        total = [len(info['synsets']) >= 2 for info in annotation.values()].count(True)

        #load method
        output_path = os.path.join(self.out_folder,'_sub_.bin')
        if os.path.exists(output_path):
            annotation = pickle.load(open(output_path,'rb'))

        print()
        print(total) 
        print()
        for counter,(base,info) in enumerate(sorted(annotation.items())):
            if len(info['synsets']) == 1:
                continue
            if info['checked']:
                continue
            print()
            print('item: %s (of %s), to go: %s' % (counter,total,(total-counter)))
            print('le_id: '+base)
            print('lemma: '+info['lemma'])
            print('odwn definition: '+info['odwn_definition'])
            if base in orbn_data:
                print('orbn_definition: '+orbn_data[base]['definition'])
                for example in orbn_data[base]['examples']:
                    print('example: '+example)
            print()
            for counter,synset in enumerate(info['synsets']):
                print()
                print(counter)
                print(synset)
                print(synset_info[synset]['definition'])
            correct = input("which ones are correct (separated by spaces ?: ")
            try:
                answers = [int(answer) for answer in correct.split(' ')]
            except ValueError:
                answers = []
            annotation[base]['answers'] = answers
    
            annotation[base]['checked'] = True 

            #save it to file        
            output_path = os.path.join(self.out_folder,'_sub_.bin')
            with open(output_path,'wb') as outfile:
                pickle.dump(annotation,outfile)
            

    def lemma_inspection(self,min_polysemy=1):
        '''
        '''
        pass 

    def stats_synset_inspection(self):
        '''
        
        @type  task: str
        @ivar  task: empty_base_synsets | tops | large_synsets
        '''
        output_path = os.path.join(self.out_folder,self.task+'.bin')
        synsets = pickle.load( open( os.path.join(self.cwd,'resources',self.task+'.bin'),'rb') )
        if None in synsets:
            synsets.remove(None)
        synonym_dict = pickle.load( open ( os.path.join(self.cwd,'resources','synonym_dict.bin')    ,'rb') )
        
        #load annotation
        if os.path.exists(output_path):
            annotation = pickle.load( open(output_path,'rb'))
        else:
            annotation = { synset: {'done': False}
                          for synset in synsets}
        
        total = len(synsets)
        
        for counter,(sy_id,info) in enumerate(sorted(annotation.items())):
            
            if info['done']:
                continue
            
            sy_obj = self.synsets_find_synset(sy_id)
            if sy_obj is None:
                continue        
            
            
            print()
            print('item: %s (of %s), to go: %s' % (counter,total,(total-counter)))
            print('sy_id: '+sy_id)
            eng_lemmas = []
            if sy_id in synonym_dict:
                eng_lemmas = synonym_dict[sy_id]
            print('english lemmas: %s' % eng_lemmas)
            for gloss in sy_obj.get_glosses(languages=['en']):
                print('gloss: %s' % gloss)
            print()
            print('START OF PRINTING LE_IDS') 
            le_dict = {}
            for le_counter,le_obj in enumerate(self.les_all_les_of_one_synset(sy_id)):
                print()
                le_dict[str(le_counter)] = le_obj.get_id()
                print('le_id identifier: %s' % le_obj.get_id())
                print('le_id number: %s' % le_counter)
                print('le_id definition: %s' % le_obj.get_definition())
                print('le_id lemma: %s' % le_obj.get_lemma())
            print('END OF PRINTING LE_IDS')
            print()

            
            #user input
            le_ids_to_remove = input('le_ids to remove (numbers separated by spaces): ')
            c_lu_ids_to_add = input('c_lu_ids to add (separated by spaces): ')
            lemmas_to_add = input('lemmas to add (lemmas separated by spaces): ')
            for category,item in [('le_ids_to_remove',''),
                                  ('c_lu_ids_to_add',c_lu_ids_to_add),
                                  ('lemmas_to_add',lemmas_to_add)]:
                splitted = item.split()
                annotation[sy_id][category] = splitted
            for number in le_ids_to_remove.split():
                try:
                    annotation[sy_id]['le_ids_to_remove'].append(le_dict[number])
                except KeyError:
                    pass
            annotation[sy_id]['done'] = True       

            #save and load
            with open(output_path,'wb') as outfile:
                pickle.dump(annotation,outfile)
            annotation = pickle.load( open(output_path,'rb'))
            print(annotation[sy_id])
            input('continue?')

