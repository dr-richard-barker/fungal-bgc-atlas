# Fungal BGC Atlas 🍄🧬

### A curated, evidence-linked knowledge base of 609 fungal biosynthetic gene cluster dossiers

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-blue.svg)](LICENSE)
[![Reproducible](https://img.shields.io/badge/build-deterministic-success)](run_all.py)
[![Data: MIBiG-linked](https://img.shields.io/badge/data-MIBiG--linked-0b3d64)](https://mibig.secondarymetabolites.org)
[![Status](https://img.shields.io/badge/status-v0.1.0%20snapshot-orange)]()

> Resolves 609 MIBiG-linked fungal biosynthetic gene cluster (BGC) dossiers into genes, metabolites,
> experiments, measurements, claims and curated relationships, all traceable to their sources — with
> disagreements preserved, not collapsed. Packaged as a relational **database**, a **knowledge
> graph**, and a self-contained interactive **dashboard**, archived for **Zenodo** and accompanied by
> a manuscript prepared for the journal *Database* (Oxford Academic).

**Live dashboard:** https://dr-richard-barker.github.io/fungal-bgc-atlas/

---

## What this is

Fungal biosynthetic gene clusters are individually well described in MIBiG, but the *evidence* behind
each record — which gene was actually shown to matter, which metabolite was directly detected, under
what conditions, and whether independent studies agree — lives only in the cited literature. This
project turns 609 such dossiers into structured, queryable data: every gene, metabolite, experiment,
measurement, claim and relationship is linked back to a source record, uncertain or conflicting
evidence is kept as an explicit record rather than silently resolved, and the whole resource is
rebuildable from the original source workbook by a single command.

## Repository layout

| Path | Contents |
|---|---|
| [`scripts/`](scripts) | All build code: `parse_xlsx.py`, `build_database.py`, `build_graph.py`, `compute_stats.py`, `make_figures.py`, `build_dashboard.py` |
| [`run_all.py`](run_all.py) | Orchestrator — runs the full pipeline end to end |
| [`db/schema.sql`](db/schema.sql) | Documented relational schema (23 tables) |
| [`data/`](data) | `raw/` (source workbook), `processed/` (per-table CSVs), `db/` (SQLite), `graph/` (GraphML/JSON/CSV) |
| [`figures/`](figures) | Dated, publication-quality figure snapshots (300dpi PNG + SVG) with a manifest |
| [`tables/`](tables) | Manuscript tables (CSV + LaTeX-ready `.tex` snippets) |
| [`supplementary/`](supplementary) | Full dossier index, facet-axis reference, source bibliography, and more |
| [`manuscript/latex/`](manuscript/latex) | LaTeX manuscript, styled for the journal *Database* (Oxford Academic) |
| [`docs/`](docs) | GitHub Pages dashboard (built by CI — not hand-edited) |

## Reproducing the build

```bash
pip install -r requirements.txt
python run_all.py
```

This parses the source workbook, rebuilds the SQLite database and knowledge graph, recomputes every
statistic used in the manuscript and dashboard, re-renders the dated figure snapshot, and rebuilds
`docs/index.html`. Row counts are asserted against the source workbook's own summary at build time,
so a parsing regression fails loudly rather than silently drifting from the real data.

## Dashboard panels

Overview · Taxonomy Explorer · Chemistry & Biosynthesis · Facet Explorer (27 axes) · Knowledge Graph
(994 curated subject-predicate-object relationships) · Evidence & Provenance · Conflicts &
Uncertainty · Dossier Browser (searchable, with a full cross-table detail view per BGC) · Data
Dictionary (rendered from the source workbook's own schema documentation).

## Data curation

Each dossier was built by Claude (Anthropic) LLM-assisted extraction from the primary literature and
MIBiG, followed by full manual review of all 609 dossiers. See
[`manuscript/latex/sections/methods.tex`](manuscript/latex/sections/methods.tex) for details.

## License & citation

Released under [CC-BY-4.0](LICENSE). See [`CITATION.cff`](CITATION.cff) and
[`.zenodo.json`](.zenodo.json). Every dossier is anchored to a MIBiG accession — please also cite the
relevant MIBiG accessions and primary literature (see
[`supplementary/supp_table10_source_bibliography.csv`](supplementary/supp_table10_source_bibliography.csv))
when reusing the integrated data.
