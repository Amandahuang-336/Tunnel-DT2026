"""
Tunnel Digital Twin — Operator Dashboard
=========================================
Main Streamlit application entry point and page router.

Run locally:
    streamlit run app.py      # see README.md for installation

This is the human-facing interface for a serviceability-oriented
multimodal tunnel maintenance digital twin. It queries a populated
ontology (OWL/Turtle) through rdflib and presents defect records,
FMEA chains, and prescribed interventions.

Navigation uses st.navigation (MPA v2) so the sidebar shows the pages
in numbered workflow order, grouped by purpose — the page list itself
tells a first-time user where to start. The files in pages/ remain
standalone-runnable (e.g. for AppTest), but their sidebar order,
labels and icons are defined here.

Architecture:
    Protégé (authoring)
        │
        ▼  OWL/Turtle file
    ontology/tunnel_maintenance.ttl
        │
        ▼  rdflib loads into memory
    This Streamlit app
        │
        ├─ SPARQL queries on page load
        └─ Operator views defects, FMEA chains, interventions
"""

import sys

import pandas as pd
import streamlit as st

from utils.ontology_loader import load_ontology, load_defects
from utils.styling import apply_custom_css
from utils.gis import list_tunnels
from utils.cost_model import effective_cost
from utils.explainers import render_glossary
from utils import overview_stack
from utils.demo_mode import is_public_demo, show_error, notice

# -----------------------------------------------------------------------------
# Page configuration — MUST be the first Streamlit call
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Tunnel DT",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/Amandahuang-336/Tunnel-DT2026",
        "Report a bug": "https://github.com/Amandahuang-336/Tunnel-DT2026/issues",
        "About": (
            "Tunnel Digital Twin operator dashboard, accompanying the paper "
            "*Serviceability-oriented multimodal data integration for "
            "prescriptive road-tunnel maintenance digital twins* "
            "(Tunnelling and Underground Space Technology)."
        ),
    },
)

apply_custom_css()


