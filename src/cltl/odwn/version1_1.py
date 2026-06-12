import os 
import sys

from odwn import Wn_grid_parser

from datetime import datetime

with open('log.txt','w') as outfile:
    outfile.close()

def log_it(message):
    with open("log.txt","a") as outfile:
        outfile.write(str(datetime.now())+"\t"+message+"\n")
#here
cwd             = os.path.dirname(os.path.realpath(__file__))
omegawiki       = "{cwd}/odwn/resources/wn-omegawiki-nld.txt".format(**locals())
wiktionary      = "{cwd}/odwn/resources/wn-wiktionary-nld.txt".format(**locals())
google          = "{cwd}/odwn/resources/wn-google-nld.txt".format(**locals())

#load it
log_it("starting")

instance = Wn_grid_parser(Wn_grid_parser.odwn)

log_it("start cleaning")

#clean it
instance.clean()

log_it('done cleaning')
#remove all babelnet + wiktionary + google_api results
for resource in ['babelnet','google_api','wiktionary']:
    log_it("removing %s" % resource)
    instance.les_remove_a_resource(resource)

#add results antoni + google monosemous results
def add_antoni():
    pos_dict = {'n':'noun','v':'verb'}
    for results in [omegawiki,wiktionary,google]:
        if results.endswith("omegawiki-nld.txt"):
            provenance = "omegawiki"
        elif results.endswith("wn-wiktionary-nld.txt"):
            provenance = "wiktionary"
        elif results.endswith("wn-google-nld.txt"):
            provenance = "google"
    
        with open(results) as infile:
            for counter,line in enumerate(infile):
                offset_pos,lemma = line.strip().split("\t")
                synset_identifier    = "eng-30-{offset_pos}".format(**locals())
                short_pos            =  synset_identifier[-1]
                if short_pos not in ['n','v']:
                    continue

                if counter % 100 == 0:
                    log_it("_".join([provenance,str(counter),synset_identifier,lemma]))

                long_pos             =  pos_dict[short_pos]
                                
                instance.les_add_le(lemma,
                                    long_pos,
                                    short_pos,
                                    synset_identifier,
                                    provenance,
                                    definition="",
                                    sense_id=None,
                                    sense_number=None)
            

log_it("adding antoni and google")
add_antoni()

log_it("gathering stats")
instance.get_stats(verbose=True)

instance.clean()

#export
output_path = os.path.join(cwd,'odwn','resources','odwn','odwn_orbn_gwg-LMF_1.1.xml')
instance.export(output_path)
