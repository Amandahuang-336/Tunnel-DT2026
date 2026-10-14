"""
Report — page 8
===============

One click turns the whole session into a board-ready PDF: KPIs, the
BIM 3-D model image, the full defect register, a case file per defect
(evidence → FMEA chain → prescribed intervention → cost build-up),
survey coverage, and the standards library behind the prescriptions.

Two versions are offered: A, a one-page coloured summary, and B, the
comprehensive report. Both are built from the same figure panel and the
same totals, so they cannot disagree, and each names the other.

Output is a real PDF, printed from self-contained HTML by headless
Chrome or Edge. The HTML is offered too: it opens in any browser,
works offline, and prints to the same PDF with Ctrl+P. No LaTeX
installation is required.
"""

import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.ontology_loader import load_ontology, load_defects
from utils.styling import apply_custom_css
from utils.explainers import render_plain_guide
from utils.gis import list_tunnels
from utils.bim import get_tunnel_record
from utils.report_html import (
    generate_onepager_html, generate_full_html, generate_deck_html,
    build_inspection_html, html_to_pdf,
)
from utils import change_report, governance, inspection_report
from utils.demo_mode import rate_limit


def _allow(action: str) -> bool:
    """Rate-gate an expensive render/compile. Always true for trusted
    (non public-demo) deployments; see utils/demo_mode.py."""
    ok, wait = rate_limit(action, max_calls=3, window_s=300)
    if not ok:
        st.warning(
            f"Document generation is rate-limited on this public "
            f"deployment. Please try again in {wait} s."
        )
    return ok

apply_custom_css()

if "graph" not in st.session_state:
    st.session_state.graph = load_ontology()
    st.session_state.defects = load_defects(st.session_state.graph)

st.title("Report & presentation")
st.caption(
    "Generate a single PDF capturing everything in this session — "
    "inputs, outputs, the BIM model image, and every defect's case "
    "file — so nobody has to click through the app to see the results."
)

render_plain_guide(
    "Pick the tunnel, press **Generate report** for the full PDF — or "
    "**Generate presentation** lower down for a slide deck. Defects "
    "registered via Ingest this session are included automatically."
)

# -----------------------------------------------------------------------------
# Options
# -----------------------------------------------------------------------------
tunnels = list_tunnels()
if not tunnels:
    st.error("No tunnel geometry found — check data/tunnel_geometry.json.")
    st.stop()
label_to_tunnel = {t["label"]: t for t in tunnels}
labels = list(label_to_tunnel.keys())
# Default to the tunnel chosen in the sidebar so the report follows the
# asset the operator is working on — not always Tunnel A.
active_label = st.session_state.get("current_tunnel")
default_idx = labels.index(active_label) if active_label in labels else 0

col1, col2 = st.columns([2, 2])
with col1:
    picked_label = st.selectbox(
        "Tunnel", options=labels, index=default_idx,
        help="Defaults to the active tunnel in the sidebar. The report "
             "covers this tunnel and the defects logged against it.",
    )
with col2:
    include_cases = st.checkbox(
        "Include per-defect case files",
        value=True,
        help="Evidence, FMEA chain, prescribed intervention and cost "
             "build-up for every defect. Uncheck for a short summary-only "
             "report.",
    )

with st.expander("Specialist sections (outputs from the expert tools)",
                 expanded=False):
    st.caption(
        "Append the Specialist tools' outputs as extra report sections — "
        "so the PDF shows the evidence, not just the headline numbers."
    )
    inc_sparql = st.checkbox(
        "Knowledge-base verification (SPARQL competency questions)",
        value=True,
        help="Runs the canned SPARQL queries against the populated graph and "
             "tabulates the answers, so the report's numbers are traceable "
             "to the knowledge base.",
    )
    inc_cobie = st.checkbox(
        "COBie data-handover rows",
        value=True,
        help="This tunnel's defects as COBie Component + measurement rows — "
             "the facility-management handover format.",
    )
    inc_ontology = st.checkbox(
        "Knowledge-model summary",
        value=True,
        help="Counts of classes, properties and the FMEA chain that back "
             "the prescriptions.",
    )

