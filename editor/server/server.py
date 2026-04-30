#!/usr/bin/env python3
"""
Collaborative ODWN LMF Editor — Server
Python 3.6+, no external dependencies.

Usage:
    python3 server.py                                          # port 8080, auto-find ODWN
    python3 server.py data/odwn_orbn_gwg-LMF_1.3.xml          # explicit file
    python3 server.py data/odwn_orbn_gwg-LMF_1.3.xml 9000     # explicit file + port
"""

import http.server, json, threading, time, os, sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────────────────────────────────────
# Global state (mutated only under lock)
# ─────────────────────────────────────────────────────────────────────

_lock = threading.RLock()

db = {
    'ready':        False,
    'loading_msg':  'Initializing…',
    'globalInfo':   {'label': ''},
    'lexicon':      {'language': '', 'languageCoding': '', 'label': '', 'owner': ''},
    'entries':      {},      # id → full entry dict
    'synsets':      {},      # id → full synset dict
    'entry_index':  [],      # [{id, lemma, partOfSpeech, isMWE}]  for sidebar
    'synset_index': [],      # [{id, gloss}]
    'changes':      [],      # change log (capped at 5000)
    'seq':          0,
    'modified':     False,
    'filepath':     None,
    'filename':     None,
    'active_users': {},      # username → last_seen timestamp
}

def _next_seq():
    db['seq'] += 1
    return db['seq']

def _record_change(op, item_type, item_id, data, user):
    """Append a change record; cap log at 5000 entries."""
    record = {'seq': _next_seq(), 'op': op, 'itemType': item_type,
              'id': item_id, 'data': data, 'user': user, 'ts': time.time()}
    db['changes'].append(record)
    if len(db['changes']) > 5000:
        db['changes'] = db['changes'][-5000:]
    db['modified'] = True
    return record['seq']

# ─────────────────────────────────────────────────────────────────────
# XML Parser  (matches JS data model exactly)
# ─────────────────────────────────────────────────────────────────────

def _g(el, attr, default=''):
    return el.get(attr, default) or default

