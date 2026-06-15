#!/usr/bin/env python3
"""
Collaborative ODWN LMF Editor — SQLite backend with row-level locking and user auth.
Python 3.6+, no external dependencies.

Usage:
    python3 server.py                                         # port 8080, auto-find ODWN
    python3 server.py data/odwn.xml                           # import XML → data/odwn.db
    python3 server.py data/odwn.db                            # use existing database
    python3 server.py data/odwn.xml 9000                      # explicit file + port

Authentication:
    Users are loaded from a JSON config file (default: users.json next to server.py).
    Pass a different path as a command-line argument ending in .json.
    Passwords are hashed with PBKDF2-SHA256 and stored in the database.

Locking:
    A lock is acquired when a user opens an entry or synset for editing.
    The lock expires after LOCK_TTL seconds of inactivity (no auto-saves).
    Other users see locked items as read-only until the lock expires or is released.
"""

import http.server, json, threading, time, os, sys, sqlite3, hashlib, secrets, re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

LOCK_TTL    = 60          # seconds before an idle editing lock expires
SESSION_TTL = 8 * 3600    # seconds a login session stays valid (8 hours)

# ─────────────────────────────────────────────────────────────────────
# User accounts — loaded from a JSON config file at startup.
# ─────────────────────────────────────────────────────────────────────

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
USERS = {}   # populated by load_users_file() in main()

_USERS_TEMPLATE = '''\
{
  "admin": "changeme"
}
'''

