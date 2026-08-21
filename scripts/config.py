"""config.py — shared paths and cross-check constants for the build pipeline.

The EXPECTED_COUNTS block mirrors the SUMMARY sheet of the source workbook
verbatim; build_database.py asserts against it so a parsing regression is
caught immediately rather than silently drifting from the real numbers.
"""
from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RAW_XLSX = REPO_ROOT / "data" / "raw" / "Fungal_BGC_Atlas_609_2026-08-21.xlsx"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DB_PATH = REPO_ROOT / "data" / "db" / "fungal_bgc_atlas.db"
SCHEMA_SQL = REPO_ROOT / "db" / "schema.sql"
GRAPH_DIR = REPO_ROOT / "data" / "graph"
TABLES_DIR = REPO_ROOT / "tables"
SUPPLEMENTARY_DIR = REPO_ROOT / "supplementary"
FIGURES_ROOT = REPO_ROOT / "figures"
DOCS_DIR = REPO_ROOT / "docs"

# Data tables (one CSV each) vs. documentation sheets (captured as text, not loaded to DB).
DATA_SHEETS = [
    "BGC", "ORGANISM", "STRAIN", "BGC_FACET", "GENE", "METABOLITE", "EXPERIMENT",
    "TERM", "EXPERIMENT_LINK", "MEASUREMENT", "OBSERVATION", "CLAIM", "RELATIONSHIP",
    "CONFLICT", "SOURCE", "EVIDENCE_LINK", "ASSERTION", "COMPACT_FACT", "COVERAGE",
    "DOSSIER_SCHEMA", "NORMALIZATION_QUEUE", "PROVENANCE_EXCLUDED", "RAW_ROW",
]
DOC_SHEETS = ["SUMMARY", "README", "SCHEMA", "FEATURE_POLICY", "VIEW_SPEC"]

# Verbatim from the workbook's SUMMARY sheet (21 August 2026, 18:10 IST snapshot).
EXPECTED_COUNTS = {
    "BGC": 609,
    "ORGANISM": 371,
    "STRAIN": 1018,
    "BGC_FACET": 7800,
    "GENE": 1572,
    "METABOLITE": 807,
    "EXPERIMENT": 915,
    "EXPERIMENT_LINK": 4707,
    "MEASUREMENT": 936,
    "OBSERVATION": 1641,
    "CLAIM": 1534,
    "RELATIONSHIP": 1264,
    "CONFLICT": 995,
    "SOURCE": 2575,
    "EVIDENCE_LINK": 47768,
    "ASSERTION": 24502,
    "COMPACT_FACT": 813,
    "TERM": 3042,
    "NORMALIZATION_QUEUE": 882,
    "RAW_ROW": 30851,
}

SNAPSHOT_LABEL = "2026-08-21"
