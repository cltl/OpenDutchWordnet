

class LexicalEntry():
    """
    class from XML element LexicalEntry

    .. highlight::
        <LexicalEntry id="havenplaats-n-1">
        <Lemma partOfSpeech="noun" writtenForm="havenplaats"/>
        <Sense id="o_n-109910434"
               provenance="cdb2.2_Auto"
               synset="eng-30-08633957-n/>
    """
    def __init__(self, le_el, lexicon_el):
        self.le_el = le_el
        self.sense_el = self.le_el.find("Sense")
        self.lexicon_el = lexicon_el

    def id(self):
        """
        Get identifier of lexical entry by returning attribute "id".

        :rtype: str
        :return: identifier of lexical entry
        """
        return self.le_el.get("id")

    def lemma(self):
        """
        Get attribute "writtenForm" from child "Lemma".

        :rtype: str
        :return: lemma of le
        """
        self.lemma_el = self.le_el.find("Lemma")
        if self.lemma_el is not None:
            return self.lemma_el.get("writtenForm")
        else:
            return None

    def pos(self):
        """
        Grt "partOfSpeech" attribute (noun | verb) of lexical entry.

        :rtype: str
        :return: noun | verb. None if not found.
        """
        return self.le_el.get("partOfSpeech")

    def sense_id(self):
        """
        return sense id from open referentie bestand nederlands
        by returning attribute "id" from child element "Sense"

        :rtype: str
        :return: sense id from open referentie bestand nederlands.
        None if not found
        """
        return self.sense_el.get("id")

    def annotator(self):
        """
        return manual annotator (default is '')
        by returning attribute 'annotator' from child element 'Sense'

        :rtype: str
        :return: manual annotator (default '')
        """
        return self.sense_el.get('annotator')

    def sense_number(self):
        """
        return sense number
        by returning attribute "senseId" from child element "Sense"

        :rtype: int
        :return: sense number, None if not found
        """
        return self.sense_el.get("senseId")

    def provenance(self):
        """
        get provenance of lexical entry by returning
        attribute "provenance" from child element "Sense"

        :rtype: str
        :return: provenance (source concatenated by "+")
        """

        return self.sense_el.get("provenance")

    def definition(self):
        """
        Get definition of lexical entry by returning
        attribute 'definition' from child element 'Sense'

        :rtype: str
        :return: definition
        """
        return self.sense_el.get('definition')

    def synset_id(self):
        """
        Return synset identifier to which lexical entry belongs.

        :rtype: str
        :return: synset identifier. None if not found
        """
        return self.sense_el.get("synset")

    def remove(self):
        """Remove lexical entry element."""
        try:
            self.lexicon_el.remove(self.le_el)
            return (True,'')
        except ValueError:
            return (False,'could not remove %s' % self.id())