def load_users_file(path: str) -> dict:
    """Read username→password pairs from a JSON file. Creates a template if absent."""
    if not os.path.isfile(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(_USERS_TEMPLATE)
            print(f'Created sample users file: {path}')
            print('Edit it to set real usernames and passwords, then restart.\n')
        except OSError as e:
            print(f'Warning: could not create {path}: {e}')
        return {'admin': 'changeme'}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data:
            print(f'Warning: {path} is empty or not a JSON object — no users loaded.')
            return {}
        # Validate: all values must be non-empty strings
        users = {}
        for k, v in data.items():
            k, v = str(k).strip(), str(v)
            if k and v:
                users[k] = v
            else:
                print(f'Warning: skipping invalid entry in {path}: {k!r}')
        print(f'Loaded {len(users)} user(s) from {path}')
        return users
    except (json.JSONDecodeError, OSError) as e:
        print(f'Error reading {path}: {e}')
        sys.exit(1)

# ─────────────────────────────────────────────────────────────────────
# Database — per-thread connections in WAL mode
# ─────────────────────────────────────────────────────────────────────

DB_PATH = None   # set in main()

_tls = threading.local()

def _con():
    """Return (creating if needed) a per-thread SQLite connection."""
    if not hasattr(_tls, 'c') or _tls.c is None:
        # timeout=20: wait up to 20s if another writer holds the DB before raising
        c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('PRAGMA synchronous=NORMAL')
        _tls.c = c
    return _tls.c

# Serialises all write operations within this process so no two threads
# ever contend on the same rows simultaneously.
_write_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS users (
    username   TEXT PRIMARY KEY,
    pass_hash  TEXT NOT NULL,
    salt       TEXT NOT NULL,
    created_at REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sess_exp ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS entries (
    id                 TEXT PRIMARY KEY,
    data               TEXT NOT NULL,
    lemma              TEXT NOT NULL DEFAULT '',
    mwe_form           TEXT NOT NULL DEFAULT '',
    part_of_speech     TEXT NOT NULL DEFAULT '',
    is_mwe             INTEGER NOT NULL DEFAULT 0,
    updated_at         REAL NOT NULL DEFAULT 0,
    updated_by         TEXT NOT NULL DEFAULT '',
    has_unlinked_sense INTEGER DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS synsets (
    id         TEXT PRIMARY KEY,
    data       TEXT NOT NULL,
    gloss      TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL DEFAULT 0,
    updated_by TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS locks (
    item_type  TEXT NOT NULL,
    item_id    TEXT NOT NULL,
    user       TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY (item_type, item_id)
);
CREATE TABLE IF NOT EXISTS changelog (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    op         TEXT NOT NULL,
    item_type  TEXT NOT NULL,
    item_id    TEXT NOT NULL,
    data       TEXT,
    user       TEXT NOT NULL DEFAULT '',
    ts         REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_cl_seq ON changelog(seq);
CREATE TABLE IF NOT EXISTS en_synonyms (
    synset_id TEXT PRIMARY KEY,
    words     TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS synset_entry_index (
    synset_id TEXT NOT NULL,
    entry_id  TEXT NOT NULL,
    PRIMARY KEY (synset_id, entry_id)
);
CREATE INDEX IF NOT EXISTS idx_sei_synset ON synset_entry_index(synset_id);
"""

def _init_schema():
    c = _con()
    c.executescript(_SCHEMA)
    # Migrate: add has_unlinked_sense column to existing databases
    cols = {r[1] for r in c.execute("PRAGMA table_info(entries)").fetchall()}
    if 'has_unlinked_sense' not in cols:
        c.execute("ALTER TABLE entries ADD COLUMN has_unlinked_sense INTEGER DEFAULT NULL")
    c.commit()

# ─────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────

def _hash_pw(password: str, salt_hex: str = None):
    """Hash a password with PBKDF2-SHA256. Returns (hash_hex, salt_hex)."""
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    key  = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200_000)
    return key.hex(), salt.hex()

def _verify_pw(password: str, stored_hash: str, salt_hex: str) -> bool:
    key, _ = _hash_pw(password, salt_hex)
    return key == stored_hash

def _sync_users():
    """Insert/update users from the USERS config dict into the database."""
    c = _con()
    for username, password in USERS.items():
        row = c.execute('SELECT pass_hash, salt FROM users WHERE username=?', (username,)).fetchone()
        if row is None:
            h, s = _hash_pw(password)
            c.execute('INSERT INTO users (username,pass_hash,salt,created_at) VALUES (?,?,?,?)',
                      (username, h, s, time.time()))
        else:
            # Re-hash if the stored hash doesn't match (password changed in config)
            if not _verify_pw(password, row['pass_hash'], row['salt']):
                h, s = _hash_pw(password)
                c.execute('UPDATE users SET pass_hash=?, salt=? WHERE username=?', (h, s, username))
    # Remove users no longer in config
    c.execute('DELETE FROM users WHERE username NOT IN (%s)' % ','.join('?' * len(USERS)),
              list(USERS.keys()))
    c.commit()

def _do_login(username: str, password: str):
    """Validate credentials and create a session. Returns token or None."""
    c = _con()
    row = c.execute('SELECT pass_hash, salt FROM users WHERE username=?', (username,)).fetchone()
    if not row or not _verify_pw(password, row['pass_hash'], row['salt']):
        return None
    token = secrets.token_hex(32)
    with _write_lock:
        c = _con()
        c.execute('INSERT INTO sessions (token,username,expires_at,created_at) VALUES (?,?,?,?)',
                  (token, username, time.time() + SESSION_TTL, time.time()))
        c.commit()
    return token

def _validate_session(token: str):
    """Return username for a valid, non-expired token, else None."""
    if not token:
        return None
    with _write_lock:
        c = _con()
        c.execute('DELETE FROM sessions WHERE expires_at<?', (time.time(),))
        c.commit()
        row = c.execute('SELECT username FROM sessions WHERE token=?', (token,)).fetchone()
    return row['username'] if row else None

def _do_logout(token: str):
    with _write_lock:
        c = _con()
        c.execute('DELETE FROM sessions WHERE token=?', (token,))
        c.commit()

# ─────────────────────────────────────────────────────────────────────
# In-memory state (indices + metadata + presence)  — mutated under _slock
# ─────────────────────────────────────────────────────────────────────

_slock = threading.RLock()
_st = {
    'ready':        False,
    'loading_msg':  'Initializing…',
    'modified':     False,
    'filepath':     None,
    'filename':     None,
    'active_users': {},    # user → last_seen timestamp
    'entry_index':  [],    # [{id, lemma, partOfSpeech, isMWE, mweForm}]
    'synset_index': [],    # [{id, gloss}]
    'globalInfo':   {'label': ''},
    'lexicon':      {'language': '', 'languageCoding': '', 'label': '', 'owner': ''},
}

# ─────────────────────────────────────────────────────────────────────
# Lock helpers
# ─────────────────────────────────────────────────────────────────────

def try_acquire_lock(item_type, item_id, user):
    """
    Atomically try to acquire (or refresh) a lock.
    Returns (ok: bool, lock_dict).
    ok=True  → lock is now held by `user`
    ok=False → held by someone else; lock_dict describes who holds it
    """
    now = time.time()
    exp = now + LOCK_TTL
    with _write_lock:          # serialise within this process; no BEGIN EXCLUSIVE needed
        c = _con()
        c.execute('DELETE FROM locks WHERE item_type=? AND item_id=? AND expires_at<?',
                  (item_type, item_id, now))
        row = c.execute('SELECT * FROM locks WHERE item_type=? AND item_id=?',
                        (item_type, item_id)).fetchone()
        if row is None:
            c.execute('INSERT INTO locks (item_type,item_id,user,expires_at) VALUES (?,?,?,?)',
                      (item_type, item_id, user, exp))
            c.commit()
            return True, {'item_type': item_type, 'item_id': item_id, 'user': user, 'expires_at': exp}
        row = dict(row)
        if row['user'] == user:
            c.execute('UPDATE locks SET expires_at=? WHERE item_type=? AND item_id=?',
                      (exp, item_type, item_id))
            c.commit()
            row['expires_at'] = exp
            return True, row
        c.commit()             # commit the expiry DELETE so it isn't rolled back
        return False, row

def release_lock(item_type, item_id, user):
    with _write_lock:
        c = _con()
        c.execute('DELETE FROM locks WHERE item_type=? AND item_id=? AND user=?',
                  (item_type, item_id, user))
        c.commit()

def get_lock(item_type, item_id):
    """Return the current non-expired lock row, or None."""
    now = time.time()
    with _write_lock:
        c = _con()
        c.execute('DELETE FROM locks WHERE item_type=? AND item_id=? AND expires_at<?',
                  (item_type, item_id, now))
        row = c.execute('SELECT * FROM locks WHERE item_type=? AND item_id=?',
                        (item_type, item_id)).fetchone()
        c.commit()
        return dict(row) if row else None

def all_locks():
    """Return all non-expired locks."""
    now = time.time()
    with _write_lock:
        c = _con()
        c.execute('DELETE FROM locks WHERE expires_at<?', (now,))
        c.commit()
        return [dict(r) for r in c.execute('SELECT * FROM locks').fetchall()]

# ─────────────────────────────────────────────────────────────────────
# Change log
# ─────────────────────────────────────────────────────────────────────

def _record_change(op, item_type, item_id, data, user):
    payload = json.dumps(data, ensure_ascii=False) if data is not None else None
    with _write_lock:
        c = _con()
        c.execute(
            'INSERT INTO changelog (op,item_type,item_id,data,user,ts) VALUES (?,?,?,?,?,?)',
            (op, item_type, item_id, payload, user, time.time())
        )
        c.commit()
        return c.execute('SELECT last_insert_rowid()').fetchone()[0]

def _changes_since(seq):
    rows = _con().execute(
        'SELECT seq,op,item_type,item_id,data,user,ts FROM changelog WHERE seq>? ORDER BY seq LIMIT 500',
        (seq,)
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            'seq':      r['seq'],
            'op':       r['op'],
            'itemType': r['item_type'],
            'id':       r['item_id'],
            'data':     json.loads(r['data']) if r['data'] else None,
            'user':     r['user'],
            'ts':       r['ts'],
        })
    return out

def _current_seq():
    row = _con().execute('SELECT MAX(seq) FROM changelog').fetchone()
    return row[0] or 0

# ─────────────────────────────────────────────────────────────────────
# Item CRUD
# ─────────────────────────────────────────────────────────────────────

def get_entry(eid):
    row = _con().execute('SELECT data FROM entries WHERE id=?', (eid,)).fetchone()
    return json.loads(row['data']) if row else None

def get_synset(sid):
    row = _con().execute('SELECT data FROM synsets WHERE id=?', (sid,)).fetchone()
    return json.loads(row['data']) if row else None

def upsert_entry(data, user):
    lemma  = data.get('mweForm', '') if data.get('isMWE') else data.get('lemma', '')
    is_mwe = 1 if data.get('isMWE') else 0
    has_unlinked = 1 if any(not s.get('synset', '') for s in data.get('senses', [])) else 0
    ts = time.time()
    changes = data.get('_changes', [])
    if not changes or changes[-1].get('user') != user or ts - changes[-1].get('ts', 0) > 300:
        changes.append({'user': user, 'ts': ts})
    data['_changes'] = changes
    with _write_lock:
        c = _con()
        c.execute(
            'INSERT INTO entries (id,data,lemma,mwe_form,part_of_speech,is_mwe,updated_at,updated_by,has_unlinked_sense) VALUES (?,?,?,?,?,?,?,?,?) '
            'ON CONFLICT(id) DO UPDATE SET data=excluded.data,lemma=excluded.lemma,mwe_form=excluded.mwe_form,'
            'part_of_speech=excluded.part_of_speech,is_mwe=excluded.is_mwe,updated_at=excluded.updated_at,'
            'updated_by=excluded.updated_by,has_unlinked_sense=excluded.has_unlinked_sense',
            (data['id'], json.dumps(data, ensure_ascii=False),
             data.get('lemma', ''), data.get('mweForm', ''),
             data.get('partOfSpeech', ''), is_mwe, ts, user, has_unlinked)
        )
        c.execute('DELETE FROM synset_entry_index WHERE entry_id=?', (data['id'],))
        for sense in data.get('senses', []):
            ss_ref = sense.get('synset', '')
            if ss_ref:
                c.execute('INSERT OR IGNORE INTO synset_entry_index (synset_id, entry_id) VALUES (?,?)',
                          (ss_ref, data['id']))
        c.commit()

def upsert_synset(data, user):
    gloss = data['definitions'][0]['gloss'][:80] if data.get('definitions') else ''
    ts = time.time()
    changes = data.get('_changes', [])
    if not changes or changes[-1].get('user') != user or ts - changes[-1].get('ts', 0) > 300:
        changes.append({'user': user, 'ts': ts})
    data['_changes'] = changes
    with _write_lock:
        c = _con()
        c.execute(
            'INSERT INTO synsets (id,data,gloss,updated_at,updated_by) VALUES (?,?,?,?,?) '
            'ON CONFLICT(id) DO UPDATE SET data=excluded.data,gloss=excluded.gloss,updated_at=excluded.updated_at,updated_by=excluded.updated_by',
            (data['id'], json.dumps(data, ensure_ascii=False), gloss, ts, user)
        )
        c.commit()

def delete_entry(eid):
    with _write_lock:
        c = _con()
        c.execute('DELETE FROM entries WHERE id=?', (eid,))
        c.execute('DELETE FROM locks WHERE item_type=? AND item_id=?', ('entry', eid))
        c.execute('DELETE FROM synset_entry_index WHERE entry_id=?', (eid,))
        c.commit()

def delete_synset(sid):
    with _write_lock:
        c = _con()
        c.execute('DELETE FROM synsets WHERE id=?', (sid,))
        c.execute('DELETE FROM locks WHERE item_type=? AND item_id=?', ('synset', sid))
        c.commit()

def _refresh_synset_nl_flags(synset_ids):
    """Update hasDutchSynonyms on in-memory synset_index stubs for the given synset IDs."""
    if not synset_ids:
        return
    id_set = set(synset_ids)
    c = _con()
    linked = {r[0] for r in c.execute(
        'SELECT DISTINCT synset_id FROM synset_entry_index WHERE synset_id IN ({})'.format(
            ','.join('?' * len(id_set))), list(id_set)).fetchall()}
    with _slock:
        for stub in _st['synset_index']:
            if stub['id'] in id_set:
                stub['hasDutchSynonyms'] = stub['id'] in linked

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

# ─────────────────────────────────────────────────────────────────────
# XML Import
# ─────────────────────────────────────────────────────────────────────

def load_xml(filepath):
    """Parse XML and populate the SQLite database, then rebuild in-memory indices."""
    try:
        with _slock:
            _st['loading_msg'] = f'Reading {os.path.basename(filepath)}…'
        print(f'Loading {filepath}…', flush=True)
        with open(filepath, encoding='utf-8', errors='replace') as _f:
            _xml_text = _f.read()
        # Fix spurious " before /> generated by older versions of this serializer.
        # Pattern 1: attr="val""/>  →  attr="val"/>  (double-quote before self-close)
        # Pattern 2: <TagName"/>   →  <TagName/>     (bare " after element name, no attrs)
        if '"/>' in _xml_text:
            _xml_text = _xml_text.replace('""/>', '"/>')  # step 1: ""/> → "/> (double-quote before />)
            _xml_text = re.sub(r'(<[A-Za-z][A-Za-z0-9_:.-]*)"(/>)', r'\1\2', _xml_text)  # step 2: <Tag"/> → <Tag/>
        root = ET.fromstring(_xml_text)
        del _xml_text
        lex  = root.find('Lexicon')
        if lex is None:
            with _slock: _st['loading_msg'] = 'Error: no <Lexicon> element found'
            return

        gi = root.find('GlobalInformation')
        global_info  = {'label': _g(gi,'label') if gi is not None else ''}
        lexicon_meta = {k: _g(lex,k) for k in ['language','languageCoding','label','owner']}

        _init_schema()

        c = _con()
        c.execute('INSERT OR REPLACE INTO meta VALUES ("globalInfo",?)', (json.dumps(global_info),))
        c.execute('INSERT OR REPLACE INTO meta VALUES ("lexicon",?)',     (json.dumps(lexicon_meta),))
        c.execute('INSERT OR REPLACE INTO meta VALUES ("filename",?)',    (os.path.basename(filepath),))
        c.execute('INSERT OR REPLACE INTO meta VALUES ("filepath",?)',    (filepath,))
        c.commit()

        all_entries = lex.findall('LexicalEntry')
        all_synsets = lex.findall('Synset')
        total_e, total_s = len(all_entries), len(all_synsets)

        entry_index, synset_index = [], []

        BATCH = 2000
        batch_e, batch_sei = [], []
        for i, eEl in enumerate(all_entries):
            if i % 5000 == 0:
                with _slock: _st['loading_msg'] = f'Parsing entries… {i:,} / {total_e:,}'
            e = parse_entry(eEl)
            lemma  = e['mweForm'] if e['isMWE'] else e['lemma']
            is_mwe = 1 if e['isMWE'] else 0
            has_unlinked = 1 if any(not s.get('synset','') for s in e.get('senses',[])) else 0
            batch_e.append((e['id'], json.dumps(e, ensure_ascii=False),
                            e.get('lemma',''), e.get('mweForm',''),
                            e.get('partOfSpeech',''), is_mwe, time.time(), 'import', has_unlinked))
            for sense in e.get('senses', []):
                ss_ref = sense.get('synset', '')
                if ss_ref:
                    batch_sei.append((ss_ref, e['id']))
            entry_index.append({'id': e['id'], 'isMWE': e['isMWE'],
                                 'lemma': lemma, 'partOfSpeech': e['partOfSpeech'],
                                 'mweForm': e.get('mweForm',''),
                                 'hasMissingSynset': bool(has_unlinked)})
            if len(batch_e) >= BATCH:
                c.executemany(
                    'INSERT OR REPLACE INTO entries (id,data,lemma,mwe_form,part_of_speech,is_mwe,updated_at,updated_by,has_unlinked_sense) VALUES (?,?,?,?,?,?,?,?,?)',
                    batch_e)
                c.commit()
                batch_e = []
        if batch_e:
            c.executemany(
                'INSERT OR REPLACE INTO entries (id,data,lemma,mwe_form,part_of_speech,is_mwe,updated_at,updated_by,has_unlinked_sense) VALUES (?,?,?,?,?,?,?,?,?)',
                batch_e)
            c.commit()
        if batch_sei:
            for i in range(0, len(batch_sei), BATCH):
                c.executemany('INSERT OR IGNORE INTO synset_entry_index (synset_id, entry_id) VALUES (?,?)',
                              batch_sei[i:i + BATCH])
            c.commit()

        with _slock: _st['loading_msg'] = f'Parsing synsets… 0 / {total_s:,}'

        batch_s = []
        for i, ssEl in enumerate(all_synsets):
            if i % 10000 == 0:
                with _slock: _st['loading_msg'] = f'Parsing synsets… {i:,} / {total_s:,}'
            ss = parse_synset(ssEl)
            gloss = ss['definitions'][0]['gloss'][:80] if ss['definitions'] else ''
            batch_s.append((ss['id'], json.dumps(ss, ensure_ascii=False), gloss, time.time(), 'import'))
            synset_index.append({'id': ss['id'], 'gloss': gloss})
            if len(batch_s) >= BATCH:
                c.executemany(
                    'INSERT OR REPLACE INTO synsets (id,data,gloss,updated_at,updated_by) VALUES (?,?,?,?,?)',
                    batch_s)
                c.commit()
                batch_s = []
        if batch_s:
            c.executemany(
                'INSERT OR REPLACE INTO synsets (id,data,gloss,updated_at,updated_by) VALUES (?,?,?,?,?)',
                batch_s)
            c.commit()

        # Annotate synset_index with hasDutchSynonyms using the synset_entry_index
        linked_ss = {r[0] for r in c.execute('SELECT DISTINCT synset_id FROM synset_entry_index').fetchall()}
        for stub in synset_index:
            stub['hasDutchSynonyms'] = stub['id'] in linked_ss

        with _slock:
            _st['globalInfo']   = global_info
            _st['lexicon']      = lexicon_meta
            _st['entry_index']  = entry_index
            _st['synset_index'] = synset_index
            _st['filepath']     = filepath
            _st['filename']     = os.path.basename(filepath)
            _st['ready']        = True
            _st['loading_msg']  = ''
        print(f'Ready: {len(entry_index):,} entries, {len(synset_index):,} synsets', flush=True)
        _load_en_synonyms()
    except Exception as ex:
        with _slock: _st['loading_msg'] = f'Error: {ex}'
        print(f'Load error: {ex}', flush=True)
        import traceback; traceback.print_exc()


def load_from_db():
    """Rebuild in-memory indices from an existing database (subsequent server runs)."""
    try:
        with _slock: _st['loading_msg'] = 'Loading from database…'
        print('Loading from existing database…', flush=True)
        _init_schema()
        c = _con()

        meta = {r['key']: r['value'] for r in c.execute('SELECT key,value FROM meta').fetchall()}
        global_info  = json.loads(meta.get('globalInfo', '{"label":""}'))
        lexicon_meta = json.loads(meta.get('lexicon', '{"language":"","languageCoding":"","label":"","owner":""}'))
        filepath     = meta.get('filepath', '')
        filename     = meta.get('filename', '')

        rows_e = c.execute('SELECT id, lemma, mwe_form, part_of_speech, is_mwe, has_unlinked_sense FROM entries').fetchall()
        entry_index = [{'id': r['id'],
                        'lemma':            r['mwe_form'] if r['is_mwe'] else r['lemma'],
                        'isMWE':            bool(r['is_mwe']),
                        'partOfSpeech':     r['part_of_speech'],
                        'mweForm':          r['mwe_form'],
                        'hasMissingSynset': bool(r['has_unlinked_sense'])} for r in rows_e]

        rows_s = c.execute('SELECT id, gloss FROM synsets').fetchall()
        synset_index = [{'id': r['id'], 'gloss': r['gloss']} for r in rows_s]

        # Backfill synset→entry index if missing (first run after upgrade)
        if c.execute('SELECT COUNT(*) FROM synset_entry_index').fetchone()[0] == 0:
            print('Building synset→entry index…', flush=True)
            batch_sei = []
            for row in c.execute('SELECT id, data FROM entries').fetchall():
                entry = json.loads(row['data'])
                for sense in entry.get('senses', []):
                    ss_ref = sense.get('synset', '')
                    if ss_ref:
                        batch_sei.append((ss_ref, row['id']))
            BATCH = 5000
            for i in range(0, len(batch_sei), BATCH):
                c.executemany('INSERT OR IGNORE INTO synset_entry_index (synset_id, entry_id) VALUES (?,?)',
                              batch_sei[i:i + BATCH])
            c.commit()
            print(f'Synset→entry index built: {len(batch_sei):,} links', flush=True)

        # Backfill has_unlinked_sense if missing (first run after column migration)
        if c.execute('SELECT COUNT(*) FROM entries WHERE has_unlinked_sense IS NULL').fetchone()[0] > 0:
            print('Backfilling has_unlinked_sense…', flush=True)
            updates = []
            for row in c.execute('SELECT id, data FROM entries WHERE has_unlinked_sense IS NULL').fetchall():
                entry = json.loads(row['data'])
                has_unlinked = 1 if any(not s.get('synset','') for s in entry.get('senses',[])) else 0
                updates.append((has_unlinked, row['id']))
            c.executemany('UPDATE entries SET has_unlinked_sense=? WHERE id=?', updates)
            c.commit()
            # Refresh entry_index with backfilled values
            rows_e2 = c.execute('SELECT id, has_unlinked_sense FROM entries').fetchall()
            uls_map = {r['id']: bool(r['has_unlinked_sense']) for r in rows_e2}
            for stub in entry_index:
                stub['hasMissingSynset'] = uls_map.get(stub['id'], False)
            print(f'has_unlinked_sense backfilled for {len(updates):,} entries', flush=True)

        # Annotate synset_index with hasDutchSynonyms using the synset_entry_index
        linked_ss = {r[0] for r in c.execute('SELECT DISTINCT synset_id FROM synset_entry_index').fetchall()}
        for stub in synset_index:
            stub['hasDutchSynonyms'] = stub['id'] in linked_ss

        with _slock:
            _st['globalInfo']   = global_info
            _st['lexicon']      = lexicon_meta
            _st['entry_index']  = entry_index
            _st['synset_index'] = synset_index
            _st['filepath']     = filepath
            _st['filename']     = filename
            _st['ready']        = True
            _st['loading_msg']  = ''
        print(f'Ready: {len(entry_index):,} entries, {len(synset_index):,} synsets', flush=True)
        _load_en_synonyms()
    except Exception as ex:
        with _slock: _st['loading_msg'] = f'Error: {ex}'
        print(f'Load error: {ex}', flush=True)
        import traceback; traceback.print_exc()

# ─────────────────────────────────────────────────────────────────────
# English synonym loader
# ─────────────────────────────────────────────────────────────────────

_EN_SYN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'data', 'wneng30_synset_synonyms.json')

def _load_en_synonyms():
    """Load English synonym mapping from JSON into DB, then enrich synset_index stubs."""
    c = _con()
    count = c.execute('SELECT COUNT(*) FROM en_synonyms').fetchone()[0]
    if count == 0:
        if not os.path.isfile(_EN_SYN_FILE):
            print(f'EN synonyms file not found, skipping: {_EN_SYN_FILE}', flush=True)
            return
        print('Loading English synonyms into database…', flush=True)
        with open(_EN_SYN_FILE, encoding='utf-8') as f:
            data = json.load(f)
        items = [(ss_id, json.dumps(words, ensure_ascii=False)) for ss_id, words in data.items()]
        BATCH = 5000
        with _write_lock:
            for i in range(0, len(items), BATCH):
                c.executemany('INSERT OR REPLACE INTO en_synonyms (synset_id, words) VALUES (?,?)',
                              items[i:i + BATCH])
                c.commit()
        print(f'Loaded {len(items):,} English synonym sets', flush=True)
    else:
        print(f'EN synonyms already in DB: {count:,}', flush=True)

    # Enrich in-memory synset_index stubs with a space-joined search string
    rows = c.execute('SELECT synset_id, words FROM en_synonyms').fetchall()
    lookup = {r['synset_id']: ' '.join(json.loads(r['words'])) for r in rows}
    enriched = 0
    with _slock:
        for stub in _st['synset_index']:
            en = lookup.get(stub['id'])
            if en:
                stub['enSyns'] = en
                enriched += 1
    print(f'Enriched {enriched:,} synset stubs with EN synonyms', flush=True)

# ─────────────────────────────────────────────────────────────────────
# XML Serializer
# ─────────────────────────────────────────────────────────────────────

def _xe(s):
    return str(s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def _at(n, v):
    return f' {n}="{_xe(v)}"' if v else ''

def _entry_to_xml_lines(e):
    """Return XML lines for a single LexicalEntry dict (4-space indent at top level)."""
    L = []
    L.append(f'    <LexicalEntry id="{_xe(e["id"])}"{_at("partOfSpeech",e.get("partOfSpeech",""))}{_at("formType",e.get("formType",""))}>')
    if e.get('isMWE'):
        L.append(f'      <MultiwordExpression writtenForm="{_xe(e.get("mweForm",""))}"{_at("expressionType",e.get("mweExpressionType",""))}/>')
    else:
        L.append(f'      <Lemma writtenForm="{_xe(e.get("lemma",""))}"{_at("mode",e.get("lemmaMode",""))}/>')
        wfs = e.get('wordForms', [])
        if wfs:
            L.append('      <WordForms>')
            for wf in wfs:
                L.append(f'        <WordForm writtenForm="{_xe(wf["writtenForm"])}"{_at("grammaticalNumber",wf.get("grammaticalNumber",""))}{_at("comparison",wf.get("comparison",""))} article="{_xe(wf.get("article",""))}"{_at("tense",wf.get("tense",""))}/>')
            L.append('      </WordForms>')
        else:
            L.append('      <WordForms/>')
    rfs = e.get('relatedForms', [])
    if rfs:
        L.append('      <RelatedForms>')
        for rf in rfs:
            L.append(f'        <RelatedForm writtenForm="{_xe(rf["writtenForm"])}"{_at("variantType",rf.get("variantType",""))}/>')
        L.append('      </RelatedForms>')
    m = e.get('morphology', {})
    L.append(f'      <Morphology{_at("morphoType",m.get("morphoType",""))}{_at("comparisonType",m.get("comparisonType",""))}{_at("declinable",m.get("declinable",""))}{_at("separability",m.get("separability",""))}/>')
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
        for comp in comps:
            L.append(f'        <Complementation{_at("complement",comp.get("complement",""))}{_at("preposition",comp.get("preposition",""))}/>')
        for frm in frames:
            L.append('        <SyntacticSubcategorisationFrame>')
            for a in frm.get('args', []):
                L.append(f'          <syntacticArgument{_at("constituent",a.get("constituent",""))}{_at("function",a.get("function",""))}{_at("preposition",a.get("preposition",""))}{_at("complementizer",a.get("complementizer",""))}/>')
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
                for sh in shifts: L.append(f'          <semanticShifts-noun{_at("semanticType",sh.get("semanticType",""))}/>')
                L.append('        </Semantics-noun>')
            else:
                L.append(f'        <Semantics-noun{sn_a}/>')
        sv = sense.get('semanticsVerb')
        if sv is not None:
            types = sv.get('semanticTypes', [])
            if types:
                L.append('        <Semantics-verb>')
                for t in types: L.append(f'          <semanticTypes{_at("semanticType",t.get("semanticType",""))}{_at("semanticFeatureSet",t.get("semanticFeatureSet",""))}/>')
                L.append('        </Semantics-verb>')
            else:
                L.append('        <Semantics-verb/>')
        sa = sense.get('semanticsAdj')
        if sa is not None:
            sa_a = _at('semanticType', sa.get('semanticType',''))
            shifts = sa.get('shifts', [])
            if shifts:
                L.append(f'        <Semantics-adjective{sa_a}>')
                for sh in shifts: L.append(f'          <semanticShifts-adjective{_at("semanticType",sh.get("semanticType",""))}/>')
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
                L.append(f'            <textualForm textualform="{_xe(ex["textualForm"])}"{_at("phraseType",ex.get("phraseType",""))}/>')
                L.append('            <Semantics_ex/><Pragmatics/>')
                L.append('          </SenseExample>')
            L.append('        </SenseExamples>')
        sent = sense.get('sentiment')
        if sent is not None:
            L.append(f'        <Sentiment polarity="{_xe(sent["polarity"])}" externalReference="{_xe(sent["externalReference"])}"/>')
        L.append('      </Sense>')
    L.append('    </LexicalEntry>')
    return L

def _synset_to_xml_lines(ss):
    """Return XML lines for a single Synset dict (4-space indent at top level)."""
    L = []
    ss_a = f' id="{_xe(ss["id"])}"{_at("ili",ss.get("ili",""))}{_at("baseConcept",ss.get("baseConcept",""))}'
    defs = ss.get('definitions', [])
    rels = ss.get('synsetRelations', [])
    mers = ss.get('monolingualExternalRefs', [])
    if not (defs or rels or mers):
        L.append(f'    <Synset{ss_a}/>'); return L
    L.append(f'    <Synset{ss_a}>')
    if defs:
        L.append('      <Definitions>')
        for d in defs: L.append(f'        <Definition gloss="{_xe(d["gloss"])}"{_at("language",d.get("language",""))}{_at("provenance",d.get("provenance",""))}/>')
        L.append('      </Definitions>')
    if rels:
        L.append('      <SynsetRelations>')
        for r in rels: L.append(f'        <SynsetRelation{_at("provenance",r.get("provenance",""))} relType="{_xe(r["relType"])}" target="{_xe(r["target"])}"/>')
        L.append('      </SynsetRelations>')
    if mers:
        L.append('      <MonolingualExternalRefs>')
        for m in mers: L.append(f'        <MonolingualExternalRef externalReference="{_xe(m["externalReference"])}" externalSystem="{_xe(m["externalSystem"])}"{_at("relType",m.get("relType",""))}/>')
        L.append('      </MonolingualExternalRefs>')
    L.append('    </Synset>')
    return L

def serialize_xml():
    with _slock:
        entry_index  = list(_st['entry_index'])
        synset_index = list(_st['synset_index'])
        gi  = _st['globalInfo']
        lx  = _st['lexicon']

    c = _con()
    entries = {r['id']: json.loads(r['data']) for r in c.execute('SELECT id,data FROM entries').fetchall()}
    synsets = {r['id']: json.loads(r['data']) for r in c.execute('SELECT id,data FROM synsets').fetchall()}

    L = ["<?xml version='1.0' encoding='UTF-8'?>", '<LexicalResource>',
         f'  <GlobalInformation label="{_xe(gi["label"])}"/>']
    L.append(f'  <Lexicon{_at("languageCoding",lx["languageCoding"])}{_at("label",lx["label"])}{_at("language",lx["language"])}{_at("owner",lx["owner"])}>')

    for idx in entry_index:
        e = entries.get(idx['id'])
        if e is None: continue
        L.extend(_entry_to_xml_lines(e))

    for ss_idx in synset_index:
        ss = synsets.get(ss_idx['id'])
        if ss is None: continue
        L.extend(_synset_to_xml_lines(ss))

    L.append('  </Lexicon>')
    L.append('</LexicalResource>')
    return '\n'.join(L)

# ─────────────────────────────────────────────────────────────────────
# HTTP Request Handler
# ─────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR  = os.path.join(BASE_DIR, 'log')

def _write_change_log(item_type, item_id, user, ts, old_data, new_data):
    """Write a change-log XML file to LOG_DIR capturing old and new versions of an item."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        iso_file = time.strftime('%Y%m%d_%H%M%S', time.localtime(ts))
        iso_full = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ts))
        safe_id  = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in item_id)
        fname    = f'{iso_file}_{item_type}_{safe_id}.xml'
        L = [
            "<?xml version='1.0' encoding='UTF-8'?>",
            f'<ChangeLog itemType="{item_type}" itemId="{_xe(item_id)}" user="{_xe(user)}" timestamp="{iso_full}">',
            '  <OldVersion>',
        ]
        if old_data:
            if item_type == 'entry':
                L.extend(_entry_to_xml_lines(old_data))
            else:
                L.extend(_synset_to_xml_lines(old_data))
        L.append('  </OldVersion>')
        L.append('  <NewVersion>')
        if item_type == 'entry':
            L.extend(_entry_to_xml_lines(new_data))
        else:
            L.extend(_synset_to_xml_lines(new_data))
        L.append('  </NewVersion>')
        L.append('</ChangeLog>')
        with open(os.path.join(LOG_DIR, fname), 'w', encoding='utf-8') as f:
            f.write('\n'.join(L))
        print(f'Change log: {fname}', flush=True)
    except Exception as ex:
        print(f'Warning: change log write failed: {ex}', flush=True)

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress per-request logs

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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Session-Token')
        self.end_headers()

    def _auth_user(self, body=None):
        """Extract and validate session token. Returns username or None."""
        token = (self.headers.get('X-Session-Token', '') or
                 parse_qs(urlparse(self.path).query).get('token', [''])[0])
        if not token and body:
            token = str(body.get('token', ''))
        return _validate_session(token)

    def do_GET(self):
        p = urlparse(self.path)
        path, qs = p.path, parse_qs(p.query)

        # Public endpoints (no auth required)
        if path == '/api/status':
            now = time.time()
            with _slock:
                _st['active_users'] = {u: t for u, t in _st['active_users'].items() if now - t < 120}
                active = [u for u, t in _st['active_users'].items() if now - t < 60]
                ready  = _st['ready']
                msg    = _st['loading_msg']
                fname  = _st['filename']
            c = _con()
            self._json({
                'ready': ready, 'loadingMsg': msg, 'filename': fname,
                'seq': _current_seq(),
                'active_users': len(active), 'users': len(active), 'userList': active,
                'entriesCount': c.execute('SELECT COUNT(*) FROM entries').fetchone()[0],
                'synsetsCount': c.execute('SELECT COUNT(*) FROM synsets').fetchone()[0],
            })
            return

        if not path.startswith('/api/'):
            self._serve_static(path)
            return

        # All other /api/ endpoints require a valid session
        user = self._auth_user()
        if not user:
            self._json({'error': 'unauthorized'}, 401); return

        if path == '/api/whoami':
            self._json({'username': user})

        elif path == '/api/index':
            if not _st['ready']:
                self._json({'error': 'loading', 'msg': _st['loading_msg']}, 503); return
            with _slock:
                self._json({
                    'globalInfo':   _st['globalInfo'],
                    'lexicon':      _st['lexicon'],
                    'filename':     _st['filename'],
                    'seq':          _current_seq(),
                    'entry_index':  _st['entry_index'],
                    'synset_index': _st['synset_index'],
                })

        elif path.startswith('/api/entry/'):
            eid = path[len('/api/entry/'):]
            e   = get_entry(eid)
            if e is None:
                self._json({'error': 'not found'}, 404); return
            ok, lock = try_acquire_lock('entry', eid, user)
            e['_lock'] = {**lock, 'is_mine': ok}
            self._json(e)

        elif path.startswith('/api/synset/'):
            sid = path[len('/api/synset/'):]
            ss  = get_synset(sid)
            if ss is None:
                self._json({'error': 'not found'}, 404); return
            c = _con()
            # English synonyms
            en_row = c.execute('SELECT words FROM en_synonyms WHERE synset_id=?', (sid,)).fetchone()
            if en_row:
                ss['_en_synonyms'] = json.loads(en_row['words'])
            # Dutch entry synonyms from index
            nl_rows = c.execute(
                'SELECT e.id, e.lemma, e.mwe_form, e.is_mwe, e.part_of_speech '
                'FROM synset_entry_index sei JOIN entries e ON sei.entry_id = e.id '
                'WHERE sei.synset_id = ?', (sid,)
            ).fetchall()
            ss['_nl_entries'] = [
                {'id': r['id'],
                 'lemma': r['mwe_form'] if r['is_mwe'] else r['lemma'],
                 'partOfSpeech': r['part_of_speech']}
                for r in nl_rows
            ]
            ok, lock = try_acquire_lock('synset', sid, user)
            ss['_lock'] = {**lock, 'is_mine': ok}
            self._json(ss)

        elif path == '/api/changes':
            since = int(qs.get('since', ['0'])[0])
            now   = time.time()
            with _slock:
                _st['active_users'] = {u: t for u, t in _st['active_users'].items() if now - t < 120}
                active_count = sum(1 for t in _st['active_users'].values() if now - t < 60)
            changes = _changes_since(since)
            self._json({'changes': changes, 'active_users': active_count})

        elif path == '/api/locks':
            self._json({'locks': all_locks()})

        elif path == '/api/export/xml':
            self._handle_export_xml()

        elif path == '/api/export/json':
            self._handle_export_json()

        else:
            self._json({'error': 'Not found'}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        # Login — public, no auth
        if path == '/api/login':
            username = str(body.get('username', ''))[:64].strip()
            password = str(body.get('password', ''))
            token    = _do_login(username, password)
            if token:
                self._json({'ok': True, 'token': token, 'username': username})
            else:
                self._json({'error': 'Invalid username or password.'}, 401)
            return

        # All other POST endpoints require a valid session
        user = self._auth_user(body)
        if not user:
            self._json({'error': 'unauthorized'}, 401); return

        if path == '/api/logout':
            token = (self.headers.get('X-Session-Token', '') or str(body.get('token', '')))
            _do_logout(token)
            self._json({'ok': True})

        elif path == '/api/update':
            body['user'] = user  # always use authenticated username
            self._handle_update(body)

        elif path == '/api/unlock':
            item_type = body.get('itemType', '')
            item_id   = body.get('itemId', '')
            if item_type and item_id:
                release_lock(item_type, item_id, user)
            self._json({'ok': True})

        elif path == '/api/save':
            self._handle_save()

        elif path == '/api/heartbeat':
            with _slock:
                _st['active_users'][user] = time.time()
                count = sum(1 for t in _st['active_users'].values() if time.time() - t < 60)
            self._json({'ok': True, 'users': count, 'active_users': count})

        elif path == '/api/lexicon':
            c = _con()
            with _slock:
                if 'globalInfo' in body: _st['globalInfo'] = body['globalInfo']
                if 'lexicon'    in body: _st['lexicon']    = body['lexicon']
            if 'globalInfo' in body:
                c.execute('INSERT OR REPLACE INTO meta VALUES ("globalInfo",?)', (json.dumps(body['globalInfo']),))
            if 'lexicon' in body:
                c.execute('INSERT OR REPLACE INTO meta VALUES ("lexicon",?)',    (json.dumps(body['lexicon']),))
            c.commit()
            seq = _record_change('update', 'lexicon', 'lexicon', body, user)
            self._json({'ok': True, 'seq': seq})

        else:
            self._json({'error': 'Not found'}, 404)

    def _handle_update(self, body):
        op        = body.get('op', 'update')
        item_type = body.get('itemType', 'entry')
        data      = body.get('data', {})
        user      = str(body.get('user', ''))[:64] or self.client_address[0]
        item_id   = data.get('id', '') if data else body.get('id', '')
        explicit  = bool(body.get('explicit', False))

        # For update/delete, require that the user holds (or is free to take) the lock
        if op in ('update', 'delete') and item_id:
            lock = get_lock(item_type, item_id)
            if lock and lock['user'] != user:
                self._json({'error': 'locked', 'lock': lock}, 423)
                return
            if op == 'update':
                try_acquire_lock(item_type, item_id, user)

        # Capture old version from DB before overwriting (for change log)
        old_data = None
        if explicit and op == 'update' and item_id:
            c = _con()
            if item_type == 'entry':
                row = c.execute('SELECT data FROM entries WHERE id=?', (item_id,)).fetchone()
            else:
                row = c.execute('SELECT data FROM synsets WHERE id=?', (item_id,)).fetchone()
            if row:
                old_data = json.loads(row['data'])

        if item_type == 'entry':
            if op == 'delete':
                # Collect old synset links before deleting so we can refresh their flags
                old_ss = [r[0] for r in _con().execute(
                    'SELECT DISTINCT synset_id FROM synset_entry_index WHERE entry_id=?', (item_id,)).fetchall()]
                delete_entry(item_id)
                with _slock:
                    _st['entry_index'] = [x for x in _st['entry_index'] if x['id'] != item_id]
                _refresh_synset_nl_flags(old_ss)
            elif op == 'add':
                upsert_entry(data, user)
                try_acquire_lock('entry', item_id, user)
                lemma = data.get('mweForm','') if data.get('isMWE') else data.get('lemma','')
                has_unlinked = any(not s.get('synset','') for s in data.get('senses',[]))
                with _slock:
                    _st['entry_index'].insert(0, {
                        'id': data['id'], 'isMWE': data.get('isMWE', False),
                        'lemma': lemma, 'partOfSpeech': data.get('partOfSpeech',''),
                        'mweForm': data.get('mweForm',''),
                        'hasMissingSynset': has_unlinked,
                    })
                # Update hasDutchSynonyms on affected synset stubs
                _refresh_synset_nl_flags([s.get('synset','') for s in data.get('senses',[]) if s.get('synset','')])
            else:
                # Collect OLD synset links before overwriting (to refresh removed links too)
                old_ss = [r[0] for r in _con().execute(
                    'SELECT DISTINCT synset_id FROM synset_entry_index WHERE entry_id=?', (item_id,)).fetchall()]
                upsert_entry(data, user)
                lemma = data.get('mweForm','') if data.get('isMWE') else data.get('lemma','')
                has_unlinked = any(not s.get('synset','') for s in data.get('senses',[]))
                with _slock:
                    for idx in _st['entry_index']:
                        if idx['id'] == item_id:
                            idx['lemma']             = lemma
                            idx['partOfSpeech']      = data.get('partOfSpeech','')
                            idx['mweForm']           = data.get('mweForm','')
                            idx['hasMissingSynset']  = has_unlinked
                            break
                # Refresh both old (possibly removed) and new synset stubs
                new_ss = [s.get('synset','') for s in data.get('senses',[]) if s.get('synset','')]
                _refresh_synset_nl_flags(list(set(old_ss + new_ss)))
        else:
            if op == 'delete':
                delete_synset(item_id)
                with _slock:
                    _st['synset_index'] = [x for x in _st['synset_index'] if x['id'] != item_id]
            elif op == 'add':
                upsert_synset(data, user)
                try_acquire_lock('synset', item_id, user)
                gloss = data['definitions'][0]['gloss'][:80] if data.get('definitions') else ''
                with _slock:
                    _st['synset_index'].insert(0, {'id': data['id'], 'gloss': gloss})
            else:
                upsert_synset(data, user)
                gloss = data['definitions'][0]['gloss'][:80] if data.get('definitions') else ''
                with _slock:
                    for idx in _st['synset_index']:
                        if idx['id'] == item_id:
                            idx['gloss'] = gloss
                            break

        with _slock:
            _st['modified'] = True
        seq = _record_change(op, item_type, item_id, data if op != 'delete' else None, user)
        changes = data.get('_changes', []) if data and op != 'delete' else []

        if explicit and op == 'update' and data:
            _write_change_log(item_type, item_id, user, time.time(), old_data, data)

        self._json({'ok': True, 'seq': seq, 'changes': changes})

    def _handle_save(self):
        if not _st['ready']:
            self._json({'error': 'not ready'}, 503); return
        try:
            xml = serialize_xml()
            with _slock:
                filepath = _st['filepath']
                _st['modified'] = False
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(xml)
                print(f'Saved to {filepath}', flush=True)
                self._json({'ok': True, 'filename': os.path.basename(filepath)})
            else:
                self._json({'ok': True, 'filename': 'lexicon.xml'})
        except Exception as ex:
            self._json({'error': str(ex)}, 500)

    def _handle_export_xml(self):
        if not _st['ready']:
            self._json({'error': 'not ready'}, 503); return
        try:
            xml = serialize_xml()
            body = xml.encode('utf-8')
            with _slock:
                fname = os.path.basename(_st['filepath']) if _st['filepath'] else 'lexicon.xml'
            self.send_response(200)
            self.send_header('Content-Type', 'application/xml; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
            self.send_header('Content-Length', len(body))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        except Exception as ex:
            self._json({'error': str(ex)}, 500)

    def _handle_export_json(self):
        if not _st['ready']:
            self._json({'error': 'not ready'}, 503); return
        try:
            c = _con()
            entries = [json.loads(r['data']) for r in c.execute('SELECT data FROM entries ORDER BY rowid').fetchall()]
            synsets = [json.loads(r['data']) for r in c.execute('SELECT data FROM synsets ORDER BY rowid').fetchall()]
            with _slock:
                gi  = _st['globalInfo']
                lx  = _st['lexicon']
                raw = _st['filepath'] or 'lexicon.xml'
            fname = os.path.basename(raw).replace('.xml', '') + '.json'
            data  = {'globalInfo': gi, 'lexicon': lx, 'entries': entries, 'synsets': synsets}
            body  = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
            self.send_header('Content-Length', len(body))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        except Exception as ex:
            self._json({'error': str(ex)}, 500)

    def _serve_static(self, path):
        if path in ('/', '/index.html', ''):
            path = '/index.html'
        filepath = os.path.join(BASE_DIR, path.lstrip('/'))
        if not os.path.realpath(filepath).startswith(BASE_DIR):
            self.send_response(403); self.end_headers(); return
        if os.path.isfile(filepath):
            ext  = os.path.splitext(filepath)[1]
            mime = {'html':'text/html','js':'application/javascript','css':'text/css',
                    'xml':'application/xml','json':'application/json'}.get(ext.lstrip('.'), 'application/octet-stream')
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

    xml_file   = None
    db_file    = None
    users_file = USERS_FILE
    port       = 8080

    for arg in args:
        if arg.isdigit():
            port = int(arg)
        elif arg.endswith('.db'):
            db_file = arg
        elif arg.endswith('.xml') or arg.endswith('.xml.gz'):
            xml_file = arg
        elif arg.endswith('.json'):
            users_file = arg

    USERS = load_users_file(users_file)

    # Auto-discover: prefer existing .db over .xml, but only if DB has actual data
    if xml_file is None and db_file is None:
        candidates = [
            ('data/odwn_orbn_gwg-LMF_1.3.db',  'data/odwn_orbn_gwg-LMF_1.3.xml'),
            ('data/odwn_orbn_gwg-LMF_1.2.db',  'data/odwn_orbn_gwg-LMF_1.2.xml'),
        ]
        for cdb, cxml in candidates:
            if os.path.isfile(cdb):
                _db_has_data = False
                try:
                    _db_has_data = sqlite3.connect(cdb).execute('SELECT COUNT(*) FROM entries').fetchone()[0] > 0
                except Exception:
                    pass
                if _db_has_data:
                    db_file = cdb; break
                elif os.path.isfile(cxml):
                    print(f'Database {cdb} exists but is empty — will re-import from {cxml}.')
                    xml_file = cxml; break
            elif os.path.isfile(cxml):
                xml_file = cxml; break

    # Derive DB path from XML path if needed
    if db_file:
        DB_PATH = db_file
    elif xml_file:
        base = xml_file
        for suffix in ('.xml.gz', '.xml'):
            if base.endswith(suffix):
                base = base[:-len(suffix)]; break
        DB_PATH = base + '.db'
    else:
        DB_PATH = 'lexicon.db'

    _init_schema()
    _sync_users()

    if db_file:
        t = threading.Thread(target=load_from_db, daemon=True)
        t.start()
    elif xml_file:
        existing = False
        if os.path.isfile(DB_PATH) and os.path.getsize(DB_PATH) > 4096:
            try:
                cnt = _con().execute('SELECT COUNT(*) FROM entries').fetchone()[0]
                existing = cnt > 0
            except Exception:
                existing = False
        if existing:
            print(f'Existing database found: {DB_PATH} — loading (skip re-import).')
            t = threading.Thread(target=load_from_db, daemon=True)
        else:
            if os.path.isfile(DB_PATH) and not existing:
                print(f'Database {DB_PATH} exists but is empty — re-importing from XML.')
            t = threading.Thread(target=load_xml, args=(xml_file,), daemon=True)
        t.start()
    else:
        with _slock:
            _st['ready']       = True
            _st['loading_msg'] = ''
        print('No data file found. Starting with empty lexicon.')

    server = http.server.ThreadingHTTPServer(('', port), Handler)
    print(f'ODWN LMF Editor  →  http://localhost:{port}')
    if xml_file or db_file:
        src = db_file or xml_file
        print(f'Data: {src}  →  DB: {DB_PATH}')
        print('Editor available immediately; data loads in background.')
    print(f'Lock TTL: {LOCK_TTL}s  |  Press Ctrl+C to stop.\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