tunnel = label_to_tunnel[picked_label]
tunnel_id = tunnel["tunnel_id"]
defects = [d for d in st.session_state.defects
           if d.get("tunnel_id", "TUN-A") == tunnel_id]

st.caption(
    f"Report will cover **{len(defects)} defect(s)** on "
    f"**{picked_label}** — including any registered this session."
)
if not defects:
    st.warning(
        f"**{picked_label}** has no defects registered yet, so the report "
        f"will be a setup summary — title, BIM model image and tunnel "
        f"parameters, with an empty defect register. Log findings on the "
        f"**4 · Ingest** page first, then come back and regenerate."
    )

# Both documents are named up front so each can point at the other.
_job = tunnel_id.replace("-", "_")
ONEPAGER_PDF = f"{_job}_onepager.pdf"
FULL_PDF = f"{_job}_report.pdf"

st.markdown("**Choose a version**")
st.caption(
    "Both are generated from the same register and share the same figure "
    "panel, so they cannot disagree. Each names the other, so whoever "
    "receives one knows where the rest is."
)

ver_a, ver_b = st.columns(2)

with ver_a:
    st.markdown("##### A · One-pager")
    st.caption(
        "A single coloured page for an asset manager or a board pack — map, "
        "lining model, where the defects sit, priority mix, cost exposure, "
        "and the actions with their estimates."
    )
    max_actions = st.slider(
        "Actions listed", min_value=4, max_value=15, value=8,
        help="The most urgent defects, ordered by priority then cost. The "
             "rest stay in the comprehensive report.",
    )
    if st.button("Generate one-pager", type="primary",
                 key="gen_onepager") and _allow("onepager"):
        with st.spinner("Rendering the panel and printing the page…"):
            st.session_state.onepager_artifacts = generate_onepager_html(
                tunnel=tunnel,
                bim_tunnel=get_tunnel_record(tunnel_id),
                defects=defects,
                issued_on=date.today(),
                full_report_name=FULL_PDF,
                max_actions=max_actions,
            )

with ver_b:
    st.markdown("##### B · Comprehensive")
    st.caption(
        "Everything above plus the per-defect case files, evidence, FMEA "
        "chain, cost build-ups and the specialist sections selected above. "
        "Now coloured, and it opens on the same panel as the one-pager."
    )
    st.caption("")  # keep the two columns' buttons on the same baseline
    if st.button("Generate comprehensive report", type="primary",
                 key="gen_full") and _allow("full_report"):
        with st.spinner("Rendering the figures and printing the PDF…"):
            st.session_state.report_artifacts = generate_full_html(
                tunnel=tunnel,
                bim_tunnel=get_tunnel_record(tunnel_id),
                defects=defects,
                issued_on=date.today(),
                onepager_name=ONEPAGER_PDF,
                include_case_files=include_cases,
            )

# ---- version A output -------------------------------------------------------
one = st.session_state.get("onepager_artifacts")
if one:
    st.divider()
    st.markdown("#### A · One-pager")
    if one["pdf"]:
        st.success(f"One-pager ready — {len(one['pdf']) / 1e6:.2f} MB PDF.")
    else:
        st.info(one["message"])
    st.image(one["panel"], caption="Figure panel used by both versions",
             use_container_width=True)
    o1, o2, o3 = st.columns(3)
    with o1:
        if one["pdf"]:
            st.download_button(
                "📄 Download PDF", data=one["pdf"],
                file_name=f"{one['jobname']}.pdf", mime="application/pdf")
    with o2:
        st.download_button(
            "🌐 Download web page (HTML)",
            data=one["html"].encode("utf-8"),
            file_name=f"{one['jobname']}.html", mime="text/html",
            help="Self-contained — opens in any browser, works offline, and "
                 "prints to PDF with Ctrl+P.")
    with o3:
        st.download_button(
            "🖼️ Download panel (PNG)", data=one["panel"],
            file_name=f"{one['jobname']}_panel.png", mime="image/png")