# -----------------------------------------------------------------------------
# Session state initialisation
# -----------------------------------------------------------------------------
def init_session_state():
    """Initialise session state with sensible defaults."""
    defaults = {
        "ontology_loaded": False,
        "selected_defect_id": None,
        "current_tunnel": "Tunnel A",
        "graph": None,
        "defects": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# -----------------------------------------------------------------------------
# Ontology loader — wrapped to handle errors gracefully
# -----------------------------------------------------------------------------
def ensure_ontology_loaded():
    """Load ontology and defect data into session state if not already done."""
    if st.session_state.ontology_loaded:
        return True

    try:
        with st.spinner("Loading ontology and defect data..."):
            graph = load_ontology()
            defects = load_defects(graph)
            st.session_state.graph = graph
            st.session_state.defects = defects
            st.session_state.ontology_loaded = True
        return True
    except Exception as e:
        show_error(e, "Failed to load the ontology.")
        return False


# -----------------------------------------------------------------------------
# Sidebar — compact: tunnel selector plus one collapsed System expander.
# Page navigation itself is rendered by st.navigation above this content.
# -----------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown("#### 🛣️ Tunnel DT")
        st.caption("Serviceability-oriented digital twin")

        if is_public_demo():
            st.info(notice(), icon="🌐")

        # Built-in tunnels plus any the user registered on Tunnel Setup.
        tunnel_labels = [t["label"] for t in list_tunnels()] or ["Tunnel A"]
        tunnel_choice = st.selectbox(
            "Active tunnel",
            options=tunnel_labels,
            index=0,
            help=(
                "Tunnel A carries the full demo dataset. "
                "Add your own tunnel on the **Tunnel Setup** page."
            ),
        )
        st.session_state.current_tunnel = tunnel_choice

        with st.expander("System", expanded=False):
            if st.session_state.ontology_loaded and st.session_state.graph is not None:
                st.caption(
                    f"✓ Ontology loaded — "
                    f"{len(st.session_state.graph):,} triples · "
                    f"{len(st.session_state.defects)} defect instances"
                )
            else:
                st.caption("Ontology not loaded")
            if st.button("Reload ontology", width="stretch"):
                st.session_state.ontology_loaded = False
                st.cache_data.clear()
                st.cache_resource.clear()
                st.rerun()
            st.caption(
                f"Python {sys.version.split()[0]} · "
                f"Streamlit {st.__version__}"
            )
            st.caption(
                "Companion app to the paper *Serviceability-oriented "
                "multimodal data integration for prescriptive road-tunnel "
                "maintenance digital twins*."
            )


# -----------------------------------------------------------------------------
# Overview page content
# -----------------------------------------------------------------------------
def render_overview():
    st.title("Tunnel Maintenance Digital Twins")
    st.markdown(
        "<p style='font-size:21px;color:#5C6270;margin:-10px 0 16px;"
        "line-height:1.4;letter-spacing:-.01em;'>"
        "Serviceability-oriented Multimodal Data Integration</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "This dashboard turns tunnel inspection evidence into costed, "
        "standards-backed maintenance decisions. Findings from four sensing "
        "sources — image, 3-D depth, thermal and ground-penetrating "
        "radar — are registered against the tunnel's as-built model and "
        "reasoned over an OWL ontology that traces each defect along a "
        "seven-level FMEA chain: component → mechanism → defect → indicator "
        "→ cause → threshold → intervention. What comes back is a "
        "prioritised repair with an indicative cost and the AASHTO / "
        "Austroads clause that justifies it."
    )
    st.caption(
        "Work through the numbered steps in the sidebar — set up the asset "
        "(1–2), inspect and diagnose (3–6), use the specialist tools if you "
        "need them (7–9) — then produce the deliverables in **Report and "
        "presentation**. Headline figures for the selected tunnel live in "
        "those documents. The map below shows how the parts fit together."
    )

    defects = st.session_state.defects
    if not defects:
        st.warning(
            "No defect data loaded. Check that "
            "`data/defects_tunnel_a.json` exists and is valid."
        )
        return

    # Filter by status
    active_defects = [d for d in defects if d.get("status") == "Active"]
    high_priority = [d for d in active_defects if d.get("priority") == "HIGH"]
    # The headline KPI row and its "bottom line" reading used to sit here.
    # They are the executive summary of the Report and presentation page (see
    # utils/report_html.py and utils/report_onepager.py), so the Overview
    # stays an explanation of the system rather than a second dashboard.

    st.divider()

    # -----------------------------------------------------------------------------
    # The framework as a layered stack. Reads bottom to top: evidence enters at
    # the base, the ontology reasons over it, the operator's deliverables come
    # out of the top. Every block links to the page that implements it, so this
    # is the app's navigation as well as its explanation. Hovering a block dims
    # everything not on its evidence path.
    # -----------------------------------------------------------------------------
    st.markdown(
        # Each capability links to the page where it is actually carried out.
        overview_stack.render_stack(capabilities=[
            ("Classify severity", "/Ingest"),
            ("Resolve threshold", "/Defect_Detail#resolve-threshold"),
            ("Rank priority", "/Defect_Register"),
            ("Estimate cost", "/Defect_Detail#cost-build-up"),
            ("Trace cause", "/Defect_Detail#trace-cause"),
            ("Detect inter-cycle change", "/Governance"),
        ]),
        unsafe_allow_html=True,
    )
    st.caption(
        "Read bottom to top: evidence enters at the base, the ontology reasons "
        "over it, deliverables leave from the top. Hover a block to see what it "
        "depends on; click a link to open that page."
    )

    st.divider()

    # -----------------------------------------------------------------------------
    # Section coverage — one compact row
    # -----------------------------------------------------------------------------
    st.subheader("Survey coverage by tunnel section")
    st.caption(
        "🟢 well surveyed · 🟡 partial · 🔴 needs follow-up survey — "
        "coverage = rings with evidence from ≥3 of 4 sensing sources."
    )

    sections = [
        ("Section 1", "K248+500 – K249+200", 95, "🟢"),
        ("Section 2", "K249+200 – K249+900", 78, "🟡"),
        ("Section 3", "K249+900 – K250+600", 52, "🔴"),
        ("Section 4", "K250+600 – K251+300", 67, "🟡"),
    ]

    cols = st.columns(4)
    for col, (name, span, pct, icon) in zip(cols, sections):
        with col:
            st.markdown(f"{icon} **{name}** · {pct}%")
            st.progress(pct / 100)
            st.caption(span)

    st.divider()

    # -----------------------------------------------------------------------------
    # Top priority defects — compact table
    # -----------------------------------------------------------------------------
    st.subheader("Top priority defects")
    st.caption(
        "Five most urgent, ranked by condition and evidence strength. "
        "Evidence 4/4 = corroborated by every applicable source. "
        "Full list: **Defect Register**."
    )

    top_defects = sorted(
        high_priority,
        key=lambda d: (
            -d.get("completeness_score", 0),
            d.get("discovered_on", ""),
        ),
    )[:5]

    if not top_defects:
        st.info("No high priority defects currently identified.")
        return

    rows = []
    for d in top_defects:
        cost, basis = effective_cost(d)
        rows.append({
            "ID": d["defect_id"],
            "Defect": d["description"],
            "Where": f"Ring {d['ring_id']} · K{d['chainage_m']:.0f}m · "
                     f"{d.get('position', '—')}",
            "Evidence": f"{int(d.get('completeness_score', 0) * 4)}/4",
            "Priority": d.get("priority", "—"),
            "Est. cost (AUD)": cost,
            "Basis": basis,
        })
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Est. cost (AUD)": st.column_config.NumberColumn(format="$%d"),
        },
    )
    st.caption(
        "Cost basis: **engineer** = recorded estimate · **modelled** = "
        "unit-rate model (build-up on the Defect Detail page)."
    )

    render_glossary()


