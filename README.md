#Global WordNet Grid LMF parser

This repo provides a python module to work with Open Dutch WordNet.
Please first check the [Issues](https://github.com/MartenPostma/OpenDutchWordnet/issues) to see if your question has already
been answered. It was created using python 3.4. The most recent version (1.3) of the resource can be
found [here](https://github.com/MartenPostma/OpenDutchWordnet/raw/master/resources/odwn/odwn_orbn_gwg-LMF_1.3.xml.gz).
Three pdf files in this repository document the resource:
* [odwn_documentation.pdf](https://github.com/MartenPostma/OpenDutchWordnet/raw/master/odwn_documentation.pdf): technical report of the creation of version 1.0
* [gwc2016_odwn13.pdf](https://github.com/MartenPostma/OpenDutchWordnet/raw/master/gwc2016_odwn13.pdf): paper accepted at [the Global WordNet Conference 2016](http://gwc2016.racai.ro/)
* [slides_gwc2016_odwn13.pdf](https://github.com/MartenPostma/OpenDutchWordnet/raw/master/slides_gwc2016_odwn13.pdf): slides from presentating odwn at [the Global WordNet Conference 2016](http://gwc2016.racai.ro/)

If you make use of the resource and/or this repository, please cite the following reference:

@InProceedings{Postma:Miltenburg:Segers:Schoen:Vossen:2016,
  author =	 "Marten Postma and Emiel van Miltenburg and Roxane Segers and Anneleen Schoen and Piek Vossen",
  title =	 "Open {Dutch} {WordNet}",
  booktitle =	 "Proceedings of the Eight Global Wordnet Conference",
  year =	 2016,
  address =	 "Bucharest, Romania",
}

##USAGE AND INSTALL
git clone this repository.

The python module 'lxml' is needed. Hopefully, 'pip install lxml'
will do the trick. If you prefer using a virtual environment,
everything should be installed by calling
'bash install.sh' in the module directory.
Don't forget to source your virtual environment each time you use the module.

Epydoc was used to document the code (http://epydoc.sourceforge.net/).
The documentation can be found [here](http://htmlpreview.github.io/?https://github.com/MartenPostma/OpenDutchWordnet/blob/master/html/odwn.wn_grid_parser.Wn_grid_parser-class.html).
The general idea of the module is that it consists of a lot of classes which are
inherited by the main class 'Wn_grid_parser'.

```shell
python

>>> from OpenDutchWordnet import Wn_grid_parser

#please check the attribute LICENSE before using this module
>>> print(Wn_grid_parser.LICENSE)

#the attribute 'odwn' stores the path to the most recent version
>>>print(Wn_grid_parser.odwn)

#example of how to use module
>>> instance = Wn_grid_parser(Wn_grid_parser.odwn)

>>> le_el = instance.les_find_le("havenplaats-n-1")
>>> le_el.get_id()
'havenplaats-n-1'
>>> le_el.get_lemma()
'havenplaats'
>>> le_el.get_pos()
'noun'
>>> le_el.get_sense_id()
'o_n-109910434'
>>> le_el.get_provenance()
'cdb2.2_Auto'
>>> le_el.get_synset_id()
'eng-30-08633957-n'

>>> synset_el = instance.synsets_find_synset('eng-30-00324560-v')
>>> synset_el.get_id()
'eng-30-00324560-v'
>>> synset_el.get_ili()
'i23355'
>>> relation_el = synset_el.get_relations("has_hyperonym")[0]
>>> relation_el.get_provenance()
'pwn'
>>> relation_el.get_reltype()
'has_hyperonym'
>>> relation_el.get_target()
'eng-30-00322847-v'

```	                  
##Contact
* Piek Vossen (piek.vossen@vu.nl)
