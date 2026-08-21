"""build_dashboard.py — render docs/index.html, the interactive Pages dashboard.

Nine panels: Overview, Taxonomy, Chemistry & Biosynthesis, Facet Explorer,
Knowledge Graph, Evidence & Provenance, Conflicts & Uncertainty, Dossier
Browser (with cross-table detail view), and Data Dictionary. Plotly charts
are loaded from CDN (same convention as the sibling osdr-plant-microbiome
report); the dossier browser and facet explorer are plain vanilla JS reading
JSON files written alongside index.html — no other external dependency.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.io import to_html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import __version__
from scripts.config import DOCS_DIR, GRAPH_DIR, PROCESSED_DIR, SNAPSHOT_LABEL

TEMPLATE = "plotly_white"
PALETTE = px.colors.qualitative.Safe


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{name}.csv")


def _fig_html(fig: go.Figure, div_id: str) -> str:
    fig.update_layout(template=TEMPLATE, margin=dict(l=40, r=20, t=50, b=40),
                       font=dict(family="Inter, Segoe UI, sans-serif", size=12))
    return to_html(fig, include_plotlyjs=False, full_html=False,
                   div_id=div_id, config={"displaylogo": False, "responsive": True})


# ---------------------------------------------------------------- Overview
def panel_overview(d: dict) -> str:
    bgc, organism = d["bgc"], d["organism"]
    cards = [
        ("BGC dossiers", f"{len(bgc):,}", "all MIBiG-linked"),
        ("Organisms", f"{len(organism):,}", f"{organism['genus'].nunique()} genera"),
        ("Genes", f"{len(d['gene']):,}", ""),
        ("Metabolites", f"{len(d['metabolite']):,}", ""),
        ("Claims", f"{len(d['claim']):,}", ""),
        ("Relationships", f"{len(d['relationship']):,}", "knowledge-graph triples"),
        ("Conflicts", f"{len(d['conflict']):,}", "preserved, not collapsed"),
        ("Sources", f"{len(d['source']):,}", f"{len(d['evidence_link']):,} evidence links"),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="card-value">{v}</div>'
        f'<div class="card-label">{label}</div>'
        f'<div class="card-note">{note}</div></div>'
        for label, v, note in cards
    )

    cov = d["coverage"]
    cov_cols = ["genes", "metabolites", "experiments", "measurements", "claims", "relationships", "conflicts"]
    fig = go.Figure()
    for c in cov_cols:
        fig.add_trace(go.Box(y=cov[c], name=c, boxpoints=False, marker_color=PALETTE[0]))
    fig.update_layout(title="Evidence-coverage completeness per dossier", showlegend=False,
                       yaxis_title="records per dossier")

    return f"""
    <section id="overview" class="panel">
      <h2>Overview</h2>
      <p class="lede">A curated, evidence-linked knowledge base of {len(bgc)} fungal biosynthetic gene
      cluster (BGC) dossiers, each anchored to a MIBiG accession and built from primary literature with
      full source provenance. Snapshot: {SNAPSHOT_LABEL}.</p>
      <div class="card-grid">{cards_html}</div>
      <div class="chart-box">{_fig_html(fig, "overview-coverage")}</div>
    </section>"""


# ---------------------------------------------------------------- Taxonomy
def panel_taxonomy(d: dict) -> str:
    organism = d["organism"]
    tax = organism.fillna({"phylum": "Unclassified", "class": "Unclassified", "order": "Unclassified",
                            "genus": "Unclassified"})
    fig = px.sunburst(tax, path=["phylum", "class", "order", "genus"],
                       color="phylum", color_discrete_sequence=PALETTE,
                       title="Taxonomic composition of curated organisms (phylum → class → order → genus)")
    fig.update_traces(textinfo="label+value")

    bgc_by_genus = d["bgc"].merge(organism[["organism_key", "genus"]], on="organism_key", how="left")
    top = bgc_by_genus["genus"].value_counts().head(20).sort_values()
    fig2 = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=PALETTE[1]))
    fig2.update_layout(title="Top 20 genera by number of BGC dossiers", xaxis_title="BGC dossiers")

    return f"""
    <section id="taxonomy" class="panel">
      <h2>Taxonomy Explorer</h2>
      <div class="chart-box">{_fig_html(fig, "tax-sunburst")}</div>
      <div class="chart-box">{_fig_html(fig2, "tax-genus-bar")}</div>
    </section>"""


# --------------------------------------------------------- Chemistry/Biosynthesis
def panel_chemistry(d: dict) -> str:
    bgc = d["bgc"]
    fields = {
        "MIBiG BGC class": "mibig_bgc_class_raw",
        "Chemical class": "chemical_class_raw",
        "Product family": "product_family_raw",
        "Biological role": "biological_role_raw",
    }
    fig = go.Figure()
    buttons = []
    for i, (label, col) in enumerate(fields.items()):
        vc = bgc[col].value_counts().head(15).sort_values()
        fig.add_trace(go.Bar(x=vc.values, y=vc.index, orientation="h",
                              marker_color=PALETTE[i % len(PALETTE)], visible=(i == 0)))
        vis = [j == i for j in range(len(fields))]
        buttons.append(dict(label=label, method="update", args=[{"visible": vis}, {"title": f"Top 15: {label}"}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, x=1.0, xanchor="right", y=1.15)],
        title=f"Top 15: {list(fields.keys())[0]}", height=520,
    )
    return f"""
    <section id="chemistry" class="panel">
      <h2>Chemistry &amp; Biosynthesis</h2>
      <p class="lede">Use the dropdown to switch between the four independent categorical descriptors
      MIBiG/curation reports for each BGC.</p>
      <div class="chart-box">{_fig_html(fig, "chem-bar")}</div>
    </section>"""


# ---------------------------------------------------------------- Facet explorer
def panel_facets(d: dict) -> str:
    facet = d["bgc_facet"]
    axes = sorted(facet["facet_axis"].unique())
    facet_by_axis = {
        axis: facet.loc[facet["facet_axis"] == axis, ["dossier_id", "raw_value"]]
        .rename(columns={"raw_value": "value"}).fillna("(missing)").to_dict("records")
        for axis in axes
    }
    (DOCS_DIR / "data").mkdir(parents=True, exist_ok=True)
    with open(DOCS_DIR / "data" / "bgc_facets.json", "w") as fh:
        json.dump(facet_by_axis, fh)

    options = "".join(f'<option value="{a}">{a}</option>' for a in axes)
    return f"""
    <section id="facets" class="panel">
      <h2>Facet Explorer</h2>
      <p class="lede">609 BGCs are independently categorised along 27 facet axes (biosynthesis, chemistry,
      ecology, activation conditions, genome context). Pick an axis to see its value distribution and the
      matching dossiers.</p>
      <div class="facet-controls">
        <label for="facet-axis-select">Facet axis:</label>
        <select id="facet-axis-select">{options}</select>
      </div>
      <div id="facet-value-chart" class="chart-box"></div>
      <div id="facet-dossier-list" class="scroll-list"></div>
    </section>"""


# ---------------------------------------------------------------- Knowledge graph
def panel_graph(d: dict) -> str:
    with open(GRAPH_DIR / "relationship_graph.json") as fh:
        gdata = json.load(fh)
    g = nx.MultiDiGraph()
    for n in gdata["nodes"]:
        g.add_node(n["id"])
    for e in gdata["edges"]:
        g.add_edge(e["source"], e["target"], predicate=e.get("predicate", ""))

    pos = nx.spring_layout(g, seed=767, k=0.6 / max(np.sqrt(g.number_of_nodes()), 1), iterations=50)

    pred_counts = pd.Series([e.get("predicate", "") for e in gdata["edges"]]).value_counts()
    top_predicates = list(pred_counts.head(14).index)

    fig = go.Figure()
    for i, pred in enumerate(top_predicates + ["other"]):
        xs, ys = [], []
        for u, v, dat in g.edges(data=True):
            p = dat.get("predicate", "")
            match = (p == pred) if pred != "other" else (p not in top_predicates)
            if not match:
                continue
            x0, y0 = pos[u]; x1, y1 = pos[v]
            xs += [x0, x1, None]
            ys += [y0, y1, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=pred,
                                  line=dict(width=1, color=PALETTE[i % len(PALETTE)]),
                                  opacity=0.6, hoverinfo="none"))

    node_x = [pos[n][0] for n in g.nodes()]
    node_y = [pos[n][1] for n in g.nodes()]
    degrees = [g.degree(n) for n in g.nodes()]
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers", name="entities",
        marker=dict(size=[6 + 2 * min(deg, 8) for deg in degrees], color="#2c5f6f", line=dict(width=0.5, color="white")),
        text=[f"{n} (degree {g.degree(n)})" for n in g.nodes()], hoverinfo="text",
    ))
    fig.update_layout(
        title=f"Knowledge graph: {g.number_of_nodes():,} entities, {g.number_of_edges():,} predicate-labelled relationships<br>"
              f"<sup>Toggle predicates in the legend</sup>",
        xaxis=dict(visible=False), yaxis=dict(visible=False), height=650,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    )
    return f"""
    <section id="graph" class="panel">
      <h2>Knowledge Graph</h2>
      <p class="lede">Every RELATIONSHIP row is a curated subject&ndash;predicate&ndash;object triple
      (e.g. gene <em>encoded_by</em> protein, cluster <em>produces</em> metabolite). Click a predicate in
      the legend to isolate it.</p>
      <div class="chart-box">{_fig_html(fig, "kg-graph")}</div>
    </section>"""


# ---------------------------------------------------------------- Evidence & provenance
def panel_evidence(d: dict) -> str:
    source = d["source"]
    vc = source["source_type_raw"].value_counts().head(12).sort_values()
    fig1 = go.Figure(go.Bar(x=vc.values, y=vc.index, orientation="h", marker_color=PALETTE[2]))
    fig1.update_layout(title="Top 12 source types", xaxis_title="source records")

    bgc = d["bgc"]
    yr = bgc.groupby("primary_reference_year").size().reset_index(name="count")
    fig2 = go.Figure(go.Bar(x=yr["primary_reference_year"], y=yr["count"], marker_color=PALETTE[3]))
    fig2.update_layout(title="Publication timeline of primary references",
                        xaxis_title="year", yaxis_title="BGC dossiers")

    ev = d["evidence_link"]
    per_dossier = ev.groupby("dossier_id").size()
    fig3 = go.Figure(go.Histogram(x=per_dossier.values, marker_color=PALETTE[4], nbinsx=30))
    fig3.update_layout(title="Evidence links per dossier", xaxis_title="evidence links", yaxis_title="dossiers")

    return f"""
    <section id="evidence" class="panel">
      <h2>Evidence &amp; Provenance</h2>
      <div class="chart-box">{_fig_html(fig1, "ev-sourcetype")}</div>
      <div class="chart-box">{_fig_html(fig2, "ev-timeline")}</div>
      <div class="chart-box">{_fig_html(fig3, "ev-density")}</div>
    </section>"""


# ---------------------------------------------------------------- Conflicts
def panel_conflicts(d: dict) -> str:
    conflict = d["conflict"]
    vc = conflict["issue_type_raw"].value_counts().head(15).sort_values()
    fig1 = go.Figure(go.Bar(x=vc.values, y=vc.index, orientation="h", marker_color=PALETTE[5]))
    fig1.update_layout(title="Top 15 conflict / uncertainty issue types", xaxis_title="conflict records")

    status = conflict["status_raw"].value_counts().head(10)
    fig2 = go.Figure(go.Pie(labels=status.index, values=status.values, hole=0.45,
                             marker_colors=PALETTE))
    fig2.update_layout(title="Conflict resolution status")

    return f"""
    <section id="conflicts" class="panel">
      <h2>Conflicts &amp; Uncertainty</h2>
      <p class="lede">Disagreements between sources, boundary ambiguities and unresolved causal questions
      are recorded as first-class CONFLICT rows rather than silently collapsed into a single consensus
      value — by design.</p>
      <div class="chart-box">{_fig_html(fig1, "cf-types")}</div>
      <div class="chart-box">{_fig_html(fig2, "cf-status")}</div>
    </section>"""


# ---------------------------------------------------------------- Dossier browser
def panel_browser(d: dict) -> str:
    bgc, coverage = d["bgc"], d["coverage"].set_index("dossier_id")
    def _clean(v):
        return None if pd.isna(v) else v

    index_rows = []
    for _, b in bgc.iterrows():
        did = b["dossier_id"]
        index_rows.append({
            "dossier_id": did,
            "mibig_accession": _clean(b["mibig_accession"]),
            "organism": _clean(b["organism_name"]),
            "product": _clean(b["primary_product_raw"]),
            "bgc_class": _clean(b["mibig_bgc_class_raw"]),
            "year": None if pd.isna(b["primary_reference_year"]) else int(b["primary_reference_year"]),
            "genes": int(coverage.loc[did, "genes"]) if did in coverage.index else 0,
            "metabolites": int(coverage.loc[did, "metabolites"]) if did in coverage.index else 0,
            "conflicts": int(coverage.loc[did, "conflicts"]) if did in coverage.index else 0,
        })

    details: dict[str, dict] = {}
    for _, b in bgc.iterrows():
        did = b["dossier_id"]
        details[did] = {"bgc": b.dropna().to_dict()}
    for tbl, fields in [
        ("gene", ["gene_name", "predicted_function_raw", "demonstrated_function_raw", "phenotype_raw"]),
        ("metabolite", ["name_raw", "chemical_role_raw", "bioactivity_raw"]),
        ("experiment", ["experiment_id", "strain_raw"]),
        ("measurement", ["analyte_raw", "value_raw", "unit_raw"]),
        ("claim", ["claim_text", "evidence_type_raw"]),
        ("relationship", ["subject_raw", "predicate_raw", "object_raw"]),
        ("conflict", ["issue_type_raw", "description_raw", "status_raw"]),
        ("source", ["source_id", "source_type_raw", "title_or_database_raw", "doi_or_accession_raw", "url_raw"]),
    ]:
        df = d[tbl]
        for did, grp in df.groupby("dossier_id"):
            details.setdefault(did, {})[tbl] = grp[fields].fillna("").to_dict("records")

    (DOCS_DIR / "data").mkdir(parents=True, exist_ok=True)
    with open(DOCS_DIR / "data" / "dossier_index.json", "w") as fh:
        json.dump(index_rows, fh, default=str)
    with open(DOCS_DIR / "data" / "dossier_details.json", "w") as fh:
        json.dump(details, fh, default=str)

    return """
    <section id="browser" class="panel">
      <h2>Dossier Browser</h2>
      <p class="lede">Search and filter all 609 BGC dossiers; click a row to assemble its full cross-table
      record &mdash; organism, genes, metabolites, experiments, measurements, claims, relationships,
      conflicts and sources, joined on <code>dossier_id</code>.</p>
      <input id="dossier-search" type="search" placeholder="Search organism, product, accession, dossier id..." />
      <div class="browser-layout">
        <div id="dossier-table-wrap"><table id="dossier-table"><thead><tr>
          <th data-key="dossier_id">Dossier</th><th data-key="mibig_accession">MIBiG</th>
          <th data-key="organism">Organism</th><th data-key="product">Product</th>
          <th data-key="year">Year</th><th data-key="genes">Genes</th>
          <th data-key="metabolites">Metab.</th><th data-key="conflicts">Conflicts</th>
        </tr></thead><tbody></tbody></table></div>
        <div id="dossier-detail" class="detail-pane"><p class="muted">Select a dossier to view its full record.</p></div>
      </div>
    </section>"""


# ---------------------------------------------------------------- Data dictionary
def panel_dictionary() -> str:
    with open(PROCESSED_DIR / "documentation_sheets.json") as fh:
        docs = json.load(fh)

    def rows_to_table(rows: list[list], header_rows: int = 1) -> str:
        if not rows:
            return ""
        head = rows[0]
        body = rows[header_rows:]
        thead = "".join(f"<th>{c}</th>" for c in head)
        trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body if len(r) > 1)
        return f'<table class="dict-table"><thead><tr>{thead}</tr></thead><tbody>{trs}</tbody></table>'

    schema_tbl = rows_to_table(docs["SCHEMA"])
    policy_tbl = rows_to_table(docs["FEATURE_POLICY"])
    view_tbl = rows_to_table(docs["VIEW_SPEC"])
    readme_text = "".join(f"<p>{' — '.join(str(c) for c in r)}</p>" for r in docs["README"][1:])

    return f"""
    <section id="dictionary" class="panel">
      <h2>Data Dictionary</h2>
      <h3>About this resource</h3>{readme_text}
      <h3>Schema (23 tables)</h3>{schema_tbl}
      <h3>Feature policy (data families)</h3>{policy_tbl}
      <h3>View groups</h3>{view_tbl}
    </section>"""


PAGE_JS = r"""
<script>
const tabs = document.querySelectorAll('nav.tabs a');
const panels = document.querySelectorAll('main .panel');
function activate(id) {
  panels.forEach(p => p.classList.toggle('active', p.id === id));
  tabs.forEach(t => t.classList.toggle('active', t.getAttribute('href') === '#' + id));
  window.dispatchEvent(new Event('resize'));
}
tabs.forEach(t => t.addEventListener('click', e => {
  e.preventDefault();
  const id = t.getAttribute('href').slice(1);
  activate(id);
  history.replaceState(null, '', '#' + id);
}));
activate((location.hash || '#overview').slice(1));

