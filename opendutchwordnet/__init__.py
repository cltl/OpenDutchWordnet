"""Init."""
import os
import sys

cwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(cwd)
from wordnetparser import WordnetParser

WordnetParser.odwn = os.path.join(cwd,
                                  'resources',
                                  'odwn',
                                  'odwn_orbn_gwg-LMF_1.3.xml.gz')
WordnetParser.orbn = os.path.join(cwd,
                                  'resources',
                                  'odwn',
                                  'orbn_1.0.xml')
WordnetParser.rbn = os.path.join(cwd,
                                 'resources',
                                 'odwn',
                                 'cdb_lu.xml')
WordnetParser.dtd = os.path.join(cwd,
                                 'resources',
                                 'odwn',
                                 'odwn-orbn-lmf.dtd')
WordnetParser.README = open(os.path.join(cwd, "../README.md")).read()
WordnetParser.LICENSE = open(os.path.join(cwd, "../LICENSE.md")).read()
WordnetParser.__author__ = "Marten Postma"
WordnetParser.__license__ = "CC-BY-SA 4.0"
WordnetParser.__version__ = "1.3"
WordnetParser.__maintainer__ = "Marten Postma"
WordnetParser.__email__ = "martenp@gmail.com"
WordnetParser.__status__ = "development"