def parse_entry(eEl):
    e = {
        'id': _g(eEl, 'id'), 'partOfSpeech': _g(eEl, 'partOfSpeech'),
        'formType': _g(eEl, 'formType'),
        'isMWE': False, 'lemma': '', 'lemmaMode': '',
        'mweForm': '', 'mweExpressionType': '',
        'wordForms': [], 'relatedForms': [],
        'morphology':  {'morphoType': '', 'comparisonType': '', 'declinable': '', 'separability': ''},
        'morphoSyntax': {'pronominalAndGrammaticalGender': '', 'adverbialUsage': '',
                         'position': '', 'reflexivity': '', 'auxiliaries': []},
        'syntacticBehaviour': {'valency': '', 'transitivity': '',
                                'complementations': [], 'subcatFrames': []},
        'senses': []
    }

    lEl = eEl.find('Lemma')
    if lEl is not None:
        e['lemma'] = _g(lEl, 'writtenForm')
        e['lemmaMode'] = _g(lEl, 'mode')

    mwEl = eEl.find('MultiwordExpression')
    if mwEl is not None:
        e['isMWE'] = True
        e['mweForm'] = _g(mwEl, 'writtenForm')
        e['mweExpressionType'] = _g(mwEl, 'expressionType')

    wfsEl = eEl.find('WordForms')
    if wfsEl is not None:
        for wf in wfsEl.findall('WordForm'):
            e['wordForms'].append({k: _g(wf, k) for k in
                ['writtenForm', 'grammaticalNumber', 'comparison', 'article', 'tense']})

    rfEl = eEl.find('RelatedForms')
    if rfEl is not None:
        for rf in rfEl.findall('RelatedForm'):
            e['relatedForms'].append({'writtenForm': _g(rf, 'writtenForm'), 'variantType': _g(rf, 'variantType')})

    mEl = eEl.find('Morphology')
    if mEl is not None:
        e['morphology'] = {k: _g(mEl, k) for k in ['morphoType', 'comparisonType', 'declinable', 'separability']}

    msEl = eEl.find('MorphoSyntax')
    if msEl is not None:
        e['morphoSyntax'] = {k: _g(msEl, k) for k in
            ['pronominalAndGrammaticalGender', 'adverbialUsage', 'position', 'reflexivity']}
        e['morphoSyntax']['auxiliaries'] = [_g(a, 'auxiliary') for a in msEl.findall('auxiliaries') if _g(a, 'auxiliary')]

    sbEl = eEl.find('SyntacticBehaviour')
    if sbEl is not None:
        comps  = [{'complement': _g(c, 'complement'), 'preposition': _g(c, 'preposition')} for c in sbEl.findall('Complementation')]
        frames = []
        for f in sbEl.findall('SyntacticSubcategorisationFrame'):
            args = [{'constituent': _g(a,'constituent'), 'function': _g(a,'function'),
                     'preposition': _g(a,'preposition'), 'complementizer': _g(a,'complementizer')}
                    for a in f.findall('syntacticArgument')]
            frames.append({'args': args})
        e['syntacticBehaviour'] = {'valency': _g(sbEl,'valency'), 'transitivity': _g(sbEl,'transitivity'),
                                    'complementations': comps, 'subcatFrames': frames}

    for sEl in eEl.findall('Sense'):
        sense = {k: _g(sEl, k) for k in ['id', 'senseId', 'definition', 'synset', 'provenance', 'annotator']}
        sense.update({'senseRelations': [], 'semanticsNoun': None, 'semanticsVerb': None,
                      'semanticsAdj': None, 'examples': [], 'sentiment': None,
                      'pragmatics': {'domains': [], 'chronology': '', 'connotation': '', 'geography': '', 'register': ''}})

        srEl = sEl.find('SenseRelations')
        if srEl is not None:
            sense['senseRelations'] = [{'relationType': _g(sg,'relationType'), 'targetSenseId': _g(sg,'targetSenseId')} for sg in srEl.findall('SenseGroup')]

        snEl = sEl.find('Semantics-noun')
        if snEl is not None:
            shifts = [{'semanticType': _g(sh,'semanticType')} for sh in snEl.findall('semanticShifts-noun')]
            sense['semanticsNoun'] = {k: _g(snEl,k) for k in ['reference','countability','semanticType','semanticSubType']}
            sense['semanticsNoun']['shifts'] = shifts

        svEl = sEl.find('Semantics-verb')
        if svEl is not None:
            types = [{'semanticType': _g(t,'semanticType'), 'semanticFeatureSet': _g(t,'semanticFeatureSet')} for t in svEl.findall('semanticTypes')]
            sense['semanticsVerb'] = {'semanticTypes': types}

        saEl = sEl.find('Semantics-adjective')
        if saEl is not None:
            shifts = [{'semanticType': _g(sh,'semanticType')} for sh in saEl.findall('semanticShifts-adjective')]
            sense['semanticsAdj'] = {'semanticType': _g(saEl,'semanticType'), 'shifts': shifts}

        pEl = sEl.find('Pragmatics')
        if pEl is not None:
            sense['pragmatics'] = {k: _g(pEl,k) for k in ['chronology','connotation','geography','register']}
            sense['pragmatics']['domains'] = [_g(d,'domain') for d in pEl.findall('Domains') if _g(d,'domain')]

        exsEl = sEl.find('SenseExamples')
        if exsEl is not None:
            for exEl in exsEl.findall('SenseExample'):
                tfEl = exEl.find('textualForm')
                sense['examples'].append({'id': _g(exEl,'id'),
                    'textualForm': _g(tfEl,'textualform') if tfEl is not None else '',
                    'phraseType':  _g(tfEl,'phraseType')  if tfEl is not None else ''})

        sentEl = sEl.find('Sentiment')
        if sentEl is not None:
            sense['sentiment'] = {'polarity': _g(sentEl,'polarity'), 'externalReference': _g(sentEl,'externalReference')}

        e['senses'].append(sense)
    return e


