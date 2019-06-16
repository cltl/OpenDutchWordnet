

class Relation():
    """
    Class for XML element Synset.

    <SynsetRelation provenance="pwn" relType="has_hyperonym" target="eng-30-00322847-v"/>
    """
    def __init__(self, relation_el):
        self.relation_el = relation_el

    def provenance(self):
        """
        return value provenance attribute

        @rtype: str
        @return: provenance tag
        """
        return self.relation_el.get("provenance")

    def relationtype(self):
        """
        return value relType attribute

        @rtype: str
        @return: relType tag
        """
        return self.relation_el.get("relType")

    def target(self):
        """
        return value target attribute

        @rtype: str
        @return: synset target of relation
        """
        return self.relation_el.get("target")

    def remove(self):
        """
        remove relation element
        """
        self.relation_el.getparent().remove(self.relation_el)
