"""
Application styling — a single, cohesive design system
=====================================================

One stylesheet for the whole dashboard, aimed at the look an asset owner
expects from operational software: quiet surfaces, a disciplined type
scale, tabular figures, and clear focus/hover states.

Design notes
------------
* **Typography** uses the platform UI stack (Segoe UI Variable on Windows
  11) rather than a web font, so the app stays fast and fully offline —
  the same constraint that shapes the rest of the build. Numerals are set
  ``tabular-nums`` wherever figures are compared (metrics, tables), so
  columns of numbers align.
* **Scale** is deliberately tighter than Streamlit's defaults: the earlier
  48 px headings pushed content below the fold and made the pages feel
  like slides rather than a console.
* **Colour** is defined once as custom properties. The violet primary
  matches ``.streamlit/config.toml``; semantic colours carry priority and
  status meaning consistently across pages.

Maintenance warning
-------------------
Do **not** style ``[data-testid="stSidebarNav"]``. Streamlit computes its
item heights in JS, and overriding padding/font there causes overlapping
and duplicated page labels. Only ``stSidebarUserContent`` is safe.
"""

import streamlit as st

_CSS = """
<style>
/* ============================================================ tokens === */
:root {
  --brand:        #534AB7;
  --brand-dark:   #423AA0;
  --brand-tint:   #EFEDFA;

  --ink:          #16181D;
  --ink-soft:     #5C6270;
  --ink-faint:    #858A96;

  --canvas:       #FBFAF6;
  --surface:      #FFFFFF;
  --panel:        #F5F4EF;
  --line:         #E3E1D9;
  --line-strong:  #CFCCC0;

  --ok:           #1D7A54;
  --warn:         #9A6700;
  --danger:       #B3261E;
  --info:         #1F6FEB;

  --radius:       10px;
  --radius-sm:    7px;
  --shadow-sm:    0 1px 2px rgba(22,24,29,.06);
  --shadow-md:    0 2px 8px rgba(22,24,29,.08);

  --font-ui: "Segoe UI Variable Text", "Segoe UI", Inter, -apple-system,
             BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-display: "Segoe UI Variable Display", "Segoe UI", Inter,
             -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
  --font-mono: "Cascadia Code", "JetBrains Mono", Consolas,
             "SF Mono", Menlo, monospace;
}

/* ============================================================== base === */
html, body, .stApp {
  font-family: var(--font-ui) !important;
  font-size: 17px !important;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.stApp { color: var(--ink); background: var(--canvas); }

.block-container {
  padding-top: 2.1rem;
  padding-bottom: 3rem;
  max-width: 1480px;
}

/* Headings — tighter, display face, slight optical tightening. */
h1, [data-testid="stMarkdownContainer"] h1 {
  font-family: var(--font-display) !important;
  font-weight: 700 !important;
  font-size: 34px !important;
  line-height: 1.16 !important;
  letter-spacing: -0.02em !important;
  color: var(--ink) !important;
}
h2, [data-testid="stMarkdownContainer"] h2 {
  font-family: var(--font-display) !important;
  font-weight: 650 !important;
  font-size: 25px !important;
  line-height: 1.22 !important;
  letter-spacing: -0.012em !important;
  margin-top: 0.4em !important;
}
h3, [data-testid="stMarkdownContainer"] h3 {
  font-family: var(--font-display) !important;
  font-weight: 650 !important;
  font-size: 20px !important;
  line-height: 1.3 !important;
  letter-spacing: -0.006em !important;
}

p, li, label,
[data-testid="stMarkdownContainer"] p,
.stMarkdown {
  font-size: 17px !important;
  line-height: 1.6 !important;
}
/* Paragraphs use the full column width — no artificial measure cap, which
   otherwise leaves a wide blank gutter on large monitors. */

/* Captions — the app leans on these for the plain-English layer. */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
  font-size: 15.5px !important;
  line-height: 1.5 !important;
  color: var(--ink-soft) !important;
}

a, a:visited { color: var(--brand-dark); text-decoration-thickness: 1px; }
a:hover { color: var(--brand); }

hr { border-color: var(--line) !important; margin: 1.4rem 0 !important; }

/* ============================================================ sidebar === */
/* Only the user-content area: never the nav (see module docstring). */
[data-testid="stSidebar"] {
  background: var(--panel);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebarUserContent"] * { font-size: 16px !important; }
[data-testid="stSidebarUserContent"] h4 {
  font-family: var(--font-display) !important;
  font-size: 19px !important;
  letter-spacing: -0.01em;
  margin-bottom: .1rem !important;
}

/* ============================================================ metrics === */
[data-testid="stMetric"] {
  background: var(--surface);
  padding: 18px 20px 16px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  transition: box-shadow .15s ease, border-color .15s ease;
}
[data-testid="stMetric"]:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--line-strong);
}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
  font-size: 15px !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  color: var(--ink-soft) !important;
  /* keep long labels wrapping rather than clipped */
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  line-height: 1.3 !important;
}
/* Reserve two label lines so cards in a row line their figures up. */
[data-testid="stMetricLabel"] { min-height: 2.7em; }
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
  font-family: var(--font-display) !important;
  font-size: 34px !important;
  font-weight: 700 !important;
  color: var(--ink) !important;
  line-height: 1.08 !important;
  letter-spacing: -0.02em !important;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}
/* Delta chip: let it wrap instead of truncating ("3 need attenti…"). */
[data-testid="stMetricDelta"] {
  white-space: normal !important;
  overflow: visible !important;
  margin-top: 2px;
}
[data-testid="stMetricDelta"] * {
  font-size: 14.5px !important;
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  line-height: 1.35 !important;
}

/* Equal-height cards across a row: stretch the column, push the figure to
   a common baseline, and let any delta sit at the bottom. */
[data-testid="stHorizontalBlock"] { align-items: stretch; }
[data-testid="stColumn"] > div,
[data-testid="stColumn"] [data-testid="stVerticalBlock"] { height: 100%; }
[data-testid="stMetric"] {
  height: 100%;
  display: flex;
  flex-direction: column;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] { margin-top: auto; }

/* ========================================================= components === */
/* Buttons */
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button {
  font-family: var(--font-ui) !important;
  font-size: 16.5px !important;
  font-weight: 600 !important;
  min-height: 44px !important;
  padding: .55rem 1.15rem !important;
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--line-strong) !important;
  background: var(--surface);
  color: var(--ink) !important;
  transition: background .14s ease, border-color .14s ease,
              box-shadow .14s ease, transform .06s ease;
}
[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  border-color: var(--brand) !important;
  color: var(--brand-dark) !important;
  box-shadow: var(--shadow-sm);
}
[data-testid="stButton"] button:active,
[data-testid="stDownloadButton"] button:active { transform: translateY(1px); }

/* Primary action */
[data-testid="stButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background: var(--brand) !important;
  border-color: var(--brand) !important;
  color: #FFFFFF !important;
  box-shadow: var(--shadow-sm);
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
  background: var(--brand-dark) !important;
  border-color: var(--brand-dark) !important;
  color: #FFFFFF !important;
  box-shadow: var(--shadow-md);
}

/* Visible keyboard focus everywhere (accessibility) */
:focus-visible,
[data-testid="stButton"] button:focus-visible,
[data-testid="stDownloadButton"] button:focus-visible {
  outline: 2px solid var(--brand) !important;
  outline-offset: 2px !important;
}

/* Inputs */
[data-testid="stWidgetLabel"] * {
  font-size: 16px !important;
  font-weight: 600 !important;
  color: var(--ink) !important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div {
  font-size: 16.5px !important;
  color: var(--ink) !important;
  background: var(--surface) !important;
  border-color: var(--line-strong) !important;
  border-radius: var(--radius-sm) !important;
  box-shadow: none !important;
}
[data-baseweb="select"] > div { min-height: 48px !important; }
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px var(--brand-tint) !important;
}
[data-baseweb="select"] input { font-size: 16.5px !important; }

/* Dropdown menu — keep full contrast (Streamlit dims these by default) */
[data-baseweb="popover"] *,
[data-baseweb="popover"] [role="option"],
[data-baseweb="popover"] li {
  font-size: 16.5px !important;
  color: var(--ink) !important;
  filter: none !important;
  text-shadow: none !important;
  opacity: 1 !important;
}
[data-baseweb="popover"] [role="option"]:hover { background: var(--brand-tint) !important; }

/* Multiselect tags */
[data-baseweb="tag"] {
  min-height: 32px !important;
  border-radius: var(--radius-sm);
  background: var(--brand-tint) !important;
  color: var(--brand-dark) !important;
  border: 1px solid rgba(83,74,183,.22) !important;
}
[data-baseweb="tag"] span { font-size: 15.5px !important; font-weight: 600; }

/* Radio / checkbox — comfortable hit targets */
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
  min-height: 38px !important;
  align-items: center;
  font-size: 16.5px !important;
  color: var(--ink) !important;
}
[data-testid="stRadio"] label *,
[data-testid="stCheckbox"] label * { font-size: 16.5px !important; }

/* File uploader */
[data-testid="stFileUploader"] section {
  border: 1.5px dashed var(--line-strong) !important;
  border-radius: var(--radius) !important;
  background: var(--surface) !important;
  transition: border-color .15s ease, background .15s ease;
}
[data-testid="stFileUploader"] section:hover {
  border-color: var(--brand) !important;
  background: var(--brand-tint) !important;
}
[data-testid="stFileUploader"] * { font-size: 16px !important; }

/* Tabs — used for the Overview's How-to-use / How-it-works split */
[data-baseweb="tab-list"] {
  gap: 4px;
  border-bottom: 1px solid var(--line) !important;
}
[data-baseweb="tab"] {
  font-size: 16.5px !important;
  font-weight: 600 !important;
  color: var(--ink-soft) !important;
  padding: .55rem 1rem !important;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}
[data-baseweb="tab"]:hover { background: var(--brand-tint) !important; color: var(--brand-dark) !important; }
[data-baseweb="tab"][aria-selected="true"] { color: var(--brand-dark) !important; }
[data-baseweb="tab-highlight"] { background: var(--brand) !important; height: 3px !important; }

/* Expanders — quiet cards */
[data-testid="stExpander"] {
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
[data-testid="stExpander"] summary { font-size: 16.5px !important; font-weight: 600 !important; }
[data-testid="stExpander"] summary:hover { color: var(--brand-dark) !important; }

/* Alerts — semantic left rail instead of a flat wash */
[data-testid="stAlert"] {
  border-radius: var(--radius) !important;
  border: 1px solid var(--line) !important;
  border-left-width: 4px !important;
  box-shadow: var(--shadow-sm);
}
[data-testid="stAlert"] * { font-size: 16.5px !important; line-height: 1.55 !important; }

/* Tables and editable grids — tabular figures, calmer headers */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
  font-size: 16px !important;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  font-variant-numeric: tabular-nums;
}
[data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataEditor"] [role="gridcell"] {
  font-size: 15px !important;
  color: var(--ink) !important;
}
[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stDataEditor"] [role="columnheader"] {
  font-size: 14px !important;
  font-weight: 700 !important;
  letter-spacing: .02em;
  color: var(--ink-soft) !important;
  background: var(--panel) !important;
}
[data-testid="stDataFrame"] canvas,
[data-testid="stDataEditor"] canvas { image-rendering: auto; }

/* Code */
code {
  font-family: var(--font-mono) !important;
  background: #F1EFE8;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 15px !important;
  color: #3A3550;
}
[data-testid="stCode"] * { font-family: var(--font-mono) !important; font-size: 14.5px !important; }

/* Charts sit on the surface, not the canvas */
[data-testid="stPlotlyChart"],
[data-testid="stGraphVizChart"] {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 8px;
  box-shadow: var(--shadow-sm);
}

/* Bordered containers (st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--radius) !important;
  border-color: var(--line) !important;
  background: var(--surface);
}

/* Progress / spinner in brand colour */
[data-testid="stProgress"] > div > div > div > div { background: var(--brand) !important; }

/* ===================================================== legacy helpers === */
/* Retained for any dynamically built markup. */
.badge-high { color: #791F1F; background: #FCEBEB; padding: 5px 11px; border-radius: 999px; font-size: 15px; font-weight: 700; }
.badge-med  { color: #633806; background: #FAEEDA; padding: 5px 11px; border-radius: 999px; font-size: 15px; font-weight: 700; }
.badge-low  { color: #27500A; background: #EAF3DE; padding: 5px 11px; border-radius: 999px; font-size: 15px; font-weight: 700; }
.completeness-bar { height: 6px; background: #E5E4DE; border-radius: 3px; overflow: hidden; }
.completeness-fill { height: 100%; border-radius: 3px; }
.fill-high { background: var(--ok); }
.fill-med  { background: var(--warn); }
.fill-low  { background: var(--danger); }

/* Page help control: the "?" beside a page's orientation line. Rendered as
   a quiet circular icon button so it reads as assistance, not an action. */
[data-testid="stPopover"] button {
  min-height: 30px !important;
  height: 30px !important;
  width: 30px !important;
  min-width: 30px !important;
  padding: 0 !important;
  border-radius: 50% !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  color: var(--ink-faint) !important;
  border: 1px solid var(--line-strong) !important;
  background: var(--surface) !important;
}
[data-testid="stPopover"] button:hover {
  color: #FFFFFF !important;
  background: var(--brand) !important;
  border-color: var(--brand) !important;
}
[data-testid="stPopover"] button p { font-size: 15px !important; font-weight: 700 !important; }

/* Deep-link targets: keep the anchored row clear of the top chrome, and
   give the landing section a brief highlight so the jump is obvious. */
.dd-anchor { position: relative; top: -90px; height: 0; }
[data-testid="stHeading"] > * { scroll-margin-top: 90px; }
:target { scroll-margin-top: 90px; }
@keyframes dd-flash {
  from { background: rgba(83,74,183,.14); }
  to   { background: transparent; }
}
.dd-anchor:target + div,
[data-testid="stHeading"]:target { animation: dd-flash 1.6s ease-out 1; }

/* Chrome we don't want */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

/* Respect reduced-motion preferences */
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}

/* Narrow screens: reclaim horizontal padding */
@media (max-width: 900px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  h1, [data-testid="stMarkdownContainer"] h1 { font-size: 28px !important; }
  [data-testid="stMetricValue"], [data-testid="stMetricValue"] * { font-size: 28px !important; }
}
</style>
"""


def apply_custom_css() -> None:
    """Inject the application stylesheet. Called once per page, at the top."""
    st.markdown(_CSS, unsafe_allow_html=True)