def parse_synset(ssEl):
    ss = {k: _g(ssEl,k) for k in ['id','ili','baseConcept']}
    ss['definitions'] = [{'gloss': _g(d,'gloss'), 'language': _g(d,'language'), 'provenance': _g(d,'provenance')} for d in ssEl.findall('Definitions/Definition')]
    ss['synsetRelations'] = [{'relType': _g(r,'relType'), 'target': _g(r,'target'), 'provenance': _g(r,'provenance')} for r in ssEl.findall('SynsetRelations/SynsetRelation')]
    ss['monolingualExternalRefs'] = [{'externalReference': _g(m,'externalReference'), 'externalSystem': _g(m,'externalSystem'), 'relType': _g(m,'relType')} for m in ssEl.findall('MonolingualExternalRefs/MonolingualExternalRef')]
    return ss


def load_xml(filepath):
    try:
        db['loading_msg'] = f'Reading {os.path.basename(filepath)}…'
        print(f'Loading {filepath}…')
        tree = ET.parse(filepath)
        root = tree.getroot()
        lex  = root.find('Lexicon')
        if lex is None:
            db['loading_msg'] = 'Error: no <Lexicon> element found'; return

        gi = root.find('GlobalInformation')
        global_info = {'label': _g(gi,'label') if gi is not None else ''}
        lexicon_meta = {k: _g(lex,k) for k in ['language','languageCoding','label','owner']}

        entries, entry_index = {}, []
        all_entries = lex.findall('LexicalEntry')
        total_e = len(all_entries)
        for i, eEl in enumerate(all_entries):
            if i % 5000 == 0:
                db['loading_msg'] = f'Parsing entries… {i:,} / {total_e:,}'
            e = parse_entry(eEl)
            entries[e['id']] = e
            entry_index.append({'id': e['id'], 'isMWE': e['isMWE'],
                                 'lemma': e['mweForm'] if e['isMWE'] else e['lemma'],
                                 'partOfSpeech': e['partOfSpeech']})

        synsets, synset_index = {}, []
        all_synsets = lex.findall('Synset')
        total_s = len(all_synsets)
        for i, ssEl in enumerate(all_synsets):
            if i % 10000 == 0:
                db['loading_msg'] = f'Parsing synsets… {i:,} / {total_s:,}'
            ss = parse_synset(ssEl)
            synsets[ss['id']] = ss
            gloss = ss['definitions'][0]['gloss'][:80] if ss['definitions'] else ''
            synset_index.append({'id': ss['id'], 'gloss': gloss})

        with _lock:
            db['globalInfo']   = global_info
            db['lexicon']      = lexicon_meta
            db['entries']      = entries
            db['synsets']      = synsets
            db['entry_index']  = entry_index
            db['synset_index'] = synset_index
            db['filepath']     = filepath
            db['filename']     = os.path.basename(filepath)
            db['ready']        = True
            db['loading_msg']  = ''
        print(f'Ready: {len(entries):,} entries, {len(synsets):,} synsets')
    except Exception as ex:
        db['loading_msg'] = f'Error: {ex}'
        print(f'Load error: {ex}')

# ─────────────────────────────────────────────────────────────────────
# XML Serializer
# ─────────────────────────────────────────────────────────────────────

