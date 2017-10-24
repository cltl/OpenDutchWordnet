"""

"""
import subprocess
import os

from lxml import etree
from collections import defaultdict


def validate(instance, dtd_path):
    """
    Validate against dtd.

    @type  dtd_path: str
    @param dtd_path: full path to dtd

    @rtype: tuple
    @return: (succes,message)
    """
    f = open(dtd_path)
    dtd = etree.DTD(f)
    message = ""

    succes = dtd.validate(instance.doc)
    if not succes:
        message = dtd.error_log.filter_from_errors()[0]

    return succes, message

def export(instance, output_path, format='lmf'):
    """
    Export resource to file.

    instance.doc is first validated against dtd.
    if this fails, export will not be done

    @type  output_path: str
    @param output_path: output path

    @type  format: str
    @param format: default is 'lmf',

    others include: 'omw', which is the Open Multilingual Wordnet format
    (http://compling.hss.ntu.edu.sg/omw/).
    'ili': mapping between pwn and odwn in rdf
    The output will be stored in the 'resources' folder
    """
    instance.clean()

    # validate it
    try:
        validate(instance.dtd)
    except ValueError as e:
        raise ValueError("Validation was not succesful: "
                         "{}".format(e.message))

    if format == 'lmf':
        with open(output_path, "wb") as outfile:
            instance.doc.write(outfile,
                               pretty_print=True,
                               xml_declaration=True,
                               encoding='utf-8')
    elif format == 'omw':
        instance.omw_export()

    elif format == 'ili':
        instance.ili_map_export()

def ili_map_export(instance):
    """
    Create export file in resources/ili-map-odwnVERSION.ttl.

    Based on the original English one at:
    https://raw.githubusercontent.com/globalwordnet/ili/master/ili-map.ttl
    """
    version = instance.__version__.replace('.', '')
    output_path = os.path.join(instance.cwd,
                               'resources',
                               'ili-map-odwn%s.ttl' % version)

    synonyms_dict = defaultdict(set)
    for le_obj in instance.lexical_items():
        synset_id = le_obj.synset_id()
        lemma = le_obj.lemma()
        synonyms_dict[synset_id].add(lemma)

    with open(output_path, 'w') as outfile:

        outfile.write('\n')
        outfile.write('@prefix\towl:\t<http://www.w3.org/2002/07/owl#> .\n')
        outfile.write('\n')
        outfile.write('### Wordnets\n')
        outfile.write('@prefix\todwn13:\t<http://odwn-rdf.vu.nl/odwn13/> .\n')
        outfile.write('\n')
        outfile.write('### this file\n')
        outfile.write('\n')
        outfile.write('@prefix ili: <http://globalwordnet.org/ili/> .\n')
        outfile.write('@base <http://globalwordnet.org/ili/ili-map.ttl>.\n')
        outfile.write('\n')
        for synset_obj in instance.synsets():
            ili = synset_obj.ili()
            synset_id = synset_obj.id()
            if synset_id.startswith('eng-30'):
                offset_pos = synset_id.replace('eng-30-','')
                if synonyms_dict[synset_id]:
                    synonyms = synonyms_dict[synset_id]
                    outline = 'ili:{ili}\towl:sameAs\todwn13:{offset_pos} . # {synonyms}\n'.format(**locals())
                    outfile.write(outline)


def omw_export(instance):
    """
    this method performs the following steps:
    (1) creates new folder in resources: resources/nld
    (2) copies LICENSE in it
    (3) copies reference in it
    (4) creates wn-data-nld.tab
    """
    cwd = instance.cwd
    out = os.path.join(instance.cwd, 'resources', 'nld')

    # (1) creates new folder in resources: resources/nld
    command = 'rm -rf {} && mkdir {}'.format(out, out)
    subprocess.call(command, shell=True)

    # (2) copies LICENSE in it
    command = 'cp {}/LICENSE.md {}/LICENSE'.format(cwd, out)
    subprocess.call(command, shell=True)

    # (3) copies reference in it
    command = 'cp {}/citation.bib {}/'.format(cwd, out)
    subprocess.call(command, shell=True)

    # (4) creates wn-data-nld.tab
    output_path = os.path.join(out, 'wn-data-nld.tab')
    with open(output_path, 'w') as outfile:

        # write header
        header = '\t'.join([
                            '# Open Dutch WordNet',
                            'nld',
                            'http://wordpress.let.vupr.nl/odwn/',
                            'CC BY SA 4.0'])
        outfile.write(header+'\n')
        for le_obj in instance.lexical_items():

            synset_id = le_obj.synset_id()
            lemma = le_obj.lemma()
            if not synset_id:
                continue
            prov, version, offset, pos = synset_id.split('-')

            if all([prov == 'eng',
                    lemma]):
                output = '{}-{}\tnld:lemma\t{}\n'.format(offset, pos, lemma)
                outfile.write(output)
