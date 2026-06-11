"""
Plain-language explainer components
===================================

A thin presentation layer that translates the app for clients and
senior managers — kept deliberately terse so it orients without adding
reading load:

1. render_plain_guide — one "In plain English" line at the top of
   each page.
2. render_logic_pipeline — the system's logic as four short cards
   (Detect, Diagnose, Decide, Do), with the full data-flow diagram
   one click away.
3. render_glossary — collapsed two-column jargon translator.

Nothing here reads or changes data.
"""

import streamlit as st


def render_plain_guide(text: str) -> None:
    """One-line plain-English orientation for the top of a page."""
    st.caption(f"💼 **In plain English:** {text}")


# User journey through the app's pages. Solid = the main path,
# dashed = optional branches. The work order is the goal, so it gets
# the primary fill.
_USERFLOW_DOT = """
digraph userflow {
    rankdir=LR;
    bgcolor="transparent";
    node [shape=box, style="rounded,filled", fillcolor="#F5F4EF",
          color="#534AB7", fontcolor="#2C2C2A", fontname="Helvetica",
          fontsize=12, margin="0.22,0.14"];
    edge [color="#534AB7", penwidth=1.3, arrowsize=0.8];

    overview [label="① Overview\\ncheck the numbers"];
    register [label="② Defect Register\\nfilter & pick a defect"];
    detail   [label="③ Defect Detail\\nreview the case file"];
    wo       [label="④ Work order\\ngenerate & download",
              fillcolor="#534AB7", fontcolor="#FFFFFF"];
    ingest   [label="Ⓐ Ingest\\nlog a new site finding",
              style="rounded,filled,dashed"];
    verify   [label="Ⓑ Verify\\nSPARQL / Ontology",
              style="rounded,filled,dashed"];

    overview -> register -> detail -> wo;
    ingest -> register [style=dashed];
    detail -> verify [style=dashed];
}
"""

def render_user_workflow() -> None:
    """Numbered usage steps with the user-journey diagram below, full
    width so it renders at a readable size. The step numbers match the
    sidebar's numbered page labels."""
    st.markdown(
        "① **Overview** — check the numbers below.  \n"
        "② **Defect Register** — filter the map, pick a defect.  \n"
        "③ **Defect Detail** — evidence, cause, prescribed repair.  \n"
        "④ **Work order** — generate at the bottom of Defect Detail."
    )
    st.caption(
        "Anytime: Ⓐ new site finding → **Ingest** · Ⓑ verify a "
        "number → **SPARQL / Ontology** · Ⓒ new asset → "
        "**Tunnel Setup** · 🧊 see defects in 3-D → **3D Tunnel (BIM)** "
        "· 📄 one-click PDF of everything → **Report**."
    )
    st.graphviz_chart(_USERFLOW_DOT, use_container_width=True)


# Colors match .streamlit/config.toml theme (primary #534AB7,
# secondary background #F5F4EF, text #2C2C2A).
_PIPELINE_DOT = """
digraph pipeline {
    rankdir=LR;
    bgcolor="transparent";
    node [shape=box, style="rounded,filled", fillcolor="#F5F4EF",
          color="#534AB7", fontcolor="#2C2C2A", fontname="Helvetica",
          fontsize=12, margin="0.22,0.14"];
    edge [color="#534AB7", penwidth=1.3, arrowsize=0.8];

    survey  [label="Tunnel survey\\nphoto, 3-D depth,\\nthermal, radar"];
    extract [label="AI extraction\\nfinds, measures and\\nlocates each defect"];
    records [label="Standard records\\none asset record per\\ndefect (COBie format)"];
    kb      [label="Knowledge base\\nlinks defect to cause,\\nrisk and repair"];
    rank    [label="Risk ranking\\nurgency scored against\\nroad-agency standards"];
    plan    [label="Maintenance plan\\nwork orders with method,\\ndeadline and cost"];

    survey -> extract -> records -> kb -> rank -> plan;
}
"""

_STORY_STEPS = [
    ("🔍", "Detect", "Sensors survey the tunnel; AI finds and measures defects."),
    ("🧠", "Diagnose", "Each defect is traced to its engineering cause (FMEA)."),
    ("⚖️", "Decide", "Standards-based rules rank urgency and pick the repair."),
    ("🔧", "Do", "Costed work orders feed the maintenance programme."),
]


def render_logic_pipeline() -> None:
    """The system's logic as four short cards, for the Overview page."""
    cols = st.columns(4)
    for col, (icon, title, body) in zip(cols, _STORY_STEPS):
        with col:
            with st.container(border=True):
                st.markdown(f"**{icon} {title}**")
                st.caption(body)

    with st.expander("Full data flow — survey to work order"):
        st.graphviz_chart(_PIPELINE_DOT)
        st.caption(
            "Read right to left for audit: every work order traces back "
            "to raw survey evidence."
        )


_GLOSSARY = [
    ("Knowledge base / ontology",
     "the engineering knowledge the system reasons with"),
    ("FMEA", "standard cause-and-effect analysis of failures"),
    ("COBie", "industry-standard format for asset records"),
    ("SPARQL", "query language for the knowledge base"),
    ("Modality", "one sensing source: photo, depth, thermal or radar"),
    ("Ring / chainage", "tunnel address — lining hoop / metres from entrance"),
    ("Completeness", "evidence held vs ideal (4/4 = fully corroborated)"),
    ("Priority", "rule-based urgency from moisture and severity codes — "
     "HIGH means act within 30 days"),
    ("Estimated cost",
     "engineer figure where recorded, else unit-rate model estimate"),
]


def render_glossary() -> None:
    """Compact jargon translator, collapsed by default."""
    with st.expander("📖 Jargon translator"):
        left, right = st.columns(2)
        for i, (term, meaning) in enumerate(_GLOSSARY):
            target = left if i % 2 == 0 else right
            target.markdown(f"**{term}** — {meaning}")


def render_priority_cost_help() -> None:
    """How priority and estimated cost are determined — shown wherever
    those two columns appear, so the basis is never a mystery."""
    with st.expander("ℹ️ How priority and cost are determined"):
        st.markdown(
            "**Priority** is rule-based, following AASHTO / Austroads "
            "condition coding: active water ingress (moisture code "
            "GS = gushing, F = flowing) **or** spalling at/past the "
            "reinforcement (AASHTO grade S-3 / S-4) → **HIGH** — act "
            "within 30 days. Moderate spalling (S-2) or damp surface "
            "(M) → **MEDIUM**. Otherwise **LOW**. The rule is "
            "`assign_priority()` in the CV → COBie bridge; operators "
            "can override it when registering a defect, and an "
            "engineer signs off on every work order.\n\n"
            "**Estimated cost** — engineer-recorded figures where they "
            "exist; otherwise a transparent **unit-rate model**: the "
            "defect type's repair method (AASHTO/Austroads) × measured "
            "quantity × indicative Australian rates, plus "
            "night-possession mobilisation, adjusted for severity, "
            "active water and crown access, with a contingency band "
            "that widens when evidence completeness is low. Every "
            "figure's full build-up is on the **Defect Detail** page. "
            "Default rates are placeholders — calibrate them to your "
            "maintenance contract."
        )
