"""run_all.py — deterministic build orchestrator.

parse -> database -> graph -> stats/tables -> figures -> dashboard.

Run from the repository root: `python run_all.py`
"""
from __future__ import annotations
import time

from scripts import parse_xlsx, build_database, build_graph, compute_stats, make_figures, build_dashboard


def main() -> None:
    t0 = time.time()

    print("\n[1/6] Parsing source workbook...")
    parse_xlsx.parse_workbook()

    print("\n[2/6] Building relational database...")
    build_database.build_database()

    print("\n[3/6] Building knowledge/entity graphs...")
    build_graph.main()

    print("\n[4/6] Computing manuscript/dashboard statistics...")
    compute_stats.main()

    print("\n[5/6] Rendering figures...")
    make_figures.main()

    print("\n[6/6] Building interactive dashboard...")
    build_dashboard.build_dashboard()

    print(f"\nDone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
