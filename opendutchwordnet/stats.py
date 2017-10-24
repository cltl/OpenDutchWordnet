
def stats(self, verbose=False):
    """
    Populate dict with most important stats.

    @type  verbose: bool
    @param verbose: [optional]. if set to True, general stats
    are send to stdout.
    """
    num_rels, none_targets = self.stats_rels()
    tops = self.tops()
    with open(os.path.join(self.cwd, 'resources', 'tops.bin'), 'wb') as outfile:
        pickle.dump(tops, outfile)
    empty_synsets = self.stats_empty_synsets()
    average_polysemy, polysemy_dict = self.polysemy_dict()
    self.stats_large_synsets()

    self.stats = {'num_synsets': self.stats_num_synsets(),
                  'num_lexical_entries': self.stats_num_les(),
                  'num_empty_pwn_synsets': empty_synsets['num_empty_pwn_synsets'],
                  'num_empty_odwn_synsets': empty_synsets['num_empty_odwn_synsets'],
                  'empty_leave_odwn_synsets': empty_synsets['leave_empty_odwn_synsets'],
                  'num_relations': num_rels,
                  'impossible_rels': none_targets,
                  'empty_lemmas': self.empty_lemmas(),
                  'tops': tops,
                  'sy_no_gloss,empty_glosses,one_word': self.no_gloss(),
                  'pos_counts': self.count_pos(),
                  'provenance': self.resources_check(),
                  'polysemy_dict': polysemy_dict,
                  'average_polysemy': average_polysemy,
                  'bidirectional_relations': self.missing_bidirectional_relations("has_hyponym","has_hyperonym"),
                  'no_rels': self.sy_no_rels(),
                  'contradicting': self.contradicting_rels()}

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
    """
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
    """
    self.ili_dict = {}

    for line in file_object:
        if 'http://www.w3.org/2002/07/owl#sameAs>' in line:
            s, r, o, e = line.strip().split()
            ili = s.split('/ili/')[1][:-1]
            eng = o.split('/wn30/')[1][:-1]
            eng = eng.replace('eng-','eng-30-')
            self.ili_dict[eng] = ili

def clean(self):
    """
    clean resource
    """
    self.clean_provenance_to_all_lexical_items()
    self.clean_impossible_relations()
    self.clean_bidirectional_relations()

def clean_impossible_relations(self):
    """
    all relations in
    self.stats['impossible_rels'] are removed
    """
    self.stats()
    for rel_el in self.stats['impossible_rels']:
        rel_el.remove_me()

def clean_bidirectional_relations(self):
    """
    all proposed relations in self.stats['bidirectional_relations']
    are added
    """
    self.stats()
    for source, target, relationtype in self.stats['bidirectional_relations']:
        sy_obj = self.synsets_find_synset(source)
        if sy_obj is not None:
            sy_obj.add_relation(relationtype, target)

def clean_provenance_to_all_lexical_items(self):
    """
    some LexicalEntry elements do not have a provenance tag.
    this method adds the "cdb2.2_Auto" tag as provenance
    """
    default = "cdb2.2_Auto"
    added = 0
    for le_obj in self.lexical_items():

        provenance_tag = le_obj.provenance()

        if provenance_tag is None:
            added += 1
            le_obj.sense_el.attrib["provenance"] = default

def stats_num_synsets(self):
    """
    return number of synsets (length of self.syn_ids)

    @rtype: int
    @return: number of synsets
    """
    return len(self.syn_ids)

def stats_num_les(self):
    """
    return number of lexical entries

    @rtype: int
    @return: number of lexical entries
    """
    num_les = 0
    for le_el in self.lexical_items():
        num_les += 1

    return num_les

def stats_rels(self):
    """
    Get number of synset relations.

    @rtype: int
    @return: number of synset relations
    """
    num_rels = 0
    impossible = []

    for sy_obj in self.synsets():
        existing = []

        for rel_obj in sy_obj.all_relations():
            num_rels += 1

            source = sy_obj.id()
            relationtype = rel_obj.relationtype()
            target = rel_obj.target()
            try:
                self.validate_relation(source, relationtype, target)
                if (source, relationtype, target) in existing:
                    impossible.append(rel_obj)
                else:
                    existing.append((source, relationtype, target))
            except ValueError:
                impossible.append(rel_obj)

    return num_rels, impossible

def empty_lemmas(self):
    """
    return number of synoynyms that contain an empty lemma

    @rtype: int
    @return: number of synonym with an empty lemma
    """
    empty_lemmas = 0

    for le_obj in self.lexical_items():
        lemma = le_obj.lemma()
        if not lemma:
            empty_lemmas += 1

    return empty_lemmas

def tops(self):
    """
    return number of tops (synsets without hypernym relation)

    @rtype: int
    @return: number of synsets without hypernyms
    """
    tops = []
    for sy_obj in self.synsets():
        hyperonyms = sy_obj.relations('has_hyperonym')
        if not hyperonyms:
            tops.append(sy_obj.id())

    return tops

