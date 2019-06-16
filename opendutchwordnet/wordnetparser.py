import os
import gzip

from collections import defaultdict
from .configuration import xml_paths
from .lexicalentry import LexicalEntry
from .synset import Synset

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
        self._path_wn_grid_lmf = path_wn_grid_lmf

        # read xml file and set general variables
        infile = gzip.GzipFile(self._path_wn_grid_lmf)
        self._doc = etree.parse(infile,
                                etree.XMLParser(remove_blank_text=True))
        self._lexicon_el = self._doc.find("Lexicon")
        self._relationtypes = {}
        self._syn_ids = {}
        self._cwd = os.path.dirname(os.path.realpath(__file__))

        # make xml paths class attributes
        [setattr(self, key, value) for key, value in xml_paths.items()]

        # set of synset identifiers
        self._syn_ids = {sy_el.id(): 0
                         for sy_el in self.synsets()}

        # relations
        self._relationtypes = {rel_obj.relationtype(): ""
                               for sy_obj in self.synsets()
                               for rel_obj in sy_obj.all_relations()}

        self._orbn_ids = {le_obj.sense_id(): ""
                          for le_obj in self.lexical_items()}

    def lemmas(self, pos=None):
        """
        Get all lemmas.

        @type  pos: str
        @param pos: noun | verb.
        Default is None, then no filtering is performed.
        """
        lemmas = set()

        for le_obj in self.lexical_items():
            if pos is not None and pos != le_obj.pos():
                continue
            lemmas.add(le_obj.lemma())

        return lemmas

    def lexical_item_by_lemma(self, lemma, pos=None):
        """
        Return all lexical items with a given lemma.

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
        Return the number of senses for a lemma.

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
        Return all lexical items.

        @type  mw: bool
        @param mw: default is False, multi-words will be ignored.
        if set to True, multi-words will be returned.

        @rtype: generator
        @return: generator of LexicalEntry XML elements
        """
        for l in self._doc.iterfind(self._path_to_le_els):
            instance = LexicalEntry(l, self._lexicon_el)
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

    def lexical_item_by_synset(self, synset_identifier):
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
        for synset_el in self._doc.iterfind(self._path_to_synset_els):
            yield Synset(synset_el,
                         self._relationtypes,
                         self._syn_ids)

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
