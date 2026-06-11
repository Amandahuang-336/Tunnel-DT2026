"""
Report — page 8
===============

One click turns the whole session into a board-ready PDF: KPIs, the
BIM 3-D model image, the full defect register, a case file per defect
(evidence → FMEA chain → prescribed intervention → cost build-up),
survey coverage, and the standards library behind the prescriptions.

LaTeX is compiled locally (MiKTeX / TeX Live), following the same
generator pattern as the Tri-HB app. If no TeX engine is installed
the .tex source and figures are offered instead.
"""

import pandas as pd
import streamlit as st

from utils.ontology_loader import load_ontology, load_defects
from utils.styling import apply_custom_css
from utils.explainers import render_plain_guide
from utils.gis import list_tunnels
from utils.bim import get_tunnel_record
from utils.report import generate_report
from utils.library import list_library, dataset_summary

apply_custom_css()

if "graph" not in st.session_state:
    st.session_state.graph = load_ontology()
    st.session_state.defects = load_defects(st.session_state.graph)

st.title("Report")
st.caption(
    "Generate a single PDF capturing everything in this session — "
    "inputs, outputs, the BIM model image, and every defect's case "
    "file — so nobody has to click through the app to see the results."
)

render_plain_guide(
    "Pick the tunnel, press **Generate report**, download the PDF. "
    "Defects registered via Ingest this session are included "
    "automatically."
)

# -----------------------------------------------------------------------------
# Options
# -----------------------------------------------------------------------------
tunnels = list_tunnels()
if not tunnels:
    st.error("No tunnel geometry found — check data/tunnel_geometry.json.")
    st.stop()
label_to_tunnel = {t["label"]: t for t in tunnels}

col1, col2 = st.columns([2, 2])
with col1:
    picked_label = st.selectbox("Tunnel", options=list(label_to_tunnel.keys()))
with col2:
    include_cases = st.checkbox(
        "Include per-defect case files",
        value=True,
        help="Evidence, FMEA chain, prescribed intervention and cost "
             "build-up for every defect. Uncheck for a short summary-only "
             "report.",
    )

tunnel = label_to_tunnel[picked_label]
tunnel_id = tunnel["tunnel_id"]
defects = [d for d in st.session_state.defects
           if d.get("tunnel_id", "TUN-A") == tunnel_id]

st.caption(
    f"Report will cover **{len(defects)} defect(s)** on "
    f"**{picked_label}** — including any registered this session."
)

if st.button("Generate report", type="primary"):
    with st.spinner(
        "Building LaTeX, rendering the BIM image, compiling the PDF — "
        "the first run may take a minute while MiKTeX fetches packages…"
    ):
        st.session_state.report_artifacts = generate_report(
            tunnel=tunnel,
            bim_tunnel=get_tunnel_record(tunnel_id),
            defects=defects,
            include_case_files=include_cases,
        )

art = st.session_state.get("report_artifacts")
if art:
    if art["pdf"]:
        st.success(
            f"Report compiled — {len(art['pdf']) / 1e6:.1f} MB PDF, "
            f"including the BIM model image and "
            f"{'per-defect case files' if include_cases else 'summary sections'}."
        )
    else:
        st.warning(
            "PDF could not be compiled on this machine — download the "
            "LaTeX source / ZIP below and compile elsewhere.\n\n"
            f"Details: {art['message']}"
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        if art["pdf"]:
            st.download_button(
                "📄 Download PDF report",
                data=art["pdf"],
                file_name=f"{art['jobname']}.pdf",
                mime="application/pdf",
            )
    with c2:
        st.download_button(
            "Download LaTeX source (.tex)",
            data=art["tex"].encode("utf-8"),
            file_name=f"{art['jobname']}.tex",
            mime="application/x-tex",
        )
    with c3:
        st.download_button(
            "Download ZIP (tex + figures)",
            data=art["zip"],
            file_name=f"{art['jobname']}_bundle.zip",
            mime="application/zip",
        )

    with st.expander("Preview — BIM model image used in the report"):
        st.image(art["png"], use_container_width=True)

# -----------------------------------------------------------------------------
# Reference library — standards and datasets from '2026 Ontology Paper'
# -----------------------------------------------------------------------------
st.divider()
st.subheader("Reference library")
st.caption(
    "The standards and datasets bundled with the project (folder "
    "`2026 Ontology Paper`). These back the app's thresholds, repair "
    "methods and data formats, and are cited in the report's "
    "References section."
)

library = list_library()
if not library:
    st.info(
        "Library folder not found — expected "
        "`2026 Ontology Paper/2. Standards and Technical Specifications` "
        "inside the project."
    )
else:
    st.dataframe(
        pd.DataFrame([{
            "Document": e["label"],
            "Used for": e["used_for"],
            "File": e["filename"],
            "Size (MB)": (round(e["size_mb"], 1)
                          if e["size_mb"] is not None else None),
        } for e in library]),
        hide_index=True,
        use_container_width=True,
    )

    pick = st.selectbox(
        "Open a document",
        options=[e["label"] for e in library],
        help="Pick a document, then download it with the button below.",
    )
    entry = next(e for e in library if e["label"] == pick)
    st.download_button(
        f"Download — {entry['filename']}",
        data=entry["path"].read_bytes(),
        file_name=entry["filename"],
    )

ds = dataset_summary()
if ds.get("exists"):
    st.caption(
        f"📂 Inspection image dataset **BT_Monash-001**: "
        f"{ds['n_files']} files · {ds['size_mb']:.0f} MB · located in the "
        f"project's `2026 Ontology Paper` folder (browse it in Explorer — "
        f"too large to serve through the app)."
    )
