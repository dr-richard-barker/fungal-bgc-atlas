"""make_figures.py — dated snapshot figures (300 dpi PNG + vector SVG) + MANIFEST.md.

Figures are static exports (matplotlib) of the same real, computed
statistics that feed the interactive dashboard and the manuscript tables —
a fixed point-in-time record, while the dashboard always re-derives from
the current build. See figures/<date>/MANIFEST.md for the rationale.
"""
from __future__ import annotations
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.config import FIGURES_ROOT, PROCESSED_DIR, SNAPSHOT_LABEL

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 300,
})
PALETTE = ["#2c5f6f", "#7fb069", "#e8a33d", "#c1666b", "#4a5859", "#8ecae6", "#bc6c25"]


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{name}.csv")


def _save(fig, out_dir: Path, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(out_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(out_dir / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"  {stem}")


def fig1_taxonomy(out_dir: Path) -> None:
    organism = _read("organism")
    top_genus = organism["genus"].value_counts().head(15).sort_values()
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.barh(top_genus.index, top_genus.values, color=PALETTE[0])
    ax.set_xlabel("Number of organisms")
    ax.set_title("Top 15 genera by number of curated organisms")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    _save(fig, out_dir, "Fig1_taxonomy_top_genera")


def fig2_bgc_class(out_dir: Path) -> None:
    bgc = _read("bgc")
    vc = bgc["mibig_bgc_class_raw"].value_counts().head(12).sort_values()
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.barh(vc.index, vc.values, color=PALETTE[1])
    ax.set_xlabel("Number of BGC dossiers")
    ax.set_title("Top 12 MIBiG-reported BGC classes (raw)")
    _save(fig, out_dir, "Fig2_bgc_class_distribution")


def fig3_publication_timeline(out_dir: Path) -> None:
    bgc = _read("bgc")
    counts = bgc.groupby("primary_reference_year").size()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(counts.index, counts.values, color=PALETTE[2], width=0.8)
    ax.set_xlabel("Primary reference year")
    ax.set_ylabel("Number of BGC dossiers")
    ax.set_title(f"Publication timeline of primary references ({int(counts.index.min())}-{int(counts.index.max())})")
    _save(fig, out_dir, "Fig3_publication_timeline")


def fig4_evidence_provenance(out_dir: Path) -> None:
    source = _read("source")
    vc = source["source_type_raw"].value_counts().head(10).sort_values()
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.barh(vc.index, vc.values, color=PALETTE[3])
    ax.set_xlabel("Number of source records")
    ax.set_title("Top 10 source types underpinning the evidence layer")
    _save(fig, out_dir, "Fig4_evidence_provenance")


def fig5_conflicts(out_dir: Path) -> None:
    conflict = _read("conflict")
    vc = conflict["issue_type_raw"].value_counts().head(12).sort_values()
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.barh(vc.index, vc.values, color=PALETTE[4])
    ax.set_xlabel("Number of conflict/uncertainty records")
    ax.set_title("Top 12 preserved conflict/uncertainty issue types")
    _save(fig, out_dir, "Fig5_conflict_uncertainty_types")


def fig6_coverage(out_dir: Path) -> None:
    coverage = _read("coverage")
    cols = ["genes", "metabolites", "experiments", "claims", "relationships", "conflicts"]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.boxplot([coverage[c] for c in cols], tick_labels=cols, showfliers=False,
               patch_artist=True, boxprops=dict(facecolor=PALETTE[5], alpha=0.6))
    ax.set_ylabel("Records per BGC dossier")
    ax.set_title("Evidence-coverage completeness across the 609 dossiers")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    _save(fig, out_dir, "Fig6_coverage_completeness")


def write_manifest(out_dir: Path) -> None:
    bgc = _read("bgc")
    organism = _read("organism")
    text = f"""# Figure snapshot — {SNAPSHOT_LABEL}

**Corpus state at this snapshot:** {len(bgc)} fungal BGC dossiers, {len(organism)} organisms
(phyla: {', '.join(sorted(organism['phylum'].dropna().unique()))}).

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
"""
    (out_dir / "MANIFEST.md").write_text(text)
    print(f"  MANIFEST.md -> {out_dir}")


def main() -> None:
    out_dir = FIGURES_ROOT / SNAPSHOT_LABEL
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Rendering figures -> figures/{SNAPSHOT_LABEL}/")
    fig1_taxonomy(out_dir)
    fig2_bgc_class(out_dir)
    fig3_publication_timeline(out_dir)
    fig4_evidence_provenance(out_dir)
    fig5_conflicts(out_dir)
    fig6_coverage(out_dir)
    write_manifest(out_dir)


if __name__ == "__main__":
    main()
