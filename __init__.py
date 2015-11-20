import os 
import sys
import subprocess

cwd             = os.path.dirname(os.path.realpath(__file__))
sys.path.append(cwd)


#source virtual env or activate it
#source_command = "source {cwd}/python_env_3.4/bin/activate".format(**locals())

#try:
#    cmd_output = subprocess.check_output(source_command,shell=True)
#except subprocess.CalledProcessError:
#    print ('''please first run 'bash install.sh' from the command line \
#from inside the module and try again''') 
    
from wn_grid_parser import Wn_grid_parser

#documentation attributes
Wn_grid_parser.odwn           = os.path.join(cwd,
                               'resources',
                               'odwn',
                               'odwn_orbn_gwg-LMF_1.3.xml.gz')
Wn_grid_parser.orbn           = os.path.join(cwd,
                                'resources',
                                'odwn',
                                'orbn_1.0.xml')
Wn_grid_parser.rbn            = os.path.join(cwd,
                                'resources',
                                'odwn',
                                'cdb_lu.xml')
Wn_grid_parser.dtd            = os.path.join(cwd,
                                'resources',
                                'odwn',
                                'odwn-orbn-lmf.dtd')
Wn_grid_parser.README         = open(os.path.join(cwd,"README.md")).read()
Wn_grid_parser.LICENSE        = open(os.path.join(cwd,"LICENSE.md")).read()
Wn_grid_parser.__author__     = "Marten Postma"
Wn_grid_parser.__license__    = "CC-BY-SA 4.0"
Wn_grid_parser.__version__    = "1.3"
Wn_grid_parser.__maintainer__ = "Marten Postma"
Wn_grid_parser.__email__      = "martenp@gmail.com"
Wn_grid_parser.__status__     = "development"
