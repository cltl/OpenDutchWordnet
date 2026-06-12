echo "if you only see this message, then the unit test was succesful"
python3 -m doctest -o FAIL_FAST wn_grid_parser.py


echo 'epydoc --html relation.py lemma.py configuration.py clean.py synset.py le.py user_input.py orbn.py les.py stats.py synsets.py wn_grid_parser.py'
