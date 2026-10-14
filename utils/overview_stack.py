"""
Overview page — the layered stack
=================================

Renders the framework as a single foldable diagram: sources at the bottom,
the ontology and its governance in the middle, the operator-facing outputs on
top. Every block links to the page that implements it, so the diagram is the
app's navigation as well as its explanation.

WHY THIS IS HTML AND NOT STREAMLIT WIDGETS
------------------------------------------
Three requirements pull the same way:

1. *Clicking a block must open a page.* Streamlit's MPA v2 gives every page a
   URL path (``/Defect_Register``, ``/Governance``, ...), so a plain
   ``<a href="/Defect_Register" target="_self">`` navigates with no rerun and
   no callback. ``st.page_link`` cannot be laid out as a diagram; a
   ``components.html`` iframe could be, but then the links can no longer reach
   the parent document, which defeats the point.

2. *Hover must reveal and trace.* Pointing at a block dims everything that is
   not on its evidence path, so "where does the report get its numbers from"
   is answered by moving the mouse.

3. *No JavaScript is available.* ``st.markdown`` renders ``<style>`` but strips
   ``<script>``. The trace highlighting is therefore pure CSS, using ``:has()``
   with one rule per block, generated from CHAINS below so the diagram and its
   highlighting cannot drift apart. ``:has()`` is supported in every current
   browser; where it is not, the diagram simply does not dim.

The scroll reveal uses ``animation-timeline: view()``, guarded by ``@supports``.
Browsers without it show the tiers immediately, which is a degradation in
polish and not in function.

LAYOUT
------
    outputs      Register & diagnosis | Model & geometry | Reports
                              ^  ^  ^
    ontology     [ SPARQL ]  FMEA reasoning chain  [ Governance ]
                              ^  ^  ^
    sources      Asset & survey | Extraction & rules | Standards
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Sequence

# -----------------------------------------------------------------------------
# The blocks. `pages` is a list of (label, url_path) — every page in the app
# appears exactly once, so the diagram doubles as a complete table of contents.
# -----------------------------------------------------------------------------
BLOCKS: Dict[str, Dict[str, Any]] = {
    # --- outputs (top tier) --------------------------------------------------
    "register": {
        "tier": "out", "cap": "Register & diagnosis",
        "rest": "What is wrong, where, and why",
        "hover": "Every defect with its FMEA chain, prescribed repair and work order",
        "pages": [("Defect register", "/Defect_Register"),
                  ("Defect detail", "/Defect_Detail")],
    },
    "model": {
        "tier": "out", "cap": "Model & geometry",
        "rest": "The tunnel as built",
        "hover": "Lining rings, alignment and defect positions in three dimensions",
        "pages": [("3D tunnel (BIM)", "/BIM_3D_Viewer")],
    },
    "reports": {
        "tier": "out", "cap": "Reports",
        "rest": "What leaves the system",
        "hover": "One-pager, full condition report and slide deck, as PDF or web page",
        "pages": [("Report and presentation", "/Report")],
    },
    # --- the ontology (middle) ----------------------------------------------
    "sparql": {
        "tier": "mid", "cap": "Query",
        "rest": "Verify any figure",
        "hover": "Ask the knowledge base directly; every number in the app is checkable",
        "pages": [("SPARQL console", "/SPARQL_Console")],
    },
    "ontology": {
        "tier": "core", "cap": "Ontology system",
        "rest": "Seven-level FMEA reasoning chain",
        "hover": "Component, mechanism, defect, indicator, cause, threshold, intervention",
        "pages": [("Ontology browser", "/Ontology_Browser")],
    },
    "governance": {
        "tier": "mid", "cap": "Governance",
        "rest": "Editions and manifests",
        "hover": "Thresholds bound to dated clauses, so a past decision stays reconstructible",
        "pages": [("Governance", "/Governance")],
    },
    # --- sources (bottom tier) ----------------------------------------------
    "asset": {
        "tier": "src", "cap": "Asset & survey",
        "rest": "What was inspected, and what was seen",
        "hover": "Tunnel geometry and alignment, plus RGB, depth, thermal and GPR findings",
        "pages": [("Tunnel setup", "/Tunnel_Setup"), ("Ingest a finding", "/Ingest")],
    },
    "extraction": {
        "tier": "src", "cap": "Extraction & rules",
        "rest": "Pixels to asset records",
        "hover": "Detections become COBie rows; the priority rule is applied and shown",
        "pages": [("CV to COBie bridge", "/CV_to_COBie_Bridge")],
    },
    "standards": {
        "tier": "src", "cap": "Standards",
        "rest": "Where the thresholds come from",
        "hover": "AASHTO and AS 3600 clauses, with the edition each threshold derives from",
        "pages": [("Standards library", "/Standards_Library")],
    },
}

# Evidence paths. Hovering a block lights these and dims the rest, so the
# diagram answers "what does this depend on, and what depends on it".
CHAINS: Dict[str, Sequence[str]] = {
    "asset":      ("asset", "extraction", "ontology", "register", "model", "reports"),
    "extraction": ("extraction", "asset", "ontology", "register"),
    "standards":  ("standards", "ontology", "governance", "register", "reports"),
    "ontology":   tuple(BLOCKS.keys()),
    "sparql":     ("sparql", "ontology"),
    "governance": ("governance", "ontology", "standards", "reports"),
    "register":   ("register", "ontology", "asset", "extraction", "standards"),
    "model":      ("model", "ontology", "asset"),
    "reports":    ("reports", "ontology", "register", "standards", "governance"),
}

_PRIMARY = "#534AB7"
_INK = "#2C2C2A"


def _e(text: Any) -> str:
    return html.escape("" if text is None else str(text))


def _trace_rules() -> str:
    """One :has() rule per block — generated, so highlighting cannot drift."""
    out: List[str] = []
    for bid, lit in CHAINS.items():
        dim = [b for b in BLOCKS if b not in lit]
        if not dim:
            continue
        sel = ", ".join(f".otx:has(#b-{bid}:hover) #b-{b}" for b in dim)
        out.append(f"{sel} {{ opacity:.2; filter:saturate(.3); }}")
        on = ", ".join(f".otx:has(#b-{bid}:hover) #b-{b}" for b in lit)
        out.append(f"{on} {{ border-color:{_PRIMARY}; }}")
    return "\n".join(out)


def _css() -> str:
    return f"""