# -----------------------------------------------------------------------------
# Navigation — numbered workflow order, grouped by purpose. This replaces
# Streamlit's automatic pages/ nav, so labels and grouping are explicit.
# -----------------------------------------------------------------------------
# Groups follow the asset lifecycle: set up the tunnel, see its BIM
# model, register and diagnose defects (with the standards one step
# away), and finish with the report that summarises it all.
nav = st.navigation({
    "Start here": [
        st.Page(render_overview, title="Overview", icon="🏠",
                url_path="overview", default=True),
    ],
    "Set up the asset": [
        st.Page("pages/6_Tunnel_Setup.py",
                title="1 · Tunnel Setup", icon="🛠️"),
        st.Page("pages/7_BIM_3D_Viewer.py",
                title="2 · 3D Tunnel (BIM)", icon="🧊"),
    ],
    "Inspect & diagnose": [
        st.Page("pages/0_Ingest.py",
                title="3 · Ingest a finding", icon="📤"),
        st.Page("pages/1_Defect_Register.py",
                title="4 · Defect Register", icon="🗺️"),
        st.Page("pages/2_Defect_Detail.py",
                title="5 · Defect Detail", icon="📋"),
        st.Page("pages/9_Standards_Library.py",
                title="6 · Standards Library", icon="📚"),
    ],
    "Specialists": [
        st.Page("pages/3_SPARQL_Console.py",
                title="7 · SPARQL Console", icon="🔎"),
        st.Page("pages/4_CV_to_COBie_Bridge.py",
                title="8 · CV → COBie Bridge", icon="🌉"),
        st.Page("pages/5_Ontology_Browser.py",
                title="9 · Ontology Browser", icon="🧩"),
        st.Page("pages/10_Governance.py",
                title="10 · Governance", icon="🕰️"),
    ],
    "Summary": [
        st.Page("pages/8_Report.py", title="Report and Presentation",
                icon="📄"),
    ],
})

# Load the ontology BEFORE rendering the sidebar, so the System panel reflects
# the real state. The Reload button sets ontology_loaded=False and reruns;
# rendering the sidebar first would show "Ontology not loaded" until the next
# interaction, even though the reload immediately below succeeds.
ontology_ok = ensure_ontology_loaded()
render_sidebar()
if not ontology_ok:
    st.stop()

try:
    nav.run()
except Exception as exc:
    show_error(exc, "⚠️ The dashboard encountered an unexpected error.")
    st.markdown("---")
    st.caption(
        "If this persists, please report the issue at "
        "[GitHub Issues](https://github.com/Amandahuang-336/Tunnel-DT2026/issues)."
    )
