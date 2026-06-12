# ODWN LMF Editor

A browser-based editor for lexical resources in [Lexical Markup Framework (LMF)](https://www.iso.org/standard/82429.html) format (ISO 24613). Built for the [Open Dutch WordNet (ODWN)](https://github.com/cltl/OpenDutchWordnet) / ORBN format, and conforming to the `odwn-orbn-lmf.dtd` schema. Also opens generic feat-based LMF files.
The OpenDutchWordnet uses a rich WordNetLMF DTD that allows to define form and meaning information on each sense of a word as well as Wordnet synsets and synset relations. Likewise, it has a repository of lexical units and a repository of synsets.
The synsets are based on the Pricenton WordNet3.0 but have been extended with new synsets as well. Most of the synset relations also originate from the Pricneton WordNet but new reltions have also been added.
The lexical units are linked to synsets as synonyms and vice versa. This editor allows to modify the lexical units, the synsets and the links between them.

---

## Quick start

### Collaborative server (recommended)

Allows multiple users to edit the same file simultaneously in real time. This is the primary workflow:

1. Set-up the server:

Copy the latest release of the OpenDutchWordnet to the data folder of the server, wherever it is installed. 
The latest release can be found on [https://github.com/MartenPostma/OpenDutchWordnet/raw/master/resources/odwn](https://github.com/MartenPostma/OpenDutchWordnet/raw/master/resources/odwn)
and should be part of this cloned repository.

2. Launch the server from the command line:

```bash
python3 server.py
# with options:
python3 server.py data/odwn_orbn_gwg-LMF_1.3.xml 8080
```

3. Open a client in your browser:

Then open `http://localhost:8080` in each user's browser. The editor detects the server automatically, switches to collaborative mode, and presents a login form.

On first run the server imports the XML into a SQLite database (`.db` file alongside the XML). Subsequent runs load directly from the database — no re-parsing of the large XML.

4. Export the SQLite database regularly to keep an XML copy of the data.

5. Push a stable version of the XML copy to Github

Editors need to login in with their user name and password. These are defined in the "users.json" file. When editing a lexical entry sense or a synset, the data is locked for other users.
After 

### Standalone (single user)

Open `index.html` directly in a browser (no server required). Data must be loaded programmatically or pre-loaded into the in-memory state. The collaborative server is recommended for all production use.

---

## Toolbar

| Button | Action |
|---|---|
| **Export XML** | Download the full database as an LMF XML file |
| **Export JSON** | Download the full database as a JSON file |
| **Lexicon Settings** | Edit lexicon metadata (label, language, owner, …) |
| **Sign out** | Log out and return to the login screen (collaborative mode only) |

In collaborative mode the toolbar also shows a green dot with the number of active users.

---

## Browsing

The left sidebar has two tabs: **Entries** and **Synsets**.

- Each row shows the lemma (or MWE form) and part of speech.
- The list uses **virtual scrolling** — only the visible rows are rendered in the DOM, so 99 000-entry files scroll without lag.
- Type in the **search box** to filter by lemma, entry ID, or (for synsets) definition gloss or English synonym in real time.
- The item count below the search box reflects the current filter.
- **+ Add Entry** / **+ Add Synset** button at the bottom of the sidebar creates a new item.

---

## Editing entries

Click any entry in the sidebar to open it in the editor. Changes are saved automatically every 1.5 seconds after you stop typing (collaborative mode), or collected when you switch items (standalone mode).

When multiple entries share the same lemma, clicking the lemma row shows a **sense overview table** for the whole group. Click any row to open that entry, or click **+ Add sense** in the card header to create a new entry for the same lemma.

### Lemma & Identity

| Field | Description |
|---|---|
| Written Form | The canonical lemma string |
| Part of Speech | `noun`, `verb`, `adjective`, `adverb`, `other` |
| Lemma Mode | Optional; `infinitive` for verb lemmas |
| Form Type | `contraction`, `acronym`, `abbreviation` |
| Entry ID | Unique identifier, e.g. `fiets-n-1` |

Multiword Expression (MWE) entries replace the lemma with:

| Field | Description |
|---|---|
| MWE Written Form | The full written form of the expression |
| Expression Type | `idiom` or `proverb` |

### Senses

Each entry can have one or more senses. Click **+ Add** in the Senses card header to append a sense; click **Remove** on a sense block to delete it.

| Field | Description |
|---|---|
| Definition | Free-text gloss |
| Sense ID | Numeric or string identifier within the entry |
| Synset | Synset reference, e.g. `eng-30-06952861-n` |
| Provenance | Data source (`bing`, `google`, `opus`, `cdb2.2_Auto`, …) |
| Annotator | Name of the responsible annotator (auto-filled with the logged-in username) |

The **Synset** field has an **↗ Open** button that switches to the Synsets panel and opens the referenced synset directly.

Each sense block also contains collapsible sections:

**Sense Relations** — links to other senses via `SenseGroup`:

| Type | Meaning |
|---|---|
| `co-synonyms` | Senses sharing the same synset |
| `co-hyponyms` | Senses that are co-hyponyms |
| `co-relations` | Other semantic relations |
| `co-annotation` | Annotation grouping |

**Semantics-noun** (add/remove per sense) — reference (`common`/`proper`), countability, semantic type, semantic sub-type, and semantic shifts.

**Semantics-verb** (add/remove per sense) — one or more semantic type rows (`action`, `process`, `state`) with optional feature sets.

**Semantics-adjective** (add/remove per sense) — semantic type and semantic shifts.

**Pragmatics** — chronology, connotation, geography, register, and one or more domain labels (70 values including `medicine`, `law`, `linguistics`, `sport`, …).

**Sense Examples** — usage examples with phrase type (`np`, `vp`, `ap`, `pp`, `sentence`).

**Sentiment** (add/remove per sense) — polarity (`positive`/`negative`) and external reference.

### Word Forms

Inflected forms of the lemma. Each row has:

| Field | Values |
|---|---|
| Written Form | Inflected string |
| Grammatical Number | `singular`, `plural` |
| Comparison | `comparative`, `superlative` |
| Article | Free text |
| Tense | `pastTense`, `pastParticiple` |

### Related Forms

Variant spellings and alternate forms:

| Field | Values |
|---|---|
| Written Form | Variant string |
| Variant Type | `formVariant`, `spellingVariant` |

### Morphology

| Field | Values |
|---|---|
| Morpho Type | `compderiv`, `derivation`, `compound`, `zero-derivation`, `x-compound`, `wordgroup`, `phrasal` |
| Comparison Type | `regular`, `irregular`, `mixed` |
| Declinable | `yes`, `no` |
| Separability | `separable`, `inseparable` (verbs) |

### MorphoSyntax

| Field | Values |
|---|---|
| Grammatical Gender | `m`, `f`, `n`, `fn`, `m_f`, `mfn`, `mn`, `mf` |
| Position | `attributive`, `predicative`, `attrpred` (adjectives) |
| Adverbial Usage | `yes`, `no` |
| Reflexivity | `optionalReflexive`, `reflexive` |
| Auxiliaries | `hebben`, `zijn` (checkboxes, verbs) |

### Syntactic Behaviour

| Field | Values |
|---|---|
| Valency | `mono`, `di`, `tri` |
| Transitivity | `transitive`, `intransitive` |
| Complementations | Complement type + optional preposition (expandable list) |
| Subcategorisation Frames | Read from XML; displayed as count, edit via raw XML |

### Entry actions

- **Save** (collaborative mode) — explicitly saves the current entry and writes a change-log file.
- **History** — shows a popup with the edit history (user + timestamp) for this entry.
- **Delete** — removes the entry after confirmation.
- **+ Add Entry** (sidebar footer) — opens a dialog to create a new entry together with a new synset (see [Creating new entries](#creating-new-entries)).

---

## Creating new entries

Clicking **+ Add Entry** (or **+ Add sense** in the sense overview) opens a dialog asking for:

- **Lemma** — the written form (pre-filled when opened from the sense overview).
- **Part of speech** — `noun`, `verb`, `adjective`, `adverb`, or `other`.

On confirmation the editor creates:

1. A new **lexical entry** with ID `{lemma}-{pos_abbr}-{n}` (e.g. `fiets-n-2`) and one sense.
2. A new **synset** with ID `odwn-20-{9-digit number}-{pos_abbr}` (e.g. `odwn-20-000000001-n`), automatically linked to the new sense.

The sense's Annotator field is pre-filled with the logged-in username. Both items are pushed to the server immediately in collaborative mode.

---

## Editing synsets

Click the **Synsets** tab in the sidebar to browse and edit synsets.

### Synset Identity

| Field | Description |
|---|---|
| Synset ID | Unique identifier, e.g. `odwn-20-000000001-n` |
| ILI | Interlingual Index reference |
| Base Concept | Base concept level |

### Definitions

Each synset can have multiple definitions with gloss, language code, and provenance.

### Dutch synonyms

A **Dutch synonyms** card lists all entries whose senses point to this synset. Each row shows the lemma and part of speech with:

- **↗ Open** — switches to the Entries panel and opens that entry.
- **Unlink** — removes the synset reference from that entry's sense.
- **+ Link ID** — manually type an entry ID to add as a synonym.
- **🔍 Find word** — opens a search dialog to locate an entry by lemma:
  - If found: select an existing sense to link, or add a new sense.
  - If not found: create a new entry with sense 1 linked to this synset.

### English synonyms

A read-only **English synonyms** card shows the Princeton WordNet 3.0 synonyms for this synset (sourced from `data/wneng30_synset_synonyms.json`). These cannot be edited. English synonyms are also included in the synset search index.

### Synset Relations

Relations to other synsets. Each row has a relation type (from a full enumeration including `has_hyperonym`, `has_hyponym`, `near_synonym`, `role_agent`, …), a target synset ID, and provenance. Each row has an **↗** button to jump directly to the target synset.

### Relation Graph

Every synset editor shows a **Relation Graph** card below the relations table. The graph visualises the synset's neighbourhood as a force-directed SVG diagram.

**Layout**

- The current synset sits at the centre (dark node).
- Its direct relations radiate outward as **level-1 nodes** (blue).
- Each level-1 node's own relations are shown as **level-2 nodes** (lighter blue), giving two levels of depth by default. Up to 8 outgoing relations are shown per non-root node; if more exist a grey **+N more** node marks the remainder.
- Edges are labelled with the relation type name and colour-coded by category. A colour legend appears below the graph.
- Solid lines connect level-1 nodes; dashed lines connect level-2 nodes. Arrowheads point toward the target synset.

**Node labels**

Each node is labelled with the synonym lemmas of that synset, taken from any entries that reference it. If no entries have been loaded for a synset, the first definition gloss is used instead. Labels wrap across two lines inside the node circle.

**Hover tooltip**

Hovering over any node shows a floating tooltip with:

- The synset ID (small, monospace)
- All synonym lemmas in bold
- All definition glosses in italic

The tooltip repositions automatically to stay within the viewport.

**Interaction**

| Action | Effect |
|---|---|
| Hover a **node** | Shows the tooltip with full synonyms and glosses |
| Click an **edge** | Toggles expand/collapse on the target node |
| Click a **node** | Opens a small popup with two buttons |
| Popup → **Expand** | Reveals the node's further relations |
| Popup → **Collapse** | Hides the nodes added by expanding this node |
| Popup → **Make center** | Navigates to that synset, making it the new centre of the graph |
| **Reset** button (card header) | Collapses all expansions back to the default two-level view |
| Drag the background | Pans the graph |

Expanded nodes are highlighted with an orange ring. Clicking anywhere outside the popup dismisses it.

> In collaborative mode, level-2 and deeper synsets are only shown if their full data has already been fetched from the server (i.e. you have opened them at least once).

### Monolingual External Refs

Read-only display of external references (Princeton WordNet, etc.). Edit via raw XML if needed.

### Synset actions

- **Save** (collaborative mode) — explicitly saves the current synset and writes a change-log file.
- **History** — shows a popup with the edit history (user + timestamp) for this synset.
- **Delete** — removes the synset after confirmation.

---

## Change log

Every time a user clicks the explicit **Save** button (not auto-save), the server writes an XML file to the `log/` directory alongside `server.py`:

```
log/YYYYMMDD_HHMMSS_{type}_{id}.xml
```

Each file contains the full XML of the item before and after the save:

```xml
<?xml version='1.0' encoding='UTF-8'?>
<ChangeLog itemType="entry" itemId="fiets-n-1" user="piek" timestamp="2026-06-11T14:32:01">
  <OldVersion>
    <LexicalEntry id="fiets-n-1" …>…</LexicalEntry>
  </OldVersion>
  <NewVersion>
    <LexicalEntry id="fiets-n-1" …>…</LexicalEntry>
  </NewVersion>
</ChangeLog>
```

These files can be used to review or revert individual changes.

---

## Collaborative editing

When `server.py` is running, all users who open `http://localhost:8080` share the same SQLite database. Changes are propagated in real time and each item is protected by a timed lock while it is being edited.

### Database backend

On first run, the server imports the XML file into a **SQLite database** (`.db` file alongside the XML). Subsequent runs load directly from the database — no re-parsing of the large XML. The database can be exported at any time via **Export XML** in the toolbar.

| File | Created automatically from |
|---|---|
| `data/odwn.db` | `data/odwn.xml` (first run only) |
| `data/wneng30_synset_synonyms.json` | Princeton WordNet 3.0 LMF file (run once separately) |

### Locking

Each entry and synset is protected by a per-item lock:

- When a user **opens** an item, the server acquires a lock for them (60-second TTL).
- Every **auto-save** (every 1.5 s after typing stops) **refreshes** the lock, extending it by another 60 s.
- If the user **switches away** or **closes the tab**, the lock is released immediately.
- If the user stops editing without closing (e.g. leaves the tab idle), the lock **expires automatically** after 60 seconds of no auto-saves.
- While an item is locked, **other users see it as read-only** with a yellow banner showing who holds the lock and how many seconds remain.
- Once the lock expires or is released, the next user to open the item acquires it.

### How it works

- On page load the editor calls `/api/status`. If the server responds, collaborative mode activates and the login form is shown.
- After login, the full entry/synset **index** (lightweight metadata) is fetched once from `/api/index`. Full entry data is fetched **lazily** from `/api/entry/<id>` when you click an entry — this keeps initial load fast even for 99 000-entry files and also acquires the lock.
- Every **1.5 seconds after you stop typing**, the current item is auto-saved via `POST /api/update`, which also refreshes the lock.
- Every **3 seconds**, the client polls `/api/changes?since=<seq>` for changes made by other users and applies them in place.
- A **heartbeat** is sent every 30 seconds to track active users.

### Collaborative UI

| Element | Meaning |
|---|---|
| Green dot + user count (toolbar) | Connected to server; shows number of active users |
| Username badge (toolbar) | The currently logged-in user |
| **Sign out** button (toolbar) | Logs out and reloads the page to the login screen |
| Yellow lock banner (editor top) | Item is locked by another user; shows who and countdown |
| **Claim when free** button | Re-attempts to acquire the lock (visible while locked by another) |
| Auto-save status (status bar, bottom right) | `Saving…` → `Saved` after each auto-save |
| Toast notification (bottom right) | Appears when another user edits, adds, or deletes an item |

### User accounts

Accounts are defined in **`users.json`** (created automatically alongside `server.py` on first run):

```json
{
  "alice": "mypassword",
  "bob":   "anotherpassword"
}
```

After editing `users.json`, **restart the server** — passwords are hashed with PBKDF2-SHA256 and written to the database on startup. Removing a user from the file removes them from the database on the next restart.

Users log in once per browser session (session token valid for 8 hours, stored in `localStorage`). Click **Sign out** in the toolbar to log out; the page reloads and the login form reappears.

### Server options

```
python3 server.py [xmlfile_or_dbfile] [port] [users.json]
```

| Argument | Default |
|---|---|
| `xmlfile` | `data/odwn_orbn_gwg-LMF_1.3.xml` (auto-discovered) |
| `dbfile` | Derived from XML path (e.g. `data/odwn.db`); also auto-discovered |
| `users.json` | `users.json` alongside `server.py` (created if absent) |
| `port` | `8080` |

If both an XML file and a `.db` file exist at the same path, the `.db` is used directly (no re-import). Pass the XML explicitly to force re-import.

The server loads data in a background thread so HTTP requests are served immediately. A progress message is shown while loading (`/api/status` reports `ready: false`).

### Lock TTL

The default lock TTL is 60 seconds. To change it, edit the `LOCK_TTL` constant at the top of `server.py`:

```python
LOCK_TTL = 60  # seconds
```

---

## XML format

The editor reads and writes the ODWN attribute-based LMF variant:

```xml
<?xml version='1.0' encoding='UTF-8'?>
<LexicalResource>
  <GlobalInformation label="ODWN-ORBN-LMF"/>
  <Lexicon languageCoding="ISO 639-2" label="ODWN-ORBN-LMF-1.3" language="nl" owner="VUA">

    <LexicalEntry id="fiets-n-1" partOfSpeech="noun">
      <Lemma writtenForm="fiets"/>
      <WordForms>
        <WordForm writtenForm="fietsen" grammaticalNumber="plural" article="de"/>
      </WordForms>
      <Morphology separability=""/>
      <MorphoSyntax pronominalAndGrammaticalGender="m">
        <auxiliaries auxiliary="hebben"/>
      </MorphoSyntax>
      <SyntacticBehaviour/>
      <Sense id="r_n-1" senseId="1" definition="two-wheeled pedal vehicle"
             synset="eng-30-02834778-n" provenance="cdb2.2_Auto" annotator="piek">
        <SenseRelations/>
        <Semantics-noun reference="common" countability="count" semanticType="artefact"/>
        <Pragmatics/>
      </Sense>
    </LexicalEntry>

    <Synset id="odwn-20-000000001-n" ili="" baseConcept="">
      <Definitions>
        <Definition gloss="two-wheeled pedal vehicle" language="nl" provenance=""/>
      </Definitions>
      <SynsetRelations>
        <SynsetRelation relType="has_hyperonym" target="odwn-n-5678" provenance=""/>
      </SynsetRelations>
    </Synset>

  </Lexicon>
</LexicalResource>
```

The editor also opens standard **feat-based** LMF files and detects the format automatically. Feat-based files are saved back in feat format; ODWN files are saved in attribute format.

---

## Data files

| File | Description |
|---|---|
| `data/odwn_orbn_gwg-LMF_1.3.xml` | Open Dutch WordNet (ODWN) combined with ORBN and GWG, LMF 1.3 format (~149 MB, ~99 000 entries, ~135 000 synsets) |
| `data/wneng30_synset_synonyms.json` | Princeton WordNet 3.0 synset→synonyms mapping (117 659 synsets), used for English synonym display and search |

---

## Project files

| File | Purpose |
|---|---|
| `index.html` | Complete single-file editor (HTML + CSS + JS, no build step) |
| `server.py` | Collaborative HTTP server (Python 3, stdlib only) |
| `users.json` | Username/password pairs (created on first server run) |
| `log/` | Per-save XML change logs (created automatically on first explicit save) |

---

## Requirements

- **Browser:** any modern browser (Chrome, Firefox, Safari, Edge)
- **Collaborative server:** Python 3.6+, no third-party packages