def _xe(s):
    return str(s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def _at(n, v):
    return f' {n}="{_xe(v)}"' if v else ''

def serialize_xml():
    L = ["<?xml version='1.0' encoding='UTF-8'?>", '<LexicalResource>',
         f'  <GlobalInformation label="{_xe(db["globalInfo"]["label"])}"/>']
    lx = db['lexicon']
    L.append(f'  <Lexicon{_at("languageCoding",lx["languageCoding"])}{_at("label",lx["label"])}{_at("language",lx["language"])}{_at("owner",lx["owner"])}>')

    for idx in db['entry_index']:
        e = db['entries'].get(idx['id'])
        if e is None: continue
        L.append(f'    <LexicalEntry id="{_xe(e["id"])}"{_at("partOfSpeech",e["partOfSpeech"])}{_at("formType",e["formType"])}>')
        if e['isMWE']:
            L.append(f'      <MultiwordExpression writtenForm="{_xe(e["mweForm"])}"{_at("expressionType",e["mweExpressionType"])}"/>')
        else:
            L.append(f'      <Lemma writtenForm="{_xe(e["lemma"])}"{_at("mode",e["lemmaMode"])}"/>')
            wfs = e.get('wordForms', [])
            if wfs:
                L.append('      <WordForms>')
                for wf in wfs:
                    L.append(f'        <WordForm writtenForm="{_xe(wf["writtenForm"])}"{_at("grammaticalNumber",wf["grammaticalNumber"])}{_at("comparison",wf["comparison"])} article="{_xe(wf["article"])}"{_at("tense",wf["tense"])}"/>')
                L.append('      </WordForms>')
            else:
                L.append('      <WordForms/>')

        rfs = e.get('relatedForms', [])
        if rfs:
            L.append('      <RelatedForms>')
            for rf in rfs:
                L.append(f'        <RelatedForm writtenForm="{_xe(rf["writtenForm"])}"{_at("variantType",rf["variantType"])}"/>')
            L.append('      </RelatedForms>')

        m = e.get('morphology', {})
        L.append(f'      <Morphology{_at("morphoType",m.get("morphoType",""))}{_at("comparisonType",m.get("comparisonType",""))}{_at("declinable",m.get("declinable",""))}{_at("separability",m.get("separability",""))}"/>')

        ms = e.get('morphoSyntax', {})
        ms_a = (f'{_at("pronominalAndGrammaticalGender",ms.get("pronominalAndGrammaticalGender",""))}'
                f'{_at("adverbialUsage",ms.get("adverbialUsage",""))}{_at("position",ms.get("position",""))}'
                f'{_at("reflexivity",ms.get("reflexivity",""))}')
        auxs = ms.get('auxiliaries', [])
        if auxs:
            L.append(f'      <MorphoSyntax{ms_a}>')
            for a in auxs: L.append(f'        <auxiliaries auxiliary="{_xe(a)}"/>')
            L.append('      </MorphoSyntax>')
        else:
            L.append(f'      <MorphoSyntax{ms_a}/>')

        sb = e.get('syntacticBehaviour', {})
        sb_a = f'{_at("valency",sb.get("valency",""))}{_at("transitivity",sb.get("transitivity",""))}'
        comps  = sb.get('complementations', [])
        frames = sb.get('subcatFrames', [])
        if comps or frames:
            L.append(f'      <SyntacticBehaviour{sb_a}>')
            for c in comps:
                L.append(f'        <Complementation{_at("complement",c.get("complement",""))}{_at("preposition",c.get("preposition",""))}"/>')
            for f in frames:
                L.append('        <SyntacticSubcategorisationFrame>')
                for a in f.get('args', []):
                    L.append(f'          <syntacticArgument{_at("constituent",a.get("constituent",""))}{_at("function",a.get("function",""))}{_at("preposition",a.get("preposition",""))}{_at("complementizer",a.get("complementizer",""))}"/>')
                L.append('        </SyntacticSubcategorisationFrame>')
            L.append('      </SyntacticBehaviour>')
        else:
            L.append(f'      <SyntacticBehaviour{sb_a}/>')

        for sense in e.get('senses', []):
            s_a = (f' id="{_xe(sense["id"])}"{_at("senseId",sense.get("senseId",""))}'
                   f' definition="{_xe(sense.get("definition",""))}"{_at("synset",sense.get("synset",""))}'
                   f'{_at("provenance",sense.get("provenance",""))} annotator="{_xe(sense.get("annotator",""))}"')
            L.append(f'      <Sense{s_a}>')

            srs = sense.get('senseRelations', [])
            if srs:
                L.append('        <SenseRelations>')
                for sr in srs: L.append(f'          <SenseGroup relationType="{_xe(sr["relationType"])}" targetSenseId="{_xe(sr["targetSenseId"])}"/>')
                L.append('        </SenseRelations>')
            else:
                L.append('        <SenseRelations/>')

            sn = sense.get('semanticsNoun')
            if sn is not None:
                sn_a = f'{_at("reference",sn.get("reference",""))}{_at("countability",sn.get("countability",""))}{_at("semanticType",sn.get("semanticType",""))}{_at("semanticSubType",sn.get("semanticSubType",""))}'
                shifts = sn.get('shifts', [])
                if shifts:
                    L.append(f'        <Semantics-noun{sn_a}>')
                    for sh in shifts: L.append(f'          <semanticShifts-noun{_at("semanticType",sh.get("semanticType",""))}"/>')
                    L.append('        </Semantics-noun>')
                else:
                    L.append(f'        <Semantics-noun{sn_a}/>')

            sv = sense.get('semanticsVerb')
            if sv is not None:
                types = sv.get('semanticTypes', [])
                if types:
                    L.append('        <Semantics-verb>')
                    for t in types: L.append(f'          <semanticTypes{_at("semanticType",t.get("semanticType",""))}{_at("semanticFeatureSet",t.get("semanticFeatureSet",""))}"/>')
                    L.append('        </Semantics-verb>')
                else:
                    L.append('        <Semantics-verb/>')

            sa = sense.get('semanticsAdj')
            if sa is not None:
                sa_a = _at('semanticType', sa.get('semanticType',''))
                shifts = sa.get('shifts', [])
                if shifts:
                    L.append(f'        <Semantics-adjective{sa_a}>')
                    for sh in shifts: L.append(f'          <semanticShifts-adjective{_at("semanticType",sh.get("semanticType",""))}"/>')
                    L.append('        </Semantics-adjective>')
                else:
                    L.append(f'        <Semantics-adjective{sa_a}/>')

            p = sense.get('pragmatics', {})
            p_a = f'{_at("chronology",p.get("chronology",""))}{_at("connotation",p.get("connotation",""))}{_at("geography",p.get("geography",""))}{_at("register",p.get("register",""))}'
            doms = p.get('domains', [])
            if doms:
                L.append(f'        <Pragmatics{p_a}>')
                for d in doms: L.append(f'          <Domains domain="{_xe(d)}"/>')
                L.append('        </Pragmatics>')
            else:
                L.append(f'        <Pragmatics{p_a}/>')

            exs = sense.get('examples', [])
            if exs:
                L.append('        <SenseExamples>')
                for ex in exs:
                    L.append(f'          <SenseExample id="{_xe(ex["id"])}">')
                    L.append(f'            <textualForm textualform="{_xe(ex["textualForm"])}"{_at("phraseType",ex.get("phraseType",""))}"/>')
                    L.append('            <Semantics_ex/><Pragmatics/>')
                    L.append('          </SenseExample>')
                L.append('        </SenseExamples>')

            sent = sense.get('sentiment')
            if sent is not None:
                L.append(f'        <Sentiment polarity="{_xe(sent["polarity"])}" externalReference="{_xe(sent["externalReference"])}"/>')

            L.append('      </Sense>')
        L.append('    </LexicalEntry>')

    for ss_idx in db['synset_index']:
        ss = db['synsets'].get(ss_idx['id'])
        if ss is None: continue
        ss_a = f' id="{_xe(ss["id"])}"{_at("ili",ss.get("ili",""))}{_at("baseConcept",ss.get("baseConcept",""))}'
        defs = ss.get('definitions', [])
        rels = ss.get('synsetRelations', [])
        mers = ss.get('monolingualExternalRefs', [])
        if not (defs or rels or mers):
            L.append(f'    <Synset{ss_a}/>'); continue
        L.append(f'    <Synset{ss_a}>')
        if defs:
            L.append('      <Definitions>')
            for d in defs: L.append(f'        <Definition gloss="{_xe(d["gloss"])}"{_at("language",d.get("language",""))}{_at("provenance",d.get("provenance",""))}"/>')
            L.append('      </Definitions>')
        if rels:
            L.append('      <SynsetRelations>')
            for r in rels: L.append(f'        <SynsetRelation{_at("provenance",r.get("provenance",""))} relType="{_xe(r["relType"])}" target="{_xe(r["target"])}"/>')
            L.append('      </SynsetRelations>')
        if mers:
            L.append('      <MonolingualExternalRefs>')
            for m in mers: L.append(f'        <MonolingualExternalRef externalReference="{_xe(m["externalReference"])}" externalSystem="{_xe(m["externalSystem"])}"{_at("relType",m.get("relType",""))}"/>')
            L.append('      </MonolingualExternalRefs>')
        L.append('    </Synset>')

    L.append('  </Lexicon>')
    L.append('</LexicalResource>')
    return '\n'.join(L)

# ─────────────────────────────────────────────────────────────────────
# HTTP Request Handler
# ─────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress per-request logs (noisy with polling)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        n = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        path, qs = p.path, parse_qs(p.query)

        if path == '/api/status':
            now = time.time()
            with _lock:
                active = [u for u, t in db['active_users'].items() if now - t < 60]
                db['active_users'] = {u: t for u, t in db['active_users'].items() if now - t < 120}
            self._json({'ready': db['ready'], 'loadingMsg': db['loading_msg'],
                        'filename': db['filename'], 'seq': db['seq'],
                        'users': len(active), 'userList': active,
                        'entriesCount': len(db['entries']), 'synsetsCount': len(db['synsets']),
                        'modified': db['modified']})

        elif path == '/api/index':
            if not db['ready']:
                self._json({'error': 'loading', 'msg': db['loading_msg']}, 503); return
            with _lock:
                self._json({'globalInfo': db['globalInfo'], 'lexicon': db['lexicon'],
                            'entryIndex': db['entry_index'], 'synsetIndex': db['synset_index']})

        elif path.startswith('/api/entry/'):
            eid = path[len('/api/entry/'):]
            with _lock:
                e = db['entries'].get(eid)
            self._json(e) if e else self._json({'error': 'not found'}, 404)

        elif path.startswith('/api/synset/'):
            sid = path[len('/api/synset/'):]
            with _lock:
                ss = db['synsets'].get(sid)
            self._json(ss) if ss else self._json({'error': 'not found'}, 404)

        elif path == '/api/changes':
            since = int(qs.get('since', ['0'])[0])
            with _lock:
                relevant = [c for c in db['changes'] if c['seq'] > since]
            self._json(relevant)

        else:
            self._serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == '/api/update':
            self._handle_update(body)
        elif path == '/api/save':
            self._handle_save()
        elif path == '/api/heartbeat':
            user = str(body.get('user', self.client_address[0]))[:64]
            with _lock:
                db['active_users'][user] = time.time()
                count = sum(1 for t in db['active_users'].values() if time.time() - t < 60)
            self._json({'ok': True, 'users': count})
        elif path == '/api/lexicon':
            with _lock:
                db['globalInfo'] = body.get('globalInfo', db['globalInfo'])
                db['lexicon']    = body.get('lexicon', db['lexicon'])
                seq = _record_change('update', 'lexicon', 'lexicon', body, str(body.get('user', '')))
            self._json({'ok': True, 'seq': seq})
        else:
            self._json({'error': 'Not found'}, 404)

    def _handle_update(self, body):
        op        = body.get('op', 'update')   # 'update' | 'add' | 'delete'
        item_type = body.get('itemType', 'entry')
        data      = body.get('data', {})
        user      = str(body.get('user', self.client_address[0]))[:64]
        item_id   = data.get('id', '') if data else body.get('id', '')

        with _lock:
            if item_type == 'entry':
                if op == 'delete':
                    db['entries'].pop(item_id, None)
                    db['entry_index'] = [x for x in db['entry_index'] if x['id'] != item_id]
                elif op == 'add':
                    db['entries'][item_id] = data
                    db['entry_index'].insert(0, {'id': data['id'], 'isMWE': data.get('isMWE', False),
                        'lemma': data.get('mweForm','') if data.get('isMWE') else data.get('lemma',''),
                        'partOfSpeech': data.get('partOfSpeech','')})
                else:  # update
                    db['entries'][item_id] = data
                    for idx in db['entry_index']:
                        if idx['id'] == item_id:
                            idx['lemma'] = data.get('mweForm','') if data.get('isMWE') else data.get('lemma','')
                            idx['partOfSpeech'] = data.get('partOfSpeech','')
            else:  # synset
                if op == 'delete':
                    db['synsets'].pop(item_id, None)
                    db['synset_index'] = [x for x in db['synset_index'] if x['id'] != item_id]
                elif op == 'add':
                    db['synsets'][item_id] = data
                    gloss = data['definitions'][0]['gloss'][:80] if data.get('definitions') else ''
                    db['synset_index'].insert(0, {'id': data['id'], 'gloss': gloss})
                else:
                    db['synsets'][item_id] = data
                    for idx in db['synset_index']:
                        if idx['id'] == item_id:
                            idx['gloss'] = data['definitions'][0]['gloss'][:80] if data.get('definitions') else ''

            seq = _record_change(op, item_type, item_id, data if op != 'delete' else None, user)

        self._json({'ok': True, 'seq': seq})

    def _handle_save(self):
        if not db['ready']:
            self._json({'error': 'not ready'}, 503); return
        try:
            with _lock:
                xml = serialize_xml()
                filepath = db['filepath']
                db['modified'] = False
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(xml)
                print(f'Saved to {filepath}')
                self._json({'ok': True, 'filename': os.path.basename(filepath)})
            else:
                # No filepath — send XML as download trigger
                self._json({'ok': True, 'filename': 'lexicon.xml', 'xml': xml[:200] + '…'})
        except Exception as ex:
            self._json({'error': str(ex)}, 500)

    def _serve_static(self, path):
        if path in ('/', '/index.html', ''):
            path = '/index.html'
        filepath = os.path.join(BASE_DIR, path.lstrip('/'))
        # Safety: stay within BASE_DIR
        if not os.path.realpath(filepath).startswith(BASE_DIR):
            self.send_response(403); self.end_headers(); return
        if os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1]
            mime = {'html': 'text/html', 'js': 'application/javascript', 'css': 'text/css',
                    'xml': 'application/xml', 'json': 'application/json'}.get(ext.lstrip('.'), 'application/octet-stream')
            with open(filepath, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()

# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    args = sys.argv[1:]

    # Find XML file
    xml_file = None
    port = 8080
    for arg in args:
        if arg.isdigit():
            port = int(arg)
        elif arg.endswith('.xml') or arg.endswith('.xml.gz'):
            xml_file = arg

    if xml_file is None:
        # Auto-discover
        candidates = [
            'data/odwn_orbn_gwg-LMF_1.3.xml',
            'data/odwn_orbn_gwg-LMF_1.2.xml',
        ]
        for c in candidates:
            if os.path.isfile(c):
                xml_file = c
                break

    if xml_file:
        t = threading.Thread(target=load_xml, args=(xml_file,), daemon=True)
        t.start()
    else:
        db['ready']       = True
        db['loading_msg'] = ''
        print('No XML file found. Starting with empty lexicon.')

    server = http.server.ThreadingHTTPServer(('', port), Handler)
    print(f'ODWN LMF Editor  →  http://localhost:{port}')
    if xml_file:
        print(f'Loading: {xml_file}  (editor available immediately, data loads in background)')
    print('Press Ctrl+C to stop.\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
