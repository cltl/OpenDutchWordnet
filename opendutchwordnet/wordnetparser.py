import os
import pickle
import gzip
import subprocess

from collections import defaultdict
from configuration import xml_paths
from relation import Relation
from lexicalentry import LexicalEntry
from synset import Synset

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree


class WordnetParser(object):
    """
    @type  path_wn_grid_lmf: str
    @param path_wn_grid_lmf: path to wn grid lmf file

    @ivar  path_wn_grid_lmf: str
    @param path_wn_grid_lmf: path to wn grid lmf file

    @ivar  doc: lxml.etree._ElementTree
    @param doc: param path_wn_grid_lmf parsed with etree.parse

    >>> path="resources/odwn/odwn_orbn_gwg-LMF_1.2.xml.gz"
    >>> instance = Wn_grid_parser(path_wn_grid_lmf=path)

    >>> le_el = instance.les_find_le("havenplaats-n-1")
    >>> le_el.id()
    'havenplaats-n-1'
    >>> le_el.lemma()
    'havenplaats'
    >>> le_el.pos()
    'noun'
    >>> le_el.sense_id()
    'o_n-109910434'
    >>> le_el.provenance()
    'cdb2.2_Auto'
    >>> le_el.synset_id()
    'eng-30-08633957-n'

    >>> synset_el = instance.synsets_find_synset('eng-30-00324560-v')
    >>> synset_el.id()
    'eng-30-00324560-v'
    >>> synset_el.ili()
    'i23355'
    >>> relation_el = synset_el.relations("has_hyperonym")[0]
    >>> relation_el.provenance()
    'pwn'
    >>> relation_el.relationtype()
    'has_hyperonym'
    >>> relation_el.target()
    'eng-30-00322847-v'

    >>> instance.lemma_num_senses("huis",pos="noun")
    6
    """
    def __init__(self, path_wn_grid_lmf):
        self.path_wn_grid_lmf = path_wn_grid_lmf

        # read xml file and set general variables
        infile = gzip.GzipFile(self.path_wn_grid_lmf)
        self.doc = etree.parse(infile, etree.XMLParser(remove_blank_text=True))
        self.lexicon_el = self.doc.find("Lexicon")
        self.relationtypes = {}
        self.syn_ids = {}
        self.cwd = os.path.dirname(os.path.realpath(__file__))

        # make xml paths class attributes
        [setattr(self, key, value) for key,value in xml_paths.items()]

        # set of synset identifiers
        self.syn_ids = {sy_el.id(): 0
                        for sy_el in self.synsets()}

        # relations
        self.relationtypes = {rel_obj.relationtype(): ""
                         for sy_obj in self.synsets()
                         for rel_obj in sy_obj.all_relations()}

        self.orbn_ids = {le_obj.sense_id(): ""
                         for le_obj in self.lexical_items()}

    def random_le_and_sy(self):
        """
        """
        from nltk.corpus import wordnet as wn

        start_at = random.choice(range(len(self.orbn_ids)))

        for counter, le_obj in enumerate(self.lexical_items()):

            if counter >= start_at:
                print()
                print(etree.tostring(le_obj.le_el,
                                     pretty_print=True))
                answer = input('interesting? ')
                if answer == 'y':
                    target = le_obj.synset_id()
                    eng, version, offset, pos = target.split('-')
                    sy_obj = self.find_synset(target)
                    print()
                    print(etree.tostring(sy_obj.synset_el,
                                         pretty_print=True))
                    synset = wn._synset_from_pos_and_offset(pos, int(offset))
                    print(synset.lemmas())
                    print(synset.definition())
                    input('continue?')

    def lexical_items(self, multiword=False):
        """
        Create generator of LexicalEntry elements
        (based on xml path in self.path_to_lus_els)

        @type  mw: bool
        @param mw: default is False, multi-words will be ignored.
        if set to True, multi-words will be returned.

        @rtype: generator
        @return: generator of LexicalEntry XML elements
        """
        for l in self.doc.iterfind(self.path_to_le_els):
            instance = LexicalEntry(l, self.lexicon_el)
            l_id = instance.id()
            if multiword:
                yield instance
            elif "mwe" not in l_id:
                yield instance

    def find_lexical_item(self, le_identifier):
        """
        find lexical entry based on identifier

        @type  le_identifier: str
        @param le_identifier: lexical entry identifier
        (for example havermout-n-1)

        @rtype: instance
        @return: if found, instance of class Le, else None
        """
        for le_el in self.lexical_items():
            if le_el.id() == le_identifier:
                return le_el
        else:
            return None

    def synset(self, synset_identifier):
        """
        Get all les of a synset (for example 'eng-30-00324560-v').

        @rtype: list
        @return: list of class instances of Class Le
        """
        return [l for l in self.lexical_items()
                if l.synset_id() == synset_identifier]

    def add_lexical_item(self,
                         lemma,
                         long_pos,
                         short_pos,
                         synset_identifier,
                         provenances,
                         definition="",
                         sense_id=None,
                         sense_number=None,
                         annotator=None):
        """
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
        """
        all_les_of_one_synset = [le_obj for le_obj in self.synset(synset_identifier)]

        # WARNING: if lemma,pos already occurs in synset, le will not be added
        # but provenance will be changed
        for le_obj in all_les_of_one_synset:
            l, p = le_obj.lemma(), le_obj.pos()

            # change provenance
            if (lemma, long_pos) == (l,p):
                provenance_tag = le_obj.provenance()
                for provenance in provenances:
                    if provenance not in provenance_tag:
                        provenance_tag += "+"+provenance
                le_obj.sense_el.attrib['provenance'] = provenance_tag

            # change annotator tag if needed
            if annotator is not None:
                annotator_tag = le_obj.annotator()
                if annotator not in annotator_tag:
                    annotator_tag += '+'+annotator
                le_obj.sense_el.attrib['annotator'] = annotator_tag

        # WARNING:if sense_id already exists for this lemma,le will not be added
        sense_ids = [le_obj.sense_id() for le_obj in all_les_of_one_synset]

        if sense_id is not None and sense_id in sense_ids:
            raise ValueError("sense_id %s already in sense ids of synset"
                             "{}".format(sense_id))

        # create orbn_id
        if sense_id is None:
            sense_id = self.add_sense(short_pos)

        # create lexical entry
        if sense_number is None:
            sense_number = self.lemma_highest_sense_number(lemma, pos=long_pos) + 1

        # <LexicalEntry id="leuningstoel-n-1" partOfSpeech="noun">
        le_att = {'id': "{lemma}-{short_pos}-{sense_number}".format(**locals()),
                  'partOfSpeech': long_pos}

        # <Lemma writtenForm="leuningstoel"/>
        lemma_att = {'writtenForm': lemma}

        # <Sense id="o_n-104340805" senseId="1" definition=""
        #  synset="eng-30-02738535-n" provenance="cdb2.2_Auto">
        sense_att = {'id':         sense_id,
                     'senseId':    str(sense_number),
                     'definition': definition,
                     'synset':     synset_identifier,
                     'provenance': "+".join(provenances)}

        # add manual annotator info
        if annotator is not None:
            sense_att['annotator'] = annotator

        new_le_el = etree.Element("LexicalEntry", attrib=le_att)
        children = ['Lemma', 'WordForms', 'Morphology', 'MorphoSyntax', 'Sense']
        sense_children = ["SenseRelations", "Semantics-%s" % long_pos,
                          "Pragmatics"]

        for element_name in children:
            attrib = {}

            if element_name == "Lemma":
                attrib = lemma_att
            elif element_name == "Sense":
                attrib = sense_att

            new_sub_el = etree.Element(element_name, attrib)
            if element_name == "Sense":
                for sense_child in sense_children:
                    new_sub_sub_el = etree.Element(sense_child)
                    new_sub_el.append(new_sub_sub_el)

            new_le_el.append(new_sub_el)

        self.lexicon_el.insert(0, new_le_el)
        self.orbn_ids[sense_id] = ""

    def lemmas(self, pos=None):
        """
        Dict of all lemmas.

        @type  pos: str
        @param pos: noun | verb.
        Default is None, then no filtering is performed.
        """
        lemmas = defaultdict(int)

        for le_obj in self.lexical_items():
            lemma = le_obj.lemma()

            if pos:
                part_of_speech = le_obj.pos()
                if pos == part_of_speech:
                    lemmas[lemma] += 1

            else:
                lemmas[lemma] += 1

        return lemmas

    def lexical_item_by_lemma(self, lemma, pos=None):
        """
        return generator of Le class instances

        @type  lemma: str
        @param lemma: lemma

        @type  pos: str
        @param pos: noun | verb.
        Default is None, then no filtering is performed.

        @rtype: list
        @return: list of Le class instances
        """
        les = []

        for le_obj in self.lexical_items():
            can_lemma = le_obj.lemma()

            if can_lemma == lemma:

                if pos:
                    part_of_speech = le_obj.pos()
                    if pos == part_of_speech:
                        les.append(le_obj)

                else:
                    les.append(le_obj)

        return les

    def num_senses(self, lemma, pos=None):
        """
        return number of senses for a lemma.

        @type  lemma: str
        @param lemma: lemma

        @type  pos: str
        @param pos: noun | verb.
        Default is None, then no filtering is performed.

        @rtype: int
        @return: number of senses
        """
        return len(self.lexical_item_by_lemma(lemma, pos))

    def lexical_items(self, multiword=False):
        """
        Create generator of LexicalEntry elements
        (based on xml path in self.path_to_lus_els)

        @type  mw: bool
        @param mw: default is False, multi-words will be ignored.
        if set to True, multi-words will be returned.

        @rtype: generator
        @return: generator of LexicalEntry XML elements
        """
        for l in self.doc.iterfind(self.path_to_le_els):
            instance = LexicalEntry(l, self.lexicon_el)
            l_id = instance.id()
            if multiword:
                yield instance
            elif "mwe" not in l_id:
                yield instance

    def find_lexical_item(self, le_identifier):
        """
        find lexical entry based on identifier

        @type  le_identifier: str
        @param le_identifier: lexical entry identifier
        (for example havermout-n-1)

        @rtype: instance
        @return: if found, instance of class Le, else None
        """
        for le_el in self.lexical_items():
            if le_el.id() == le_identifier:
                return le_el
        else:
            raise ValueError("No lexical item with identifier: "
                             "{}".format(le_identifier))

    def synset(self, synset_identifier):
        """
        Get all les of a synset (for example 'eng-30-00324560-v').

        @rtype: list
        @return: list of class instances of Class Le
        """
        return (l for l in self.lexical_items()
                if l.synset_id() == synset_identifier)

    def _load_synonym_dict(self):
        """
        Load dicts to obtain synonyms of lemma.

        :rtype: dict
        :return: mapping from lemma to set of synonyms
        """
        self.synset2lemmas = defaultdict(set)
        self.lemma2synsets = defaultdict(set)

        for le_obj in self.lexical_items():

            lemma = le_obj.lemma()
            synset_id = le_obj.synset_id()

            if lemma is not None and synset_id is not None:
                self.synset2lemmas[synset_id].add(lemma)
                self.lemma2synsets[lemma].add(synset_id)

        #  We don't want to keep them as defaultdicts
        #  we might create garbage synsets by accident.
        self.synset2lemmas = dict(self.synset2lemmas)
        self.lemma2synsets = dict(self.lemma2synsets)

    def synonyms(self, lemma):
        """
        Get the synonyms of a lemma.

        :param str lemma: a lemma (for example 'paard')

        :rtype: set
        :return: set of synonyms of the lemma according to odwn
        """
        if not all([hasattr(self, 'synset2lemmas'),
                    hasattr(self, 'lemma2synsets')]):
            self._load_synonym_dict()

        synonyms = set()
        for synset_id in self.lemma2synsets[lemma]:
            synonyms.update(self.synset2lemmas[synset_id])

        return synonyms

    def synsets(self):
        """
        create generator of Synset elements
        (based on xml path in self.path_to_synset_els)

        @rtype: generator
        @return: generator of Synset XML elements
        """
        for synset_el in self.doc.iterfind(self.path_to_synset_els):
            yield Synset(synset_el,
                         self.relationtypes,
                         self.syn_ids)

    def find_synset(self, synset_identifier):
        """
        find synset based on identifier

        @type  synset_identifier: str
        @param synset_identifier: synset identifier
        (for example eng-30-00325085-v)

        @rtype: instance
        @return: if found, instance of class Synset, else None
        """
        for synset_el in self.synsets():
            if synset_el.id() == synset_identifier:
                return synset_el
        else:
            raise ValueError("No synset found.")

    def synset_definitions(self):
        """
        this method loops over all Synset elements and creates a dict
        mapping from sy_id ->
            'definition' -> definition

        @rtype: dict
        @return: mapping from sy_id ->
            'definition' -> definition
        """
        synset_info = defaultdict(list)
        for sy_obj in self.synsets():
            sy_id = sy_obj.id()
            synset_info[sy_id].extend(sy_obj.glosses())
        return synset_info
