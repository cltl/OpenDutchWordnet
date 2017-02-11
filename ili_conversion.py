"""
dtd: https://github.com/globalwordnet/schemas/blob/master/WN-LMF.dtd
example: https://github.com/globalwordnet/schemas/blob/master/example.xml

FROM
<LexicalEntry id="elektroforetisch-a-1" partOfSpeech="adjective">
       <Lemma writtenForm="elektroforetisch"/>
       <WordForms/>
       <Morphology/>
       <MorphoSyntax/>
       <Sense definition="" id="o_a-73337" provenance="google+bing" senseId="1" synset="eng-30-02718845-a">
         <SenseRelations/>
         <Semantics-adjective/>
         <Pragmatics/>
       </Sense>
</LexicalEntry>

TO
<LexicalEntry id="w1">
    <Lemma writtenForm="grandfather" partOfSpeech="n"/>
    <Sense id="example-10161911-n-1" synset="example-10161911-n">
    </Sense>
</LexicalEntry>

TODO:
    1. senseId?
    2. provenance?
    3. mapping pos
    4. synset identifier -> list of definitions

FROM
<Synset id="eng-30-06618427-n" ili="i71250">
       <Definitions>
         <Definition gloss="(film) an abrupt transition from one scene to another" language="en" provenance="pwn"/>
       </Definitions>
       <SynsetRelations>
         <SynsetRelation provenance="pwn" relType="has_hyperonym" target="eng-30-06401328-n"/>
       </SynsetRelations>
</Synset>

TO
<Synset id="example-1-n" ili="in">
        <Definition>A father&apos;s father; a paternal grandfather</Definition>
        <!-- You can include metadata (such as source) at many points -->
        <!-- The ILI Definition must be at least 20 characters or five words -->
        <ILIDefinition dc:source="https://en.wiktionary.org/wiki/farfar">A father&apos;s father; a paternal grandfather</ILIDefinition>
        <SynsetRelation relType="hypernym" target="example-10162692-n"/>

</Synset>

TODO:
    1. mapping relations
    2. check provenance

QUESTIONS:
    1. difference sense example and synset definition

Proposal input format new ili's:
1.

"""
from lxml import etree
from __init__ import Wn_grid_parser
from datetime import datetime

reltypes_mapping = {'near_antonym': 'antonym',
                    'fuzzynym': 'other',

                    'has_mero_location': 'mero_location',
                    'has_mero_member': 'mero_member',

                    'role_source_direction': 'source_direction',
                    'role_patient': 'patient',
                    'role_result': 'result',
                    'role_instrument': 'instrument',
                    'role_direction': 'direction',
                    'role_location': 'location',
                    'role_agent': 'agent',
                    'role_target_direction': 'target_direction',

                    'has_subevent': 'subevent',

                    'has_hyperonym': 'hypernym',
                    'has_xpos_hyperonym': 'hypernym',
                    'has_hyponym': 'hyponym',
                    'has_xpos_hyponym': 'hyponym',
                    'has_meronym': 'meronym',
                    'has_holonym': 'holonym',

                    'has_mero_madeof': 'mero_substance',
                    'has_mero_portion': 'mero_portion',
                    'has_mero_part': 'mero_part',

                    'has_holo_portion': 'holo_portion',
                    'has_holo_member': 'holo_member',
                    'has_holo_location': 'holo_location',
                    'has_holo_part': 'holo_substance',
                    'has_holo_madeof': 'holo_substance',

                    'instance': 'instance_hypernym',

                    'near_synonym': 'eq_synonym'}


rbn_ids = set()
odwn_ids = {}
with open('resources/cili/new_synsets_v2.csv') as infile:
    next(infile)
    # rbn ids index 1
    # odwn_ids index 2
    # Ilidefinitions index 7
    for line in infile:

        split = line.strip().split('\t')
        if len(split) < 8:
            continue
        rbn_id, odwn_id, ilidef = split[1], split[2], split[7]
        if all([ilidef,
                ilidef != 'x']):
            rbn_ids.add(rbn_id)
            odwn_ids[odwn_id] = ilidef

def validate(dtd_path, loaded_xml):
    '''
    validate against dtd

    :param str dtd_path: full path to dtd

    :rtype: tuple
    :return: (succes,message)
    '''
    f = open(dtd_path)
    dtd = etree.DTD(f)
    message = ""

    succes = dtd.validate(loaded_xml)
    if not succes:
        message = dtd.error_log.filter_from_errors()[0]

    return (succes, message)


print('start', datetime.now())

dtd_path = 'resources/cili/WN-LMF-1.0.dtd'
starting_point_path = 'resources/cili/the_starting_point.xml'
old = Wn_grid_parser(Wn_grid_parser.odwn)
root = old.doc.getroot()

parser = etree.XMLParser(remove_blank_text=True)
new = etree.parse(starting_point_path, parser)
lexicon_el = new.find('Lexicon')


debug = True
# TODO: think about CDATA format for strings


# which synsets to add
added_synsets = set()
# loop through Synsets
for synset_obj in old.synsets_get_generator():
    ili = synset_obj.get_ili()
    synset_id = synset_obj.get_id()
    if all([ili is not None,
            synset_id]):
        added_synsets.add(synset_id)

    if synset_id in odwn_ids:
        added_synsets.add(synset_id)


