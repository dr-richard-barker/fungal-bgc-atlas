"""compute_stats.py — every descriptive number used in the manuscript and dashboard.

Every CSV/JSON written here is computed directly from data/processed/*.csv
(itself parsed straight from the source workbook) — nothing is invented.
Also emits a LaTeX \\input-able .tex snippet per manuscript table.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.config import EXPECTED_COUNTS, PROCESSED_DIR, TABLES_DIR, SUPPLEMENTARY_DIR


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{name}.csv")


def _write_table(df: pd.DataFrame, stem: str, caption: str, label: str) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES_DIR / f"{stem}.csv", index=False)

    cols = " ".join(["l"] * len(df.columns))
    header = " & ".join(str(c).replace("_", "\\_") for c in df.columns) + r" \\"
    body_lines = []
    for _, row in df.iterrows():
        cells = " & ".join(str(v).replace("_", "\\_").replace("%", "\\%") for v in row)
        body_lines.append(cells + r" \\")
    tex = "\n".join([
        r"\begin{table}[htbp]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabular}}{{{cols}}}",
        r"\toprule",
        header,
        r"\midrule",
        *body_lines,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    (TABLES_DIR / f"{stem}.tex").write_text(tex)
    print(f"  {stem:<28} {len(df):>4} rows -> tables/{stem}.csv + .tex")


def summary_metrics() -> pd.DataFrame:
    bgc, organism, strain = _read("bgc"), _read("organism"), _read("strain")
    rows = [
        ("BGC dossiers", len(bgc), "All linked to MIBiG accessions"),
        ("Unique organisms", len(organism), f"{organism['phylum'].nunique()} phyla, {organism['genus'].nunique()} genera"),
        ("Strain labels", len(strain), ""),
        ("Genes", EXPECTED_COUNTS["GENE"], ""),
        ("Metabolites", EXPECTED_COUNTS["METABOLITE"], ""),
        ("Experiments", EXPECTED_COUNTS["EXPERIMENT"], ""),
        ("Measurements", EXPECTED_COUNTS["MEASUREMENT"], ""),
        ("Claims", EXPECTED_COUNTS["CLAIM"], ""),
        ("Relationships (KG triples)", EXPECTED_COUNTS["RELATIONSHIP"], ""),
        ("Conflicts / uncertainties", EXPECTED_COUNTS["CONFLICT"], "preserved, not collapsed"),
        ("Sources", EXPECTED_COUNTS["SOURCE"], ""),
        ("Evidence links", EXPECTED_COUNTS["EVIDENCE_LINK"], "record <-> source provenance"),
        ("Publication span", f"{int(bgc['primary_reference_year'].min())}-{int(bgc['primary_reference_year'].max())}", ""),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value", "Notes"])


def top_taxa(n: int = 15) -> pd.DataFrame:
    """Groups by organism_key, not organism_name: a handful of distinct
    organism_keys (different NCBI taxon IDs, e.g. two records both labelled
    "Aspergillus nidulans") share the same display name in the curated data.
    They are kept as separate rows (with their taxon ID) rather than summed,
    since collapsing them would silently resolve a taxonomic ambiguity the
    curation preserved on purpose."""
    organism = _read("organism").set_index("organism_key")
    bgc = _read("bgc")
    counts = bgc.groupby("organism_key").size().rename("bgc_count")
    df = counts.to_frame().join(organism[["organism_name", "ncbi_taxon_id", "genus"]], how="left").reset_index()
    df = df[["organism_name", "bgc_count", "ncbi_taxon_id", "genus"]]
    df.columns = ["Organism", "BGC count", "NCBI taxon ID", "Genus"]
    return df.sort_values("BGC count", ascending=False).head(n).reset_index(drop=True)


def phylum_genus_breakdown() -> pd.DataFrame:
    organism = _read("organism")
    df = organism.groupby(["phylum", "genus"]).size().rename("organisms").reset_index()
    return df.sort_values(["phylum", "organisms"], ascending=[True, False])


def bgc_class_distribution(n: int = 20) -> pd.DataFrame:
    bgc = _read("bgc")
    vc = bgc["mibig_bgc_class_raw"].value_counts().head(n).reset_index()
    vc.columns = ["BGC class (MIBiG, raw)", "Count"]
    return vc


def facet_axis_summary() -> pd.DataFrame:
    facet = _read("bgc_facet")
    df = facet.groupby("facet_axis").agg(
        rows=("dossier_id", "count"),
        distinct_bgcs=("dossier_id", "nunique"),
    ).reset_index().sort_values("rows", ascending=False)
    df.columns = ["Facet axis", "Rows", "Distinct BGCs"]
    return df


def conflict_type_breakdown(n: int = 20) -> pd.DataFrame:
    conflict = _read("conflict")
    vc = conflict["issue_type_raw"].value_counts().head(n).reset_index()
    vc.columns = ["Conflict issue type", "Count"]
    return vc


def conflict_status_breakdown() -> pd.DataFrame:
    conflict = _read("conflict")
    vc = conflict["status_raw"].value_counts().reset_index()
    vc.columns = ["Status", "Count"]
    return vc


def publication_year_timeline() -> pd.DataFrame:
    bgc = _read("bgc")
    df = bgc.groupby("primary_reference_year").size().rename("bgc_count").reset_index()
    df.columns = ["Year", "BGC count"]
    return df.sort_values("Year")


def coverage_summary() -> pd.DataFrame:
    coverage = _read("coverage")
    cols = ["facets", "genes", "metabolites", "experiments", "measurements", "claims", "relationships", "conflicts", "sources"]
    desc = coverage[cols].describe().T.reset_index()
    desc.columns = ["Field", "count", "mean", "std", "min", "25%", "50%", "75%", "max"]
    return desc.round(2)


def source_type_breakdown(n: int = 20) -> pd.DataFrame:
    source = _read("source")
    vc = source["source_type_raw"].value_counts().head(n).reset_index()
    vc.columns = ["Source type (raw)", "Count"]
    return vc


def relationship_predicate_breakdown(n: int = 25) -> pd.DataFrame:
    rel = _read("relationship")
    vc = rel["predicate_raw"].value_counts().head(n).reset_index()
    vc.columns = ["Predicate", "Count"]
    return vc


def normalization_status() -> pd.DataFrame:
    """Bucket by the category prefix (text before ':'), since the raw column is
    mostly free-text reason strings (e.g. "unresolved_composite: combines ...")
    rather than a small fixed vocabulary."""
    term = _read("term")
    status = term["normalization_status"].fillna("(blank)").astype(str)
    category = status.str.split(":", n=1).str[0].str.strip()
    vc = category.value_counts().reset_index()
    vc.columns = ["Normalization status category", "TERM rows"]
    return vc


def dossier_index() -> pd.DataFrame:
    bgc = _read("bgc")
    coverage = _read("coverage").set_index("dossier_id")
    cols = ["dossier_id", "mibig_accession", "organism_name", "primary_product_raw",
            "mibig_bgc_class_raw", "primary_reference_year", "primary_reference_doi"]
    df = bgc[cols].copy()
    for c in ["genes", "metabolites", "experiments", "claims", "conflicts"]:
        df[c] = df["dossier_id"].map(coverage[c])
    return df.sort_values("dossier_id")


def source_bibliography() -> pd.DataFrame:
    source = _read("source")
    cols = ["dossier_id", "source_id", "source_type_raw", "year_raw",
            "title_or_database_raw", "doi_or_accession_raw", "pmid_raw", "url_raw"]
    return source[cols].sort_values(["dossier_id", "source_id"])


def main() -> None:
    print("Computing manuscript/dashboard statistics from data/processed/ ...")
    _write_table(summary_metrics(), "table1_summary_metrics",
                 "Fungal BGC Atlas: resource summary metrics.", "tab:summary")
    _write_table(top_taxa(), "table2_top_taxa",
                 "The 15 organisms with the most curated BGC dossiers.", "tab:toptaxa")
    _write_table(bgc_class_distribution(), "table3_bgc_class_distribution",
                 "Distribution of MIBiG-reported BGC classes across the 609 dossiers.", "tab:bgcclass")
    _write_table(conflict_type_breakdown(), "table4_conflict_types",
                 "Conflict/uncertainty issue types preserved in the resource.", "tab:conflicts")

    SUPPLEMENTARY_DIR.mkdir(parents=True, exist_ok=True)
    supp = {
        "supp_table1_dossier_index": dossier_index(),
        "supp_table2_facet_axis_reference": facet_axis_summary(),
        "supp_table3_phylum_genus_breakdown": phylum_genus_breakdown(),
        "supp_table4_publication_year_timeline": publication_year_timeline(),
        "supp_table5_coverage_summary": coverage_summary(),
        "supp_table6_source_type_breakdown": source_type_breakdown(),
        "supp_table7_relationship_predicates": relationship_predicate_breakdown(),
        "supp_table8_normalization_status": normalization_status(),
        "supp_table9_conflict_status": conflict_status_breakdown(),
        "supp_table10_source_bibliography": source_bibliography(),
    }
    for stem, df in supp.items():
        df.to_csv(SUPPLEMENTARY_DIR / f"{stem}.csv", index=False)
        print(f"  {stem:<38} {len(df):>6} rows -> supplementary/{stem}.csv")


if __name__ == "__main__":
    main()