// --- Facet explorer ---
let facetData = {};
fetch('data/bgc_facets.json').then(r => r.json()).then(data => {
  facetData = data;
  const sel = document.getElementById('facet-axis-select');
  if (sel) { renderFacet(sel.value); sel.addEventListener('change', () => renderFacet(sel.value)); }
});
function renderFacet(axis) {
  const rows = facetData[axis] || [];
  const counts = {};
  rows.forEach(r => { counts[r.value] = (counts[r.value] || 0) + 1; });
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 20);
  const trace = {
    x: entries.map(e => e[1]), y: entries.map(e => e[0]),
    type: 'bar', orientation: 'h', marker: { color: '#2c5f6f' },
  };
  Plotly.newPlot('facet-value-chart', [trace], {
    title: 'Top values for ' + axis, margin: { l: 260, t: 40 }, height: 500,
  }, { displaylogo: false, responsive: true });
  const list = document.getElementById('facet-dossier-list');
  list.innerHTML = '<strong>' + rows.length + ' rows on this axis</strong><ul>' +
    rows.slice(0, 200).map(r => '<li><code>' + r.dossier_id + '</code> — ' + r.value + '</li>').join('') +
    (rows.length > 200 ? '<li>&hellip; ' + (rows.length - 200) + ' more</li>' : '') + '</ul>';
}