# add LexicalEntries
added_sense_ids = set()
for counter, le_obj in enumerate(old.les_get_generator()): # mw not taken into account

    synset_id = le_obj.get_synset_id()
    sense_id = le_obj.get_sense_id()

    if all([synset_id,
            sense_id not in added_sense_ids]):
        if synset_id in added_synsets:

            # TODO: add sense examples
            lexical_entry_el = etree.SubElement(lexicon_el, 'LexicalEntry',
                                                attrib={'id': 'w%s' % counter})

            etree.SubElement(lexical_entry_el, 'Lemma',
                             attrib={'writtenForm': le_obj.get_lemma(),
                                     'partOfSpeech': le_obj.get_pos()[0]})

            etree.SubElement(lexical_entry_el, 'Sense', attrib={'id': le_obj.get_sense_id(),
                                                                'synset': synset_id})

            lexical_entry_el.tail = '\n'

            added_sense_ids.add(sense_id)
            #if debug:
            #    etree.dump(lexical_entry_el)
            #    input('continue?')

# Add tweet-n
lexical_entry_el = etree.SubElement(lexicon_el, 'LexicalEntry',
                                                attrib={'id': 'w1000000'})

etree.SubElement(lexical_entry_el, 'Lemma',
                 attrib={'writtenForm': 'tweet',
                         'partOfSpeech': 'n'})

etree.SubElement(lexical_entry_el, 'Sense', attrib={'id': 'r_1',
                                                    'synset': 'odwn-10-00000001-n'})

lexical_entry_el.tail = '\n'
added_sense_ids.add('r_1')

# Add tweet-v
lexical_entry_el = etree.SubElement(lexicon_el, 'LexicalEntry',
                                    attrib={'id': 'w1000001'})

etree.SubElement(lexical_entry_el, 'Lemma',
                 attrib={'writtenForm': 'tweet',
                         'partOfSpeech': 'v'})

etree.SubElement(lexical_entry_el, 'Sense', attrib={'id': 'r_2',
                                                    'synset': 'odwn-10-00000002-v'})

lexical_entry_el.tail = '\n'
added_sense_ids.add(sense_id)

# Add Synsets
for synset_obj in old.synsets_get_generator():

    ili = synset_obj.get_ili()
    synset_id = synset_obj.get_id()

    if synset_id in odwn_ids:
        ili = 'in'

    if all([ili is not None,
            synset_id]):
        synset_el = etree.Element('Synset',
                                  attrib={'id': synset_id,
                                          'ili': ili})

        # TODO: add language attribute
        # TODO: add Dutch definitions

        if synset_id.startswith('eng'):
            for def_en in synset_obj.get_glosses(languages=['en']):
                def_el = etree.Element('Definition')
                def_el.text = def_en
                synset_el.append(def_el)

        elif synset_id.startswith('odwn'):

            def_el = etree.Element('Definition')
            def_el.text = odwn_ids[synset_id]
            synset_el.append(def_el)

            def_el = etree.Element('ILIDefinition')
            def_el.text = odwn_ids[synset_id]
            synset_el.append(def_el)




        for rel_obj in synset_obj.get_all_relations():
            reltype = rel_obj.get_reltype()

            # TODO: add dc:source

            target = rel_obj.get_target()
            if all([reltype in reltypes_mapping,
                    target in added_synsets]):
                mapped_reltype = reltypes_mapping[reltype]
                source = rel_obj.get_provenance()
                rel_el = etree.Element('SynsetRelation', attrib={'relType' : mapped_reltype,
                                                                 'target' : target})

                synset_el.append(rel_el)

        #if debug:
        #    etree.dump(synset_el)
        #    input('continue?')

        synset_el.tail = '\n'
        lexicon_el.append(synset_el)

# add synset belonging to tweet-n
synset_el = etree.Element('Synset', attrib={'id': 'odwn-10-00000001-n', 'ili': 'in'})

def_el = etree.Element('Definition')
def_el.text = 'a message or image posted on Twitter'
synset_el.append(def_el)

def_el = etree.Element('ILIDefinition')
def_el.text = 'a message or image posted on Twitter'
synset_el.append(def_el)

rel_el = etree.Element('SynsetRelation', attrib={'relType': 'hypernym',
                                                 'target': 'odwn-10-00000001-n'})
synset_el.append(rel_el)

synset_el.tail = '\n'
lexicon_el.append(synset_el)


# add synset belonging to tweet-v
synset_el = etree.Element('Synset', attrib={'id': 'odwn-10-00000002-v', 'ili': 'in'})

def_el = etree.Element('Definition')
def_el.text = 'to post a message or image on Twitter'
synset_el.append(def_el)

def_el = etree.Element('ILIDefinition')
def_el.text = 'to post a message or image on Twitter'
synset_el.append(def_el)

rel_el = etree.Element('SynsetRelation', attrib={'relType': 'hypernym',
                                                 'target': 'eng-30-00742320-v'})
synset_el.append(rel_el)

synset_el.tail = '\n'
lexicon_el.append(synset_el)

# validate
succes, message = validate(dtd_path, new)
print(succes)
print(message)

if succes:
    with open('resources/cili/odwn_cili.xml', "wb") as outfile:
        new.write(outfile,
                  pretty_print=True,
                  xml_declaration=True,
                  encoding='utf-8')

print('end', datetime.now())
# export