art = st.session_state.get("report_artifacts")
if art:
    st.divider()
    st.markdown("#### B · Comprehensive report")
    if art["pdf"]:
        st.success(
            f"Report ready — {len(art['pdf']) / 1e6:.1f} MB PDF, "
            f"including the lining model and "
            f"{'per-defect case files' if include_cases else 'summary sections'}."
        )
    else:
        st.info(art["message"])

    c1, c2, c3 = st.columns(3)
    with c1:
        if art["pdf"]:
            st.download_button(
                "📄 Download PDF",
                data=art["pdf"],
                file_name=f"{art['jobname']}.pdf",
                mime="application/pdf",
            )
    with c2:
        st.download_button(
            "🌐 Download web page (HTML)",
            data=art["html"].encode("utf-8"),
            file_name=f"{art['jobname']}.html",
            mime="text/html",
            help="Self-contained — opens in any browser, works offline, and "
                 "prints to PDF with Ctrl+P.",
        )
    with c3:
        st.download_button(
            "🖼️ Download panel (PNG)",
            data=art["panel"],
            file_name=f"{art['jobname']}_panel.png",
            mime="image/png",
        )

    with st.expander("Preview — lining model used in the report"):
        st.image(art["bim"], use_container_width=True)

st.caption(
    "The report's References section cites the standards behind every "
    "prescription — browse and download them on the 📚 **Standards "
    "Library** page (step 7)."
)

st.divider()

# =============================================================================
# Condition inspection report — chain-structured, authority format
# =============================================================================
st.subheader("Condition inspection report")
st.caption(
    "The report above is a session summary. This one is the operator's "
    "deliverable: one defect sheet per defect, structured by the seven FMEA "
    "chain levels, with each assessment resolving to the clause **and edition** "
    "that states its threshold."
)

with st.expander("How the chain maps onto the report", expanded=False):
    st.dataframe(
        pd.DataFrame(inspection_report.chain_mapping_rows()),
        use_container_width=True, hide_index=True,
    )
    st.caption(
        "The chain traversal is the report's narrative structure — no "
        "intermediate authoring stage is required."
    )

ic1, ic2 = st.columns([2, 2])
with ic1:
    inspector = st.text_input("Inspector / reviewing engineer", value="")
with ic2:
    issued_on = st.date_input("Issue date", value=date.today(),
                              help="Supplied explicitly so the render is "
                                   "deterministic — two issues differ only "
                                   "where the evidence differs.")

# ---- optional inter-cycle change report ------------------------------------
st.markdown("**Inter-cycle change report** (optional)")
st.caption(
    "Classifies every defect against the previous cycle: New, Escalated, "
    "Stable, Repaired-holding, Repaired-recurred. Requires a previous-cycle "
    "snapshot and an association tolerance."
)

cc1, cc2 = st.columns([2, 2])
with cc1:
    prev_file = st.file_uploader(
        "Previous cycle (JSON defect register)", type=["json"],
        key="prev_cycle",
        help="Export a cycle with the button below, then upload it here at "
             "the next inspection.",
    )
with cc2:
    tolerance_m = st.number_input(
        "Association tolerance (m)", min_value=0.0, value=0.0, step=0.1,
        help="Operator-supplied. Derive it from a registration-accuracy study "
             "on the asset — no default is assumed, and 0 disables the "
             "change report.",
    )

st.download_button(
    "Export this cycle as a snapshot (JSON)",
    data=json.dumps(defects, indent=2, default=str),
    file_name=f"{tunnel_id}_cycle_{issued_on.isoformat()}.json",
    mime="application/json",
    help="Keep this; upload it as the previous cycle at the next inspection.",
)

change_rows = change_ambiguities = None
effective_tol = None
if prev_file is not None and tolerance_m > 0:
    try:
        previous = json.loads(prev_file.getvalue().decode("utf-8"))
        change_rows, change_ambiguities = change_report.classify_cycle(
            defects, previous, tolerance_m=tolerance_m)
        effective_tol = tolerance_m
        counts = change_report.summarise(change_rows)
        mcols = st.columns(len(counts))
        for col, (state, count) in zip(mcols, counts.items()):
            col.metric(state, count)
        if change_ambiguities:
            st.warning(
                f"{len(change_ambiguities)} ambiguous association(s) — more "
                "than one predecessor within tolerance. Not merged; deferred "
                "to Investigation_Required for adjudication."
            )
        rate = change_report.reintervention_rate(change_rows)
        if rate is None:
            st.info(
                "Re-intervention rate is not computable: no repaired "
                "predecessor is present in the comparison set."
            )
        else:
            st.metric("Re-intervention rate", f"{rate * 100:.1f}%")
    except json.JSONDecodeError as exc:
        st.error(f"Previous-cycle file is not valid JSON: {exc}")
    except change_report.ToleranceNotConfigured as exc:
        st.error(str(exc))