def stats_empty_synsets(self):
    """
    method to obtains the following stats:
    (1) number of empty synsets (no synonyms)
    (2) number of empty odwn synsets (+ of which leave nodes)
    (3) number of empty pwn  synsets (+ of which leave nodes)

    @rtype: tuple
    @return: (num_empty_synsets,
              num_empty_odwn_synsets,
              num_empty_pwn_synsets,
              empty_odwn_leave_synsets)
    """
    non_empty_synsets = set()

    for le_obj in self.lexical_items():
        target = le_obj.synset_id()
        non_empty_synsets.update([target])

    empty_synsets = set(self.syn_ids.keys()) - non_empty_synsets

    empty_odwn_synsets = [sy_id for sy_id in empty_synsets if sy_id.startswith("odwn")]
    empty_pwn_synsets  = [sy_id for sy_id in empty_synsets if sy_id.startswith("eng")]

    leave_empty_odwn_synsets = set()
    leave_pwn_synsets = set()

    for sy_obj in self.synsets():
        sy_id    = sy_obj.id()
        hyponyms = sy_obj.relations('has_hyponym')
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
    """
    return number of
    synsets without gloss + number of empty glosses + number of one word
    glosses

    @rtype: tuple
    @return: sy_no_gloss,empty_glosses,one_word
    """
    sy_no_gloss   = 0
    empty_glosses = 0
    one_word      = 0

    for sy_obj in self.synsets():

        glosses = sy_obj.glosses()

        if not glosses:
            sy_no_gloss += 1

        for gloss in glosses:
            if not gloss:
                empty_glosses += 1

            split = gloss.split()
            if len(split) == 1:
                one_word += 1

    return sy_no_gloss, empty_glosses, one_word

def count_pos(self):
    """
    return number of nouns and verbs

    @rtype: tuple
    @return: list of tuples (pos,count)
    """
    pos = defaultdict(int)

    for sy_obj in self.synsets():

        part_of_speech = sy_obj.pos()
        pos[part_of_speech] += 1

    return sorted(pos.items())


def resources_check(self):
    """
    count provenances

    @rtype: dict
    @return: list of tuples (resource,count)
    """
    resources_dict = defaultdict(int)

    for le_el in self.lexical_items():

        resource_tag = le_el.provenance()

        if resource_tag is None:
            resources_dict['None'] += 1

        else:
            resources = resource_tag.split("+")
            for resource in resources:
                resources_dict[resource] += 1

    return sorted(resources_dict.items())

def missing_bidirectional_relations(self,rel1,rel2):
    """
    given two relations that imply each other,
    for example has_hyponym and has_hyperonym,
    this method returns the relations to add

    @type  rel1: str
    @param rel1: relation, for example 'has_hyponym'

    @type  rel2: str
    @param rel2: relation, for example 'has_hyperonym'

    @rtype: list
    @return: list of 3-tuples (source synset, target synset, relation)
    """
    rels = {}

    for sy_obj in self.synsets():
        source_synset = sy_obj.id()

        for rel_el in sy_obj.all_relations():
            relationtype = rel_el.relationtype()

            if relationtype in [rel1, rel2]:
                tarsynset = rel_el.target()
                rel = (source_synset, tarsynset, relationtype)
                key = tuple(sorted([source_synset, tarsynset]))
                if key not in rels:
                    rels[key] = defaultdict(list)
                rels[key]['relationtypes'].append(relationtype)
                rels[key]['rels'].append(rel)

    rels_to_add = []
    goal = set([rel1, rel2])
    for value in rels.values():
        if set(value['relationtypes']) != goal:

            source, target, relationtype = value['rels'][0]
            miss_relationtypes = goal.difference(set(value['relationtypes']))
            for rel_to_add in miss_relationtypes:
                rels_to_add.append((target, source, rel_to_add))

    return rels_to_add

def polysemy_dict(self):
    """
    return polysemy dict
    mapping polysemy to list of lemmas

    @rtype: dict
    @return: mapping polysemy to list of lemmas
    """
    polysemy_dict = defaultdict(list)

    for lemma, polysemy in self.lemmas().items():
        polysemy_dict[polysemy].append(lemma)

    total = 0.0
    instance = 0.0
    for polysemy, list_lemmas in polysemy_dict.items():
        total += (polysemy * len(list_lemmas))
        instance += len(list_lemmas)
    average_polysemy = round(total/instance, 1)

    return average_polysemy, polysemy_dict




def sy_no_rels(self):
    """
    find synsets without relations

    @rtype: set
    @return: set of synset identifiers
    """
    no_rels = set()

    for sy_obj in self.synsets():

        if not any([sy_obj.relations("has_hyponym"),
                    sy_obj.relations("has_hyperonym")]):
            no_rels.update([sy_obj.id()])

    return no_rels

def contradicting_rels(self):
    """
    method to identify different relationtypes linking the same source
    and target

    @rtype: dict
    @return: mapping (source,target) -> list of rel_obj
    """
    contradicting = defaultdict(list)

    for sy_obj in self.synsets():
        source = sy_obj.id()

        for rel_obj in sy_obj.all_relations():

            relationtype = rel_obj.relationtype()
            target = rel_obj.target()
            contradicting[(source, target)].append(relationtype)

    keys_to_remove = [key
                      for key, value in contradicting.items()
                      if len(value) <= 1]

    for key in keys_to_remove:
        del contradicting[key]

    return contradicting

def stats_large_synsets(self):
    """
    creates a dict mapping synset identifier to
    find large synsets
    """
    freq = {}

    for le_obj in self.lexical_items():
        target = le_obj.synset_id()
        annotated = le_obj.annotator() != ''
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
    """

    """
    rootDir = os.path.join(self.cwd,'user_input')
    for dirName, subdirList, fileList in os.walk(rootDir):
        for fname in fileList:
            if fname.endswith('50.bin'):
                user_bin = os.path.join(dirName,fname)
                evaluation,d = pickle.load(open(user_bin,'rb'))
                print(fname,evaluation)