// --- Dossier browser ---
let dossierIndex = [], dossierDetails = {};
Promise.all([
  fetch('data/dossier_index.json').then(r => r.json()),
  fetch('data/dossier_details.json').then(r => r.json()),
]).then(([idx, det]) => {
  dossierIndex = idx; dossierDetails = det;
  renderDossierTable(dossierIndex);
});
function renderDossierTable(rows) {
  const tbody = document.querySelector('#dossier-table tbody');
  if (!tbody) return;
  tbody.innerHTML = rows.map(r => `<tr data-id="${r.dossier_id}">
    <td>${r.dossier_id}</td><td>${r.mibig_accession || ''}</td>
    <td>${r.organism || ''}</td><td>${(r.product || '').slice(0, 60)}</td>
    <td>${r.year || ''}</td><td>${r.genes}</td><td>${r.metabolites}</td><td>${r.conflicts}</td>
  </tr>`).join('');
  tbody.querySelectorAll('tr').forEach(tr => tr.addEventListener('click', () => showDossier(tr.dataset.id)));
}
document.addEventListener('input', e => {
  if (e.target.id !== 'dossier-search') return;
  const q = e.target.value.toLowerCase();
  renderDossierTable(dossierIndex.filter(r =>
    [r.dossier_id, r.mibig_accession, r.organism, r.product, r.bgc_class]
      .some(v => (v || '').toString().toLowerCase().includes(q))));
});
function showDossier(id) {
  const rec = dossierDetails[id];
  const pane = document.getElementById('dossier-detail');
  if (!rec) { pane.innerHTML = '<p class="muted">No detail found.</p>'; return; }
  const b = rec.bgc || {};
  const section = (title, rows, fields) => {
    if (!rows || !rows.length) return '';
    const cols = fields || Object.keys(rows[0]);
    return `<h4>${title} (${rows.length})</h4><table class="detail-table"><thead><tr>` +
      cols.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>' +
      rows.map(r => '<tr>' + cols.map(c => `<td>${r[c] ?? ''}</td>`).join('') + '</tr>').join('') +
      '</tbody></table>';
  };
  pane.innerHTML = `
    <h3>${id} — ${b.mibig_accession || ''}</h3>
    <p><strong>${b.organism_name || ''}</strong> — ${b.primary_product_raw || ''}</p>
    <p class="muted">${b.mibig_bgc_class_raw || ''} · ${b.primary_reference_year || ''} ·
      <a href="https://doi.org/${b.primary_reference_doi || ''}" target="_blank" rel="noopener">${b.primary_reference_doi || ''}</a></p>
    ${section('Genes', rec.gene)}
    ${section('Metabolites', rec.metabolite)}
    ${section('Experiments', rec.experiment)}
    ${section('Measurements', rec.measurement)}
    ${section('Claims', rec.claim)}
    ${section('Relationships', rec.relationship)}
    ${section('Conflicts', rec.conflict)}
    ${section('Sources', rec.source)}
  `;
}
</script>
"""

PAGE_CSS = r"""
<style>
/* Variable names match the shared cose-theme.css overlay's tokens so it can
   re-skin this page's own colours (--bg/--fg/--muted/--line/--card/--accent). */
