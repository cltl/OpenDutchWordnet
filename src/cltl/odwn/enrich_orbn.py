from lxml import etree
from collections import Counter, defaultdict

cdb_lu = etree.parse('resources/cdb_lu.xml')

ids = {cdblu_el.get('c_lu_id')
       for cdblu_el in cdb_lu.xpath('cdb_lu')}


distr = Counter([id_.split('_')[0]
                  for id_ in ids])
print('distribution of prefixes', distr)

distr = Counter([form_el.get('form-cat')
                 for form_el in cdb_lu.xpath('cdb_lu/form')])
print('distribution of pos', distr)

orbn = etree.parse('resources/odwn/orbn_1.0.xml')
orbn_root = orbn.getroot()
orbn_ids = {cdb_lu_el.get('c_lu_id')
            for cdb_lu_el in orbn.xpath('cdb_lu')}
old_total = len(orbn_ids)

ids_to_add = set()
pos_to_add = defaultdict(int)

for cdb_lu_el in cdb_lu.xpath('cdb_lu'):

    id_ = cdb_lu_el.get('c_lu_id')
    prefix = id_.split('_')[0]
    form_el = cdb_lu_el.find('form')
    if form_el is None:
        print('no form element found for', id_)
        continue
    pos = form_el.get('form-cat')

    if all([pos.lower() in {'adj', 'adjective', 'adverb'},
            prefix in {'c', 'r'}]):

        assert id_ not in orbn_ids, f'{id_} already in orbn'

        ids_to_add.add(id_)
        pos_to_add[pos.lower()] += 1

        orbn_root.append(cdb_lu_el)

print('number of ids to add', len(ids_to_add))
print(pos_to_add)
num_added = len(ids_to_add)


orbn_ids = {cdb_lu_el.get('c_lu_id')
            for cdb_lu_el in orbn.xpath('cdb_lu')}
new_total = len(orbn_ids)
assert new_total == (old_total + num_added), f'{new_total} {old_total} {num_added}'


with open('resources/odwn/orbn_n-v-a.xml', 'wb') as outfile:
    orbn.write(outfile,
               pretty_print=True,
               xml_declaration=True,
               encoding='utf-8')


new_orbn = etree.parse('resources/odwn/orbn_n-v-a.xml')
distr = Counter([form_el.get('form-cat')
                 for form_el in new_orbn.xpath('cdb_lu/form')])
print('distribution of pos', distr)
