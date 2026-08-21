# Figure snapshot — 2026-08-21

**Corpus state at this snapshot:** 609 fungal BGC dossiers, 371 organisms
(phyla: Ascomycota, Basidiomycota, Mortierellomycota).

> This is a fixed point-in-time snapshot. The interactive dashboard
> (`docs/index.html`) re-derives every chart from the current data on each
> build; these files are the archived record for the manuscript.

## Files

| File | Figure |
|---|---|
| Fig1_taxonomy_top_genera | Top 15 genera by curated organism count |
| Fig2_bgc_class_distribution | Top 12 MIBiG-reported BGC classes |
| Fig3_publication_timeline | Publication timeline of primary references |
| Fig4_evidence_provenance | Top 10 source types in the evidence layer |
| Fig5_conflict_uncertainty_types | Top 12 preserved conflict/uncertainty issue types |
| Fig6_coverage_completeness | Evidence-coverage completeness per dossier |

Each figure is provided as 300-dpi PNG and vector SVG. All values are computed
directly from `data/processed/*.csv` by `scripts/make_figures.py` — see
`scripts/compute_stats.py` for the equivalent tabular source of truth.
