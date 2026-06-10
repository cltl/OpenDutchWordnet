# ODWN LMF Editor

A browser-based editor for lexical resources in [Lexical Markup Framework (LMF)](https://www.iso.org/standard/82429.html) format (ISO 24613). Built for the [Open Dutch WordNet (ODWN)](https://github.com/cltl/OpenDutchWordnet) / ORBN format, and conforming to the `odwn-orbn-lmf.dtd` schema. Also opens generic feat-based LMF files.

---

## Quick start

### Standalone (single user)

No installation required. Open the file directly in any modern browser:

```bash
open index.html
# or on Linux:
xdg-open index.html
```

Then use **Open XML** in the toolbar to load an LMF file, or click **Load ODWN** to load the bundled Dutch WordNet from `data/`.

> **Note:** The **Load ODWN** button uses `fetch()` and requires an HTTP server. Opening `index.html` via `file://` will block it. Use the instructions below or click **Open XML** and select the file manually.

### Local HTTP server (recommended)

Serves the editor and data file over HTTP so **Load ODWN** works and all features are available:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080` in your browser.

### Collaborative server (multi-user)

Allows multiple users to edit the same file simultaneously in real time:

```bash
python3 server.py
# with options:
python3 server.py data/odwn_orbn_gwg-LMF_1.3.xml 8080
```

Then open `http://localhost:8080` in each user's browser. The editor detects the server automatically and switches to collaborative mode.

---

## File operations

| Action | How |
|---|---|
| Open LMF XML file | Toolbar → **Open XML** |
| Load bundled ODWN file | Toolbar → **Load ODWN** (requires HTTP server) |
| Save as LMF XML | Toolbar → **Save XML**, or **Cmd/Ctrl+S** |
| Export as JSON | Toolbar → **Export JSON** |
| Create empty lexicon | Toolbar → **New** |
| Edit lexicon metadata | Toolbar → **Lexicon Settings** |

Large files (the ODWN file is ~149 MB, ~99 000 entries) show a loading overlay during parsing and serialisation.

---

## Browsing

The left sidebar has two tabs: **Entries** and **Synsets**.

- Each row shows the lemma (or MWE form) and part of speech.
- The list uses **virtual scrolling** — only the visible rows are rendered in the DOM, so 99 000-entry files scroll without lag.
- Type in the **search box** to filter by lemma, entry ID, or (for synsets) definition gloss in real time.
- The item count below the search box reflects the current filter.

---

## Editing entries

Click any entry in the sidebar to open it in the editor. Changes are collected from the form automatically when you switch entries or save.

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

Each entry can have one or more senses. Click **+ Add** to append a sense; click **Remove** on a sense block to delete it.

| Field | Description |
|---|---|
| Definition | Free-text gloss |
| Sense ID | Numeric or string identifier within the entry |
| Synset | Synset reference, e.g. `eng-30-06952861-n` |
| Provenance | Data source (`bing`, `google`, `opus`, `cdb2.2_Auto`, …) |
| Annotator | Name of the responsible annotator |

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

- **Duplicate** — copies the current entry and inserts it immediately after.
- **Delete** — removes the entry after confirmation.
- **+ Add Entry** (sidebar footer) — inserts a new blank entry at the top of the list.

---

## Editing synsets

Click the **Synsets** tab in the sidebar to browse and edit synsets.

### Synset Identity

| Field | Description |
|---|---|
| Synset ID | Unique identifier, e.g. `odwn-n-1234` |
| ILI | Interlingual Index reference |
| Base Concept | Base concept level |

### Definitions

Each synset can have multiple definitions with gloss, language code, and provenance.

### Synonyms

A **Synonyms** card lists all entries that have a sense pointing to this synset. Each entry shows its lemma and part of speech, with an **↗ Open** button that switches to the Entries panel and opens that entry directly.

In collaborative mode, only entries that have already been fetched from the server appear in this list. Opening an entry once is enough to index it.

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
| Click an **edge** | Toggles expand/collapse on the target node — first click reveals that node's own relations as additional nodes; second click hides them again |
| Click a **node** | Opens a small popup with two buttons |
| Popup → **Expand** | Reveals the node's further relations (same as clicking its outgoing edges) |
| Popup → **Collapse** | Hides the nodes added by expanding this node |
| Popup → **Make center** | Navigates to that synset, making it the new centre of the graph |
| **Reset** button (card header) | Collapses all expansions back to the default two-level view |
| Drag the background | Pans the graph |

Expanded nodes are highlighted with an orange ring. Clicking anywhere outside the popup dismisses it.

> In collaborative mode, level-2 and deeper synsets are only shown if their full data has already been fetched from the server (i.e. you have opened them at least once).

### Monolingual External Refs

Read-only display of external references (Princeton WordNet, etc.). Edit via raw XML if needed.

---

## Collaborative editing

When `server.py` is running, all users who open `http://localhost:8080` share the same in-memory lexicon. Changes are propagated automatically.

### How it works

- On page load the editor calls `/api/status`. If the server responds, collaborative mode activates.
- The full entry/synset **index** (~lightweight metadata) is fetched once from `/api/index`. Full entry data is fetched **lazily** from `/api/entry/<id>` when you click an entry — this keeps initial load fast even for 99 000-entry files.
- Every **1.5 seconds after you stop typing**, the current entry is auto-saved to the server via `POST /api/update`.
- Every **3 seconds**, the client polls `/api/changes?since=<seq>` for changes made by other users and applies them in place.
- **Save XML** (toolbar or Cmd/Ctrl+S) writes the server's in-memory state back to the XML file on disk via `POST /api/save`.
- A **heartbeat** is sent every 30 seconds to track active users.

### Collaborative UI

| Element | Meaning |
|---|---|
| Green dot + user count (toolbar) | Connected to server; shows number of active users |
| Auto-save status (status bar, bottom right) | `Saving…` → `Saved` after each auto-save |
| Toast notification (bottom right) | Appears when another user edits, adds, or deletes an item |

### Username

On first connect you are prompted for a username. It is stored in `localStorage` and reused in future sessions. To change it, clear `localStorage` in your browser's dev tools (`localStorage.removeItem('lmf_user')`).

### Server options

```
python3 server.py [xmlfile] [port]
```

| Argument | Default |
|---|---|
| `xmlfile` | `data/odwn_orbn_gwg-LMF_1.3.xml` (auto-discovered) |
| `port` | `8080` |

The server parses the XML in a background thread so HTTP requests are served immediately. A progress message is shown while loading (`/api/status` reports `ready: false`).

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
             synset="eng-30-02834778-n" provenance="cdb2.2_Auto" annotator="">
        <SenseRelations/>
        <Semantics-noun reference="common" countability="count" semanticType="artefact"/>
        <Pragmatics/>
      </Sense>
    </LexicalEntry>

    <Synset id="odwn-n-1234" ili="" baseConcept="">
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

## Data file

`data/odwn_orbn_gwg-LMF_1.3.xml` — the Open Dutch WordNet combined with ORBN and GWG, in ODWN LMF 1.3 format.

| Stat | Value |
|---|---|
| File size | ~149 MB |
| LexicalEntry elements | 99 349 |
| Synset elements | 135 653 |
| Lines | ~3.2 million |

Parsing this file in the browser takes several seconds; a loading overlay is shown. Via the collaborative server, parsing happens once in the background and all clients share the result.

---

## Project files

| File | Purpose |
|---|---|
| `index.html` | Complete single-file editor (HTML + CSS + JS, no build step) |
| `server.py` | Collaborative HTTP server (Python 3, stdlib only) |
| `data/odwn_orbn_gwg-LMF_1.3.xml` | Bundled ODWN data file |

---

## Requirements

- **Browser:** any modern browser (Chrome, Firefox, Safari, Edge)
- **Collaborative server:** Python 3.6+, no third-party packages
