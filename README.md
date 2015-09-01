#Global WordNet Grid LMF parser

This repo provides a python module to work with Open Dutch WordNet. 
It was created using python 3.4.


##USAGE AND INSTALL
git clone this repository.

The python module 'lxml' is needed. Hopefully, 'pip install lxml'
will do the trick. If you prefer using a virtual environment,
everything should be installed by calling 
'bash install.sh' in the module directory.
Don't forget to source your virtual environment each time you use the module.

```shell
python

>>> from opendutchwordnet import Wn_grid_parser

#please check the attribute LICENSE before using this module
>>> print(Wn_grid_parser.LICENSE)

#the attribute 'odwn' stores the path to the most recent version
>>>print(Wn_grid_parser.odwn)

#example of how to use it
>>> instance = Wn_grid_parser(Wn_grid_parser.odwn)


```	                  
##Contact
* Marten Postma
* m.c.postma@vu.nl
* http://martenpostma.com/
* Free University of Amsterdam