:root { --bg:#ffffff; --fg:#1a2230; --muted:#5a6473; --line:#e5e9f0; --card:#f7f9fc; --accent:#3B6EA5; --accent2:#3FB6A8; }
@media (prefers-color-scheme: dark){
  :root{ --bg:#0f141b; --fg:#e6ebf2; --muted:#9aa6b6; --line:#232c39; --card:#161d27; --accent:#6ea3d8; --accent2:#54c9ba; }
}
* { box-sizing: border-box; }
body { margin:0; font-family: Inter, "Segoe UI", sans-serif; color:var(--fg); background:var(--bg); }
header.hero { padding:2.5rem 2rem 1.5rem; border-bottom:1px solid var(--line); }
header.hero h1 { margin:0 0 .3rem; font-size:1.7rem; }
header.hero p { margin:0; color:var(--muted); max-width:60ch; }
nav.tabs { display:flex; flex-wrap:wrap; gap:.25rem; padding:0 2rem; border-bottom:1px solid var(--line);
  background:var(--bg); position:sticky; top:0; z-index:5; }
nav.tabs a { padding:.7rem .9rem; text-decoration:none; color:var(--muted); font-size:.92rem; border-bottom:2px solid transparent; }
nav.tabs a.active { color:var(--accent); border-bottom-color:var(--accent); font-weight:600; }
main { padding:1.5rem 2rem 4rem; max-width:1200px; margin:0 auto; }
.panel { display:none; }
.panel.active { display:block; }
.panel h2 { margin-top:0; }
.lede { color:var(--muted); max-width:80ch; }
.card-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:.8rem; margin:1.2rem 0; }
.card { border:1px solid var(--line); border-radius:8px; padding:1rem; background:var(--card); }
.card-value { font-size:1.5rem; font-weight:700; color:var(--accent); }
.card-label { font-size:.85rem; margin-top:.2rem; }
.card-note { font-size:.75rem; color:var(--muted); }
.chart-box { border:1px solid var(--line); border-radius:8px; padding:.5rem; margin:1rem 0; background:var(--card); }
.facet-controls { margin:.5rem 0 1rem; }
select, input[type=search] { padding:.5rem; border:1px solid var(--line); border-radius:6px; font-size:.95rem; width:100%; max-width:420px;
  background:var(--bg); color:var(--fg); }
.scroll-list { max-height:320px; overflow:auto; border:1px solid var(--line); border-radius:8px; padding:.8rem 1.2rem; background:var(--card); }
.browser-layout { display:grid; grid-template-columns:1.2fr 1fr; gap:1rem; margin-top:1rem; align-items:start; }
#dossier-table-wrap { max-height:70vh; overflow:auto; border:1px solid var(--line); border-radius:8px; background:var(--card); }
table#dossier-table { width:100%; border-collapse:collapse; font-size:.85rem; }
table#dossier-table th { position:sticky; top:0; background:var(--card); text-align:left; padding:.5rem; border-bottom:1px solid var(--line); }
table#dossier-table td { padding:.45rem .5rem; border-bottom:1px solid var(--line); }
table#dossier-table tr:hover { background:var(--card); cursor:pointer; }
.detail-pane { border:1px solid var(--line); border-radius:8px; padding:1rem; background:var(--card); max-height:70vh; overflow:auto; }
.detail-table { width:100%; border-collapse:collapse; font-size:.78rem; margin:.3rem 0 1rem; }
.detail-table th, .detail-table td { border-bottom:1px solid var(--line); padding:.3rem; text-align:left; vertical-align:top; }
.dict-table { width:100%; border-collapse:collapse; font-size:.85rem; margin:.5rem 0 1.5rem; }
.dict-table th, .dict-table td { border-bottom:1px solid var(--line); padding:.4rem; text-align:left; }
.muted { color:var(--muted); }
footer { padding:1.5rem 2rem; text-align:center; color:var(--muted); font-size:.8rem; border-top:1px solid var(--line); }
@media (max-width:800px) { .browser-layout { grid-template-columns:1fr; } }
</style>
"""


def build_dashboard() -> None:
    d = {name.lower(): _read(name.lower()) for name in [
        "bgc", "organism", "strain", "bgc_facet", "gene", "metabolite", "experiment",
        "measurement", "claim", "relationship", "conflict", "source", "evidence_link", "coverage",
    ]}

    panels = [
        panel_overview(d), panel_taxonomy(d), panel_chemistry(d), panel_facets(d),
        panel_graph(d), panel_evidence(d), panel_conflicts(d), panel_browser(d), panel_dictionary(),
    ]
    nav_items = [
        ("overview", "Overview"), ("taxonomy", "Taxonomy"), ("chemistry", "Chemistry"),
        ("facets", "Facet Explorer"), ("graph", "Knowledge Graph"), ("evidence", "Evidence"),
        ("conflicts", "Conflicts"), ("browser", "Dossier Browser"), ("dictionary", "Data Dictionary"),
    ]
    nav_html = "".join(f'<a href="#{i}">{label}</a>' for i, label in nav_items)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Fungal BGC Atlas</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
{PAGE_CSS}
<!-- COSE shared overlay theme, loaded after the page's own CSS so it can re-point
     the --bg/--fg/--accent/etc. tokens above and add the toggleable map rail. -->
<link rel="stylesheet" href="assets/cose-theme.css" />
</head>
<body data-site-id="fungal-bgc-atlas">
<header class="hero">
  <h1>Fungal BGC Atlas</h1>
  <p>An interactive, evidence-linked explorer for {len(d['bgc'])} curated fungal biosynthetic gene
  cluster dossiers &mdash; genes, metabolites, experiments, claims, relationships and preserved
  conflicts, all traceable back to their primary sources. Build {SNAPSHOT_LABEL} &middot; v{__version__}.</p>
</header>
<nav class="tabs">{nav_html}</nav>
<main>
{''.join(panels)}
</main>
<footer>
  Fungal BGC Atlas &middot; CC-BY-4.0 &middot;
  <a href="https://github.com/dr-richard-barker/fungal-bgc-atlas">Source &amp; data on GitHub</a>
</footer>
{PAGE_JS}
<script src="assets/sites.js"></script>
<script src="assets/theme.js"></script>
</body>
</html>"""

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html)
    print(f"Wrote docs/index.html ({len(html) / 1024:.0f} KB) + docs/data/*.json")


if __name__ == "__main__":
    build_dashboard()
