"""
Standards Library — page 9
==========================

Step 7 of the workflow: after a defect is diagnosed, this is where
the operator pulls the source guideline or standard for further
information. Lists the documents found in the optional local
library folder (see utils/library.py), mapped to what each one backs
in the app, with per-document download.
"""

import pandas as pd
import streamlit as st

from utils.styling import apply_custom_css
from utils.explainers import render_plain_guide
from utils.library import list_library, dataset_summary

apply_custom_css()

st.title("Standards library")
st.caption(
    "The guidelines, standards and datasets behind every threshold, "
    "repair method and data format in this app. The standards are "
    "copyrighted and not distributed; add your own copies to the "
    "local library folder."
)

render_plain_guide(
    "Every repair the app prescribes cites one of these documents "
    "(the codes you see on Defect Detail, e.g. *AASHTO Ch16 §16.4.3*). "
    "Pick a document below and download it for the full context."
)

library = list_library()
if not library:
    st.info(
        "No library documents found. Place your copies of the standards "
        "in `library/standards/` (or set `TUNNEL_DT_LIBRARY`); see the "
        "README."
    )
    st.stop()

st.dataframe(
    pd.DataFrame([{
        "Document": e["label"],
        "Used for": e["used_for"],
        "File": e["filename"],
        "Size (MB)": (round(e["size_mb"], 1)
                      if e["size_mb"] is not None else None),
    } for e in library]),
    hide_index=True,
    width="stretch",
)

pick = st.selectbox(
    "Open a document",
    options=[e["label"] for e in library],
    help="Pick a document, then download it with the button below. "
         "Cloud-synced files may take a moment to download.",
)
entry = next(e for e in library if e["label"] == pick)
try:
    st.download_button(
        f"Download — {entry['filename']}",
        data=entry["path"].read_bytes(),
        file_name=entry["filename"],
    )
except OSError:
    st.warning(
        f"`{entry['filename']}` could not be read (it may be a "
        f"cloud-only placeholder) — sync the library folder, then retry."
    )

ds = dataset_summary()
if ds.get("exists"):
    st.caption(
        f"📂 Local inspection dataset: "
        f"{ds['n_files']} files · {ds['size_mb']:.0f} MB · located in "
        f"`{ds['path']}` (browse it directly — too large to serve "
        f"through the app)."
    )