<style>
.otx {{ margin: .25rem 0 1.25rem; }}
.otx a {{ text-decoration: none; }}

.otx-tier {{ display: flex; gap: 14px; align-items: stretch; }}
.otx-tier > * {{ flex: 1; min-width: 0; }}

.otx-blk {{
  position: relative; border: 1.5px solid rgba(0,0,0,.12); border-radius: 10px;
  background: #FFFFFF; padding: 14px 16px 12px;
  transition: opacity .18s, border-color .18s, transform .18s, box-shadow .18s;
}}
.otx-blk:hover {{ transform: translateY(-3px); box-shadow: 0 6px 18px rgba(83,74,183,.13); }}
.otx-cap {{
  font-size: 15.5px; font-weight: 600; letter-spacing: .01em;
  color: #6F6E85; margin-bottom: 7px;
}}
.otx-line {{ font-size: 17px; color: {_INK}; line-height: 1.45; min-height: 48px; }}
.otx-line .h {{ display: none; }}
.otx-blk:hover .otx-line .r {{ display: none; }}
.otx-blk:hover .otx-line .h {{ display: inline; color: {_PRIMARY}; }}
.otx-links {{ margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }}
.otx-links a {{
  font-size: 14.5px; padding: 4px 12px; border-radius: 20px;
  border: 1px solid rgba(83,74,183,.35); color: {_PRIMARY}; background: #FFFFFF;
  transition: background .15s, color .15s;
}}
.otx-links a:hover {{ background: {_PRIMARY}; color: #FFFFFF; }}

.otx-core {{
  border: 1.5px solid {_PRIMARY}; border-radius: 12px;
  background: rgba(83,74,183,.06); padding: 14px 16px 12px;
}}
.otx-core .otx-cap {{ color: {_PRIMARY}; }}
.otx-slab {{ display: flex; gap: 14px; align-items: stretch; }}
.otx-slab > .side {{ flex: 0 0 22%; }}
.otx-slab > .mid {{ flex: 1; min-width: 0; }}
.otx-pills {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }}
.otx-pills span, .otx-pills a {{
  font-size: 14px; padding: 3px 11px; border-radius: 20px;
  background: #FFFFFF; border: 1px solid rgba(83,74,183,.3); color: {_PRIMARY};
}}
/* Linked capabilities behave like the block's page links. */
.otx-pills a {{ transition: background .15s, color .15s; }}
.otx-pills a:hover {{ background: {_PRIMARY}; color: #FFFFFF; }}

.otx-flow {{ display: flex; gap: 14px; height: 26px; }}
.otx-flow > i {{ flex: 1; border-top: 2px dotted rgba(83,74,183,.45); margin-top: 12px; }}

.otx-rail {{
  font-size: 15.5px; font-weight: 600; letter-spacing: .01em;
  color: #6F6E85; margin: 0 0 8px 2px;
}}

{_trace_rules()}

@supports (animation-timeline: view()) {{
  .otx-reveal {{
    animation: otxin linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 26%;
  }}
  @keyframes otxin {{
    from {{ opacity: 0; transform: translateY(16px); }}
    to   {{ opacity: 1; transform: none; }}
  }}
}}
@media (prefers-reduced-motion: reduce) {{
  .otx-reveal {{ animation: none; }}
}}
</style>
"""


def _block(bid: str) -> str:
    b = BLOCKS[bid]
    links = "".join(
        f'<a href="{_e(url)}" target="_self">{_e(label)}</a>'
        for label, url in b["pages"]
    )
    klass = "otx-core" if b["tier"] == "core" else "otx-blk"
    return (
        f'<div id="b-{_e(bid)}" class="{klass}">'
        f'<div class="otx-cap">{_e(b["cap"])}</div>'
        f'<div class="otx-line"><span class="r">{_e(b["rest"])}</span>'
        f'<span class="h">{_e(b["hover"])}</span></div>'
        f'<div class="otx-links">{links}</div>'
        f'</div>'
    )


def render_stack(capabilities: Sequence[Any] = ()) -> str:
    """The whole diagram as one HTML string, ready for st.markdown.

    ``capabilities`` accepts either a plain label (rendered as static text)
    or a ``(label, url)`` pair, which becomes a link to the page that
    implements that capability — so a chip is only styled as clickable when
    it actually goes somewhere.
    """
    core = _block("ontology")
    if capabilities:
        parts = []
        for cap in capabilities:
            if isinstance(cap, (tuple, list)) and len(cap) == 2:
                label, url = cap
                parts.append(
                    f'<a href="{_e(url)}" target="_self">{_e(label)}</a>')
            else:
                parts.append(f"<span>{_e(cap)}</span>")
        pills = "".join(parts)
        # Insert before the block's own closing tag.
        core = core[: -len("</div>")] + f'<div class="otx-pills">{pills}</div></div>'

    flow = '<div class="otx-flow"><i></i><i></i><i></i></div>'
    return (
        _css()
        + '<div class="otx">'
        + '<div class="otx-rail">What the operator works with</div>'
        + '<div class="otx-tier otx-reveal">'
        + _block("register") + _block("model") + _block("reports")
        + '</div>' + flow
        + '<div class="otx-rail">What reasons over the evidence</div>'
        + '<div class="otx-slab otx-reveal">'
        + f'<div class="side">{_block("sparql")}</div>'
        + f'<div class="mid">{core}</div>'
        + f'<div class="side">{_block("governance")}</div>'
        + '</div>' + flow
        + '<div class="otx-rail">Where the evidence comes from</div>'
        + '<div class="otx-tier otx-reveal">'
        + _block("asset") + _block("extraction") + _block("standards")
        + '</div>'
        + '</div>'
    )