elif prev_file is not None and tolerance_m == 0:
    st.info(
        "A previous cycle is loaded but the association tolerance is 0, so "
        "identity resolution is disabled. Set a tolerance derived from your "
        "asset's registration accuracy to enable the change report."
    )

if st.button("Generate inspection report", type="primary",
             key="gen_inspection") and _allow("inspection"):
    with st.spinner("Rendering defect sheets from the FMEA chain…"):
        html_source = build_inspection_html(
            tunnel=tunnel,
            defects=defects,
            graph=st.session_state.graph,
            issued_on=issued_on,
            inspector=inspector,
            change_rows=change_rows,
            change_ambiguities=change_ambiguities,
            tolerance_m=effective_tol,
        )
        jobname = f"{tunnel_id}_inspection_report".replace("-", "_")
        pdf, message = html_to_pdf(html_source, jobname)
        st.session_state.inspection_artifacts = {
            "html": html_source, "pdf": pdf,
            "message": message, "jobname": jobname,
        }

insp = st.session_state.get("inspection_artifacts")
if insp:
    unbound = governance.unbound_clause_references(st.session_state.graph, defects)
    if unbound:
        st.warning(
            f"{len(unbound)} assessment(s) cite a clause not bound to a dated "
            "edition. These are flagged in the sheets and cannot be "
            "reconstructed after a revision — see the **Governance** page."
        )
    if insp["pdf"]:
        st.success(
            f"Inspection report ready — {len(insp['pdf']) / 1e6:.2f} MB PDF.")
    else:
        st.info(insp["message"])
    d1, d2 = st.columns(2)
    with d1:
        if insp["pdf"]:
            st.download_button(
                "📄 Download PDF",
                data=insp["pdf"],
                file_name=f"{insp['jobname']}.pdf",
                mime="application/pdf",
            )
    with d2:
        st.download_button(
            "🌐 Download web page (HTML)",
            data=insp["html"].encode("utf-8"),
            file_name=f"{insp['jobname']}.html",
            mime="text/html",
            help="Self-contained — opens in any browser, works offline, and "
                 "prints to PDF with Ctrl+P.",
        )

st.divider()
st.subheader("Presentation (slide deck)")
st.caption(
    "A board-ready **landscape slide deck** of the same session — title, "
    "where we stand, the asset and its defects, the lining model, the "
    "recommendations and the method. Same figures as the reports, so the "
    "deck cannot disagree with them."
)

if st.button("Generate presentation", type="primary",
             key="gen_presentation") and _allow("presentation"):
    with st.spinner("Building the slides and printing the PDF…"):
        st.session_state.presentation_artifacts = generate_deck_html(
            tunnel=tunnel,
            bim_tunnel=get_tunnel_record(tunnel_id),
            defects=defects,
            issued_on=date.today(),
        )

pres = st.session_state.get("presentation_artifacts")
if pres:
    if pres["pdf"]:
        st.success(f"Slide deck ready — {len(pres['pdf']) / 1e6:.1f} MB PDF.")
    else:
        st.info(pres["message"])
    p1, p2 = st.columns(2)
    with p1:
        if pres["pdf"]:
            st.download_button(
                "📊 Download slide deck (PDF)",
                data=pres["pdf"],
                file_name=f"{pres['jobname']}.pdf",
                mime="application/pdf",
                key="dl_pres_pdf",
            )
    with p2:
        st.download_button(
            "🌐 Download slides (HTML)",
            data=pres["html"].encode("utf-8"),
            file_name=f"{pres['jobname']}.html",
            mime="text/html",
            key="dl_pres_html",
            help="Self-contained — opens in any browser. Print with Ctrl+P "
                 "(landscape) for the same deck.",
        )
