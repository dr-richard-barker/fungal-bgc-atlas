"""build_graph.py — two knowledge graphs from the curated data.

1. relationship graph: the literal RELATIONSHIP table (subject_raw --
   predicate_raw --> object_raw), one edge per curated triple.
2. entity graph: BGC <-> organism <-> gene <-> metabolite <-> source,
   joined on dossier_id, for the dashboard's cross-table "connections" view.

Both are exported as GraphML + JSON node/edge lists + CSV edge lists.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.config import GRAPH_DIR, PROCESSED_DIR


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{name}.csv")


def _export(g: nx.Graph, stem: str) -> None:
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(g, GRAPH_DIR / f"{stem}.graphml")

    nodes = [{"id": n, **d} for n, d in g.nodes(data=True)]
    edges = [{"source": u, "target": v, **d} for u, v, d in g.edges(data=True)]
    with open(GRAPH_DIR / f"{stem}.json", "w") as fh:
        json.dump({"nodes": nodes, "edges": edges}, fh, indent=2, default=str)

    pd.DataFrame(nodes).to_csv(GRAPH_DIR / f"{stem}_nodes.csv", index=False)
    pd.DataFrame(edges).to_csv(GRAPH_DIR / f"{stem}_edges.csv", index=False)
    print(f"  {stem:<20} {g.number_of_nodes():>6,} nodes, {g.number_of_edges():>6,} edges")


def build_relationship_graph() -> nx.MultiDiGraph:
    rel = _read("relationship")
    g = nx.MultiDiGraph()
    for _, r in rel.iterrows():
        subj, pred, obj = r["subject_raw"], r["predicate_raw"], r["object_raw"]
        if pd.isna(subj) or pd.isna(pred) or pd.isna(obj):
            continue
        g.add_node(subj, kind="entity")
        g.add_node(obj, kind="entity")
        g.add_edge(subj, obj, predicate=pred, dossier_id=r["dossier_id"],
                   relationship_id=r["relationship_id"])
    return g


def build_entity_graph() -> nx.Graph:
    bgc = _read("bgc")
    organism = _read("organism").set_index("organism_key")
    gene = _read("gene")
    metabolite = _read("metabolite")
    source = _read("source")
    evidence = _read("evidence_link")

    g = nx.Graph()
    for _, b in bgc.iterrows():
        did = b["dossier_id"]
        g.add_node(did, kind="BGC", label=b["mibig_accession"], organism=b["organism_name"])
        ok = b["organism_key"]
        if pd.notna(ok):
            if ok not in g:
                oname = organism.loc[ok, "organism_name"] if ok in organism.index else b["organism_name"]
                g.add_node(ok, kind="ORGANISM", label=oname)
            g.add_edge(did, ok, relation="belongs_to")

    for _, gn in gene.iterrows():
        gk, did = gn["gene_key"], gn["dossier_id"]
        g.add_node(gk, kind="GENE", label=gn["gene_name"])
        g.add_edge(did, gk, relation="has_gene")

    for _, m in metabolite.iterrows():
        mk, did = m["metabolite_key"], m["dossier_id"]
        g.add_node(mk, kind="METABOLITE", label=m["name_raw"])
        g.add_edge(did, mk, relation="produces_metabolite")

    src_lookup = source.set_index(["dossier_id", "source_id"])["title_or_database_raw"].to_dict()
    for _, e in evidence.iterrows():
        rk, did, sid = e["record_key"], e["dossier_id"], e["source_id"]
        sk = f"{did}:{sid}"
        if sk not in g and (did, sid) in src_lookup:
            g.add_node(sk, kind="SOURCE", label=str(src_lookup[(did, sid)])[:80])
        if rk in g and sk in g:
            g.add_edge(rk, sk, relation="evidenced_by")

    return g


def main() -> None:
    print("Building relationship graph (subject-predicate-object triples)...")
    rel_graph = build_relationship_graph()
    _export(rel_graph, "relationship_graph")

    print("Building entity-linkage graph (BGC-organism-gene-metabolite-source)...")
    entity_graph = build_entity_graph()
    _export(entity_graph, "entity_graph")


if __name__ == "__main__":
    main()
