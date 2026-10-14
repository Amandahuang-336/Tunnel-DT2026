"""
HTML report rendering, and PDF via a headless browser
=====================================================

Why not LaTeX
-------------
The LaTeX path only produces a PDF when a TeX distribution is installed, and
when it isn't the user is left holding a `.tex` file they cannot open. This
module produces:

    * a self-contained HTML page  — always works, no dependencies at all,
      images embedded as data URIs so a single file can be emailed or opened
      from anywhere, offline
    * a real PDF                  — printed from that same HTML by headless
      Chrome or Edge, which are already present on most machines

So the two downloads offered are the two the reader actually wants. The LaTeX
generators are kept for anyone who has a TeX engine and wants typeset output,
but they are no longer the only route to a PDF.

Both documents share `report_figures`, so the HTML, the LaTeX and the on-screen
preview all show the same panel and the same totals.
"""

from __future__ import annotations

import base64
import html as _html
import os
import shutil
import subprocess
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from utils import report_figures as rf
from utils.cost_model import estimate_defect_cost, effective_cost

PRIORITY_CSS = {"HIGH": "pri-high", "MEDIUM": "pri-med", "LOW": "pri-low"}


def _e(value: Any) -> str:
    """HTML-escape."""
    return _html.escape("" if value is None else str(value))


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _chainage(value: Any) -> str:
    try:
        return f"K{float(value):.0f}"
    except (TypeError, ValueError):
        return "—"


def _b64(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


# =============================================================================
# Shared stylesheet
# =============================================================================
_CSS = """
:root{
  --high:#D62728; --med:#FF7F0E; --low:#999999;
  --ink:#22223B; --line:#4A4E8F; --soft:#EDEDF5; --muted:#7A7A8C;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink); font-size:10.5pt; line-height:1.45;
  background:#fff;
}
.masthead{
  background:var(--line); color:#fff; padding:12px 16px;
  display:flex; align-items:center; justify-content:space-between;
  border-radius:3px;
}
.masthead h1{margin:0; font-size:19pt; font-weight:700}
.masthead .meta{font-size:10pt; opacity:.92}
.kpis{display:flex; gap:10px; margin:12px 0}
.kpi{
  flex:1; border-radius:3px; padding:12px 8px; text-align:center;
  background:var(--soft);
}
.kpi .v{font-size:22pt; font-weight:700; line-height:1.05}
.kpi .c{font-size:8.5pt; color:var(--ink); margin-top:3px}
.kpi.high{background:rgba(214,39,40,.10)} .kpi.high .v{color:var(--high)}
.kpi.med{background:rgba(255,127,14,.12)} .kpi.med .v{color:var(--med)}
.kpi.line{background:rgba(74,78,143,.10)} .kpi.line .v{color:var(--line)}
.panel{width:100%; margin:6px 0 10px; display:block}
h2{
  color:var(--line); font-size:13pt; margin:18px 0 6px;
  border-bottom:1.5px solid var(--line); padding-bottom:3px;
}
h3{color:var(--ink); font-size:11pt; margin:14px 0 4px}
table{border-collapse:collapse; width:100%; font-size:9pt}
th{
  background:var(--soft); text-align:left; padding:5px 6px;
  border-bottom:1.5px solid var(--line); font-weight:600;
}
td{padding:4px 6px; border-bottom:1px solid #E3E3EC; vertical-align:top}
tr.pri-high td{background:rgba(214,39,40,.055)}
tr.pri-med  td{background:rgba(255,127,14,.06)}
tr.pri-low  td{background:rgba(153,153,153,.06)}
.dot{font-weight:700; margin-right:4px}
.dot.pri-high{color:var(--high)} .dot.pri-med{color:var(--med)}
.dot.pri-low{color:var(--low)}
.num{text-align:right; white-space:nowrap}
.total td{font-weight:700; border-top:1.5px solid var(--line); background:#fff}
.note{font-size:8.5pt; color:var(--muted); margin-top:6px}
.callout{
  background:var(--soft); border-left:3px solid var(--line);
  padding:8px 10px; margin:10px 0; font-size:9.5pt; border-radius:2px;
}
.footer{
  margin-top:14px; padding-top:6px; border-top:1px solid var(--line);
  font-size:8.5pt; color:var(--muted);
}
.case{
  border:1px solid #E3E3EC; border-left:3px solid var(--line);
  border-radius:2px; padding:10px 12px; margin:10px 0;
  break-inside:avoid; page-break-inside:avoid;
}
.case.pri-high{border-left-color:var(--high)}
.case.pri-med{border-left-color:var(--med)}
.case.pri-low{border-left-color:var(--low)}
.case h3{margin-top:0}
.kv{font-size:9pt; margin:3px 0}
.kv b{color:var(--ink)}
.badge{
  display:inline-block; padding:1px 7px; border-radius:9px;
  font-size:8pt; font-weight:700; color:#fff;
}
.badge.pri-high{background:var(--high)} .badge.pri-med{background:var(--med)}
.badge.pri-low{background:var(--low)}

@page{ size:A4; margin:12mm; }
@media print{
  body{-webkit-print-color-adjust:exact; print-color-adjust:exact}
  .page-break{page-break-before:always}
  h2{page-break-after:avoid}
}
"""


def _shell(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{_e(title)}</title><style>{_CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def _masthead(label: str, subtitle: str) -> str:
    return (
        f"<div class='masthead'><h1>{_e(label)}</h1>"
        f"<div class='meta'>{_e(subtitle)}</div></div>"
    )


def _kpis(t: Dict[str, Any]) -> str:
    cells = [
        ("line", str(t["active"]), "Open defects"),
        ("high", str(t["high"]), "Need action ≤ 30 days"),
        ("line", f"{t['confidence_pct']}%", "Diagnostic confidence"),
        ("med", _money(t["cost"]), "12-month cost exposure"),
    ]
    inner = "".join(
        f"<div class='kpi {cls}'><div class='v'>{_e(v)}</div>"
        f"<div class='c'>{_e(c)}</div></div>"
        for cls, v, c in cells
    )
    return f"<div class='kpis'>{inner}</div>"


def _actions_table(actions: Sequence[Dict[str, Any]], total: float,
                   note: str = "") -> str:
    if not actions:
        return "<p class='note'>No defects registered against this tunnel yet.</p>"
    rows = "".join(
        f"<tr class='{PRIORITY_CSS[a['priority']]}'>"
        f"<td><span class='dot {PRIORITY_CSS[a['priority']]}'>●</span>"
        f"{_e(a['defect_id'])}</td>"
        f"<td>{_e(a['defect_type'])}</td>"
        f"<td>{_e(_chainage(a['chainage_m']))}</td>"
        f"<td>{_e(a['action'])}</td>"
        f"<td class='num'>"
        + (f"{int(a['deadline_days'])} d" if a.get("deadline_days") else "—")
        + f"</td><td class='num'>{_e(_money(a['cost']))}</td></tr>"
        for a in actions
    )
    return (
        "<table><thead><tr><th>Defect</th><th>Type</th><th>Ch.</th>"
        "<th>Prescribed action</th><th class='num'>Due</th>"
        "<th class='num'>Est. cost</th></tr></thead><tbody>"
        + rows
        + "<tr class='total'><td colspan='5' class='num'>"
          "Total exposure, all open defects</td>"
          f"<td class='num'>{_e(_money(total))}</td></tr>"
        "</tbody></table>"
        + (f"<p class='note'>{_e(note)}</p>" if note else "")
    )


# =============================================================================
# Version A — one-pager
# =============================================================================
def build_onepager_html(
    tunnel: Dict[str, Any],
    defects: Sequence[Dict[str, Any]],
    panel_png: bytes,
    issued_on: Optional[date] = None,
    full_report_name: Optional[str] = None,
    max_actions: int = 8,
) -> str:
    issued = (issued_on or date.today()).strftime("%d %B %Y")
    label = tunnel.get("label", tunnel.get("tunnel_id", "Tunnel"))
    t = rf.totals(defects)
    actions = rf.prescribed_actions(defects, limit=max_actions)
    hidden = max(0, len(defects) - len(actions))

    note = ""
    if hidden:
        note = (f"Showing the {len(actions)} most urgent of {len(defects)} "
                f"registered defects; the remaining {hidden} appear in the "
                f"comprehensive report.")

    footer = ("Generated from the tunnel digital twin. Every action shown is "
              "derived by traversal of the seven-level FMEA chain and resolves "
              "to the standard clause that prescribes it.")
    if full_report_name:
        footer += f" Full evidence and per-defect case files: {full_report_name}."

    body = (
        _masthead(label, f"Maintenance summary · {issued}")
        + _kpis(t)
        + f"<img class='panel' src='{_b64(panel_png)}' alt='Summary panel'>"
        + "<h2>Prescribed actions</h2>"
        + _actions_table(actions, t["cost"], note)
        + f"<div class='footer'>{_e(footer)}</div>"
    )
    return _shell(f"{label} — maintenance summary", body)


# =============================================================================
# Version B — comprehensive
# =============================================================================
def _case_file_html(d: Dict[str, Any]) -> str:
    priority = (d.get("priority") or "LOW").upper()
    cls = PRIORITY_CSS.get(priority, "pri-low")
    est = estimate_defect_cost(d)

    kv: List[str] = []
    for label, key in [("Failure mechanism", "failure_mechanism"),
                       ("Potential cause", "potential_cause"),
                       ("Threshold triggered", "threshold_triggered"),
                       ("Standard reference", "threshold_reference")]:
        if d.get(key):
            kv.append(f"<div class='kv'><b>{_e(label)}:</b> {_e(d[key])}</div>")

    evidence = d.get("modality_evidence") or {}
    ev_html = ""
    if evidence:
        rows = "".join(
            f"<tr><td>{_e(mod)}</td><td>{_e((e or {}).get('status', '—'))}</td>"
            f"<td>{_e((e or {}).get('finding') or '—')}</td></tr>"
            for mod, e in evidence.items()
        )
        ev_html = ("<table><thead><tr><th>Source</th><th>Status</th>"
                   "<th>Finding</th></tr></thead><tbody>" + rows +
                   "</tbody></table>")

    steps = d.get("prescribed_interventions") or []
    steps_html = ""
    if steps:
        items = "".join(
            f"<li>{_e(s.get('step', ''))}"
            + (f" <span class='note'>({_e(s.get('reference'))})</span>"
               if s.get("reference") else "")
            + "</li>"
            for s in steps
        )
        steps_html = f"<h3>Prescribed intervention</h3><ol>{items}</ol>"

    cost_rows = "".join(
        f"<tr><td>{_e(name)}</td><td class='num'>{_e(_money(amount))}</td></tr>"
        for name, amount in est["lines"]
    )
    recorded = (
        f"Engineer estimate {_money(est['recorded'])} "
        + ("(inside model band)" if est["within_band"]
           else "(outside model band — review scope)")
        if est.get("recorded") else
        "No engineer estimate — modelled figure governs"
    )
    cost_html = (
        "<h3>Cost build-up</h3>"
        f"<p class='note'>{_e(est['method'])}</p>"
        "<table><thead><tr><th>Item</th><th class='num'>AUD</th></tr></thead>"
        "<tbody>" + cost_rows +
        f"<tr class='total'><td>Expected</td>"
        f"<td class='num'>{_e(_money(est['expected']))}</td></tr>"
        f"<tr><td>Band (±{int(est['band_pct'] * 100)}%)</td>"
        f"<td class='num'>{_e(_money(est['low']))} – {_e(_money(est['high']))}</td></tr>"
        "</tbody></table>"
        f"<p class='note'>{_e(recorded)}</p>"
    )

    return (
        f"<div class='case {cls}'>"
        f"<h3><span class='badge {cls}'>{_e(priority)}</span> "
        f"{_e(d.get('defect_id'))} — {_e(d.get('description', ''))}</h3>"
        f"<div class='kv'><b>Location:</b> Ring {_e(d.get('ring_id'))} · "
        f"{_e(_chainage(d.get('chainage_m')))} · {_e(d.get('position', '—'))}"
        f" &nbsp;&nbsp;<b>Severity:</b> {_e(d.get('severity', '—'))}"
        f" &nbsp;&nbsp;<b>Evidence:</b> "
        f"{int(float(d.get('completeness_score') or 0) * 4)}/4</div>"
        + ("<h3>Evidence by sensing source</h3>" + ev_html if ev_html else "")
        + "".join(kv)
        + steps_html
        + cost_html
        + "</div>"
    )


def build_full_html(
    tunnel: Dict[str, Any],
    defects: Sequence[Dict[str, Any]],
    panel_png: bytes,
    bim_png: Optional[bytes] = None,
    issued_on: Optional[date] = None,
    onepager_name: Optional[str] = None,
    include_case_files: bool = True,
) -> str:
    issued = (issued_on or date.today()).strftime("%d %B %Y")
    label = tunnel.get("label", tunnel.get("tunnel_id", "Tunnel"))
    t = rf.totals(defects)

    ordered = sorted(
        defects,
        key=lambda d: ({"HIGH": 0, "MEDIUM": 1}.get(d.get("priority"), 2),
                       str(d.get("defect_id", ""))),
    )

    link = ""
    if onepager_name:
        link = (
            "<div class='callout'><b>Companion document.</b> A one-page "
            "coloured summary of this report — map, lining model, defect "
            "distribution, cost exposure and the prescribed actions — is "
            f"issued alongside it as <code>{_e(onepager_name)}</code>. Both are "
            "generated from the same register, so their figures agree by "
            "construction.</div>"
        )

    register_rows = "".join(
        f"<tr class='{PRIORITY_CSS.get((d.get('priority') or 'LOW').upper(), 'pri-low')}'>"
        f"<td>{_e(d.get('defect_id'))}</td><td>{_e(d.get('defect_type'))}</td>"
        f"<td>{_e(d.get('ring_id'))}</td><td>{_e(_chainage(d.get('chainage_m')))}</td>"
        f"<td>{_e(d.get('position', '—'))}</td>"
        f"<td><span class='dot {PRIORITY_CSS.get((d.get('priority') or 'LOW').upper(), 'pri-low')}'>●</span>"
        f"{_e(d.get('priority', '—'))}</td>"
        f"<td>{int(float(d.get('completeness_score') or 0) * 4)}/4</td>"
        f"<td class='num'>{_e(_money(effective_cost(d)[0]))} "
        f"<span class='note'>({_e(effective_cost(d)[1])})</span></td></tr>"
        for d in ordered
    ) or "<tr><td colspan='8'>No defects registered.</td></tr>"

    body = (
        _masthead(label, f"Inspection & intervention report · {issued}")
        + link
        + "<h2>1. Executive summary</h2>"
        + _kpis(t)
        + f"<p><b>Bottom line:</b> {t['high']} of {t['active']} open defects "
          "need action within 30 days. Cost exposure blends engineer-recorded "
          "estimates with the transparent unit-rate model (basis marked per "
          "defect below).</p>"
        + f"<img class='panel' src='{_b64(panel_png)}' alt='Summary panel'>"
        + "<p class='note'>Alignment and defect locations, lining model, "
          "distribution along the tunnel, priority mix, and estimated cost "
          "exposure. This is the same panel carried by the one-page summary.</p>"
        + "<h2>2. Defect register</h2>"
        + "<table><thead><tr><th>ID</th><th>Type</th><th>Ring</th>"
          "<th>Chainage</th><th>Position</th><th>Priority</th>"
          "<th>Evidence</th><th class='num'>Est. cost (basis)</th></tr></thead>"
          f"<tbody>{register_rows}</tbody></table>"
        + "<h2>3. Prescribed actions</h2>"
        + _actions_table(rf.prescribed_actions(defects), t["cost"])
    )

    if bim_png:
        body += ("<h2>4. Lining model</h2>"
                 f"<img class='panel' src='{_b64(bim_png)}' alt='BIM model'>")

    if include_case_files and ordered:
        body += "<div class='page-break'></div><h2>5. Defect case files</h2>"
        body += "".join(_case_file_html(d) for d in ordered)

    body += (
        "<div class='footer'>Generated from the tunnel digital twin. Each "
        "prescribed action is derived by traversal of the seven-level FMEA "
        "chain and resolves to the defect code, the indicator that populated "
        "it, and the standard clause that states the threshold.</div>"
    )
    return _shell(f"{label} — inspection & intervention report", body)


# =============================================================================
# HTML -> PDF via headless Chrome / Edge
# =============================================================================
_BROWSER_CANDIDATES = [
    "chrome", "google-chrome", "chromium", "chromium-browser", "msedge",
]
_BROWSER_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
]


def find_browser() -> Optional[str]:
    """Locate a Chromium-family browser able to print to PDF."""
    for name in _BROWSER_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    for path in _BROWSER_PATHS:
        if Path(path).exists():
            return path
    return None


def html_to_pdf(html_source: str, jobname: str,
                timeout_s: int = 90,
                landscape: bool = False) -> Tuple[Optional[bytes], str]:
    """
    Print HTML to PDF with headless Chrome/Edge.

    Returns (pdf_bytes | None, message). Never raises: if no browser is present
    the caller still has the HTML, which prints to PDF from any browser with
    Ctrl+P.
    """
    browser = find_browser()
    if not browser:
        return None, (
            "No Chrome or Edge found to print the PDF. The HTML download "
            "below opens in any browser — use File ▸ Print ▸ Save as PDF, "
            "which produces the same page."
        )

    # Big reports (many embedded figures) legitimately need longer than a
    # one-page summary; scale the allowance with the document size.
    timeout_s = max(timeout_s, 45 + len(html_source) // 12000)

    try:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / f"{jobname}.html"
            out = Path(td) / f"{jobname}.pdf"
            src.write_text(html_source, encoding="utf-8")

            cmd = [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                "--disable-extensions",
                f"--user-data-dir={Path(td) / 'profile'}",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=10000",
                "--no-pdf-header-footer",
                *(["--landscape"] if landscape else []),
                f"--print-to-pdf={out}",
                src.as_uri(),
            ]
            # Older builds reject --headless=new and/or the header flag.
            legacy = [c for c in cmd
                      if c not in ("--headless=new", "--no-pdf-header-footer")]
            legacy.insert(1, "--headless")
            legacy.insert(2, "--print-to-pdf-no-header")

            # Launching a headless browser is occasionally flaky (a running
            # Chrome mid-update, AV inspection, a cold profile). Retry rather
            # than sending the operator to the manual print path on a blip.
            attempts = (("modern", cmd), ("legacy", legacy), ("retry", cmd))
            proc = None
            for label, argv in attempts:
                proc = subprocess.run(argv, capture_output=True,
                                      timeout=timeout_s)
                if out.exists() and out.stat().st_size > 0:
                    data = out.read_bytes()
                    if data.startswith(b"%PDF"):
                        return data, f"Printed with {Path(browser).stem}."
                    return None, ("The browser wrote a file that is not a "
                                  "PDF. Use the HTML download instead.")
                if label != "retry":
                    time.sleep(1.5)  # let a half-started browser settle

            rc = proc.returncode if proc is not None else "?"
            detail = (proc.stderr or b"").decode("utf-8", "replace").strip()[-400:] \
                if proc is not None else ""
            return None, (
                "The browser did not produce a PDF after three attempts — "
                "use the HTML download and print it from your browser "
                "(Ctrl+P ▸ Save as PDF), which yields the same page.\n\n"
                f"Diagnostics — browser: {browser} · exit code: {rc} · "
                f"timeout: {timeout_s}s"
                + (f"\n{detail}" if detail else "")
            )
    except subprocess.TimeoutExpired:
        return None, (
            "Timed out waiting for the browser to print. Use the HTML "
            "download and print it from your browser."
        )
    except OSError as exc:
        return None, (
            f"Could not run the browser ({exc}). Use the HTML download and "
            "print it from your browser."
        )


# =============================================================================
# Generators — mirror the LaTeX ones' return shape
# =============================================================================
def generate_onepager_html(
    tunnel: Dict[str, Any],
    bim_tunnel: Optional[Dict[str, Any]],
    defects: Sequence[Dict[str, Any]],
    issued_on: Optional[date] = None,
    full_report_name: Optional[str] = None,
    max_actions: int = 8,
) -> Dict[str, Any]:
    panel = rf.render_onepager_panel(tunnel, bim_tunnel, defects)
    jobname = f"{tunnel.get('tunnel_id', 'tunnel')}_onepager".replace("-", "_")
    html_source = build_onepager_html(
        tunnel, defects, panel, issued_on=issued_on,
        full_report_name=full_report_name, max_actions=max_actions)
    pdf, message = html_to_pdf(html_source, jobname)
    return {"html": html_source, "panel": panel, "pdf": pdf,
            "message": message, "jobname": jobname}


def generate_full_html(
    tunnel: Dict[str, Any],
    bim_tunnel: Optional[Dict[str, Any]],
    defects: Sequence[Dict[str, Any]],
    issued_on: Optional[date] = None,
    onepager_name: Optional[str] = None,
    include_case_files: bool = True,
) -> Dict[str, Any]:
    from utils.report import render_bim_png

    panel = rf.render_onepager_panel(tunnel, bim_tunnel, defects)
    bim = render_bim_png(tunnel, bim_tunnel, list(defects))
    jobname = f"{tunnel.get('tunnel_id', 'tunnel')}_report".replace("-", "_")
    html_source = build_full_html(
        tunnel, defects, panel, bim_png=bim, issued_on=issued_on,
        onepager_name=onepager_name, include_case_files=include_case_files)
    pdf, message = html_to_pdf(html_source, jobname)
    return {"html": html_source, "panel": panel, "bim": bim, "pdf": pdf,
            "message": message, "jobname": jobname}


# =============================================================================
# Condition inspection report — chain-structured defect sheets
# =============================================================================
def _defect_sheet_html(defect: Dict[str, Any], graph: Any = None) -> str:
    """
    One defect sheet, structured by the seven FMEA chain levels.

    Mirrors `inspection_report.defect_sheet_tex` field for field, including the
    L6 edition binding — a clause with no dated edition is flagged in place
    rather than printed as a bare citation.
    """
    from utils import governance as gov

    priority = (defect.get("priority") or "LOW").upper()
    cls = PRIORITY_CSS.get(priority, "pri-low")
    parts = [
        f"<div class='case {cls}'>"
        f"<h3><span class='badge {cls}'>{_e(priority)}</span> "
        f"Defect {_e(defect.get('defect_id', '—'))}</h3>",
        f"<div class='kv'><b>Asset:</b> Ring {_e(defect.get('ring_id', '—'))} · "
        f"{_e(_chainage(defect.get('chainage_m')))} · "
        f"{_e(defect.get('position', '—'))}</div>",
    ]

    if defect.get("failure_mechanism"):
        parts.append("<div class='kv'><b>Deterioration mechanism:</b> "
                     f"{_e(defect['failure_mechanism'])}</div>")

    parts.append(
        "<div class='kv'><b>Condition:</b> "
        f"{_e(defect.get('defect_type', '—'))} "
        f"(severity {_e(defect.get('severity', '—'))})"
        + (f" — {_e(defect['description'])}" if defect.get("description") else "")
        + "</div>"
    )

    evidence = defect.get("modality_evidence") or {}
    if evidence:
        rows = "".join(
            f"<tr><td>{_e(mod)}</td><td>{_e((e or {}).get('fmea_level', '—'))}</td>"
            f"<td>{_e((e or {}).get('finding') or '—')}</td>"
            f"<td>{_e((e or {}).get('status', '—'))}</td></tr>"
            for mod, e in evidence.items()
        )
        parts.append(
            "<h3>Measurements</h3><table><thead><tr><th>Modality</th>"
            "<th>Chain level</th><th>Finding</th><th>Status</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    elif defect.get("indicators_summary"):
        parts.append("<div class='kv'><b>Measurements:</b> "
                     f"{_e(defect['indicators_summary'])}</div>")

    if defect.get("potential_cause"):
        parts.append("<div class='kv'><b>Diagnosis:</b> "
                     f"{_e(defect['potential_cause'])}</div>")

    clause_ref = defect.get("threshold_reference")
    binding = gov.clause_for_reference(graph, clause_ref) if (graph and clause_ref) else None
    if binding:
        assessment = (
            f"{_e(defect.get('threshold_triggered', '—'))} "
            f"<span class='note'>[{_e(clause_ref)}, edition "
            f"<code>{_e(gov.local_name(binding[1]))}</code>]</span>"
        )
    elif clause_ref:
        assessment = (
            f"{_e(defect.get('threshold_triggered', '—'))} "
            f"<span class='note' style='color:var(--high)'>[{_e(clause_ref)} — "
            "edition not bound; this assessment cannot be reconstructed after "
            "a revision]</span>"
        )
    else:
        assessment = "<span class='note'>No threshold reference recorded.</span>"
    parts.append(f"<div class='kv'><b>Assessment against standard:</b> {assessment}</div>")

    steps = defect.get("prescribed_interventions") or []
    if steps:
        items = "".join(
            f"<li>{_e(s.get('step', ''))}"
            + (f" <span class='note'>({_e(s.get('reference'))})</span>"
               if s.get("reference") else "")
            + "</li>"
            for s in steps
        )
        parts.append(f"<h3>Recommended action</h3><ol>{items}</ol>")
    else:
        parts.append(
            "<div class='kv'><b>Recommended action:</b> "
            f"Priority {_e(priority)}"
            + (f", within {_e(defect.get('deadline_days'))} days"
               if defect.get("deadline_days") else "")
            + "</div>"
        )

    parts.append(
        "<h3>Endorsement</h3><table><thead><tr>"
        "<th>Reviewing engineer</th><th>Date</th><th>Override recorded</th>"
        "</tr></thead><tbody><tr><td>&nbsp;<br>&nbsp;</td><td></td><td></td>"
        "</tr></tbody></table></div>"
    )
    return "".join(parts)


def build_inspection_html(
    tunnel: Dict[str, Any],
    defects: Sequence[Dict[str, Any]],
    graph: Any = None,
    issued_on: Optional[date] = None,
    inspector: str = "",
    change_rows: Optional[Sequence[Any]] = None,
    change_ambiguities: Optional[Sequence[Any]] = None,
    tolerance_m: Optional[float] = None,
) -> str:
    """The condition-inspection report as a self-contained web page."""
    from utils import governance as gov
    from utils import change_report as cr

    issued = (issued_on or date.today()).strftime("%d %B %Y")
    label = tunnel.get("label", tunnel.get("tunnel_id", "Tunnel"))
    ordered = sorted(
        defects,
        key=lambda d: ({"HIGH": 0, "MEDIUM": 1}.get(d.get("priority"), 2),
                       str(d.get("defect_id", ""))),
    )

    state = gov.kb_state(graph) if graph else {}
    unbound = gov.unbound_clause_references(graph, list(defects)) if graph else []

    subtitle = f"Condition inspection report · {issued}"
    if inspector:
        subtitle += f" · {inspector}"

    basis = (
        "<h2>Basis of assessment</h2>"
        "<p>Each assessment below is produced by traversal of the seven-level "
        "FMEA reasoning chain over the evidence recorded for that defect. "
        "Every recommended action resolves to the defect code, the indicator "
        "that populated it, the threshold that fired, and the clause and "
        "edition that states that threshold.</p>"
    )
    if state:
        basis += (
            "<table><tbody>"
            "<tr><td>Knowledge base</td><td><code>"
            f"{_e(state.get('ontology_version_iri') or 'not versioned')}</code></td></tr>"
            "<tr><td>Rule set</td><td><code>"
            f"{_e((state.get('ruleset_hash') or '')[:23])}…</code></td></tr>"
            f"<tr><td>Reasoner</td><td>{_e(state['reasoner']['name'])} "
            f"({_e(state['reasoner']['profile'])})</td></tr>"
            f"<tr><td>Defects assessed</td><td>{len(ordered)}</td></tr>"
            "</tbody></table>"
        )
    if unbound:
        basis += (
            "<div class='callout' style='border-left-color:var(--high)'>"
            f"<b>Note.</b> {len(unbound)} assessment(s) cite a clause that is "
            "not bound to a dated standard edition. Those assessments are "
            "marked in the sheets below and cannot be reconstructed after a "
            "revision of the source standard.</div>"
        )

    register_rows = "".join(
        f"<tr class='{PRIORITY_CSS.get((d.get('priority') or 'LOW').upper(), 'pri-low')}'>"
        f"<td>{_e(d.get('defect_id'))}</td><td>{_e(d.get('defect_type'))}</td>"
        f"<td>{_e(d.get('ring_id'))}</td>"
        f"<td>{_e(_chainage(d.get('chainage_m')))}</td>"
        f"<td>{_e(d.get('severity', '—'))}</td>"
        f"<td>{_e(d.get('priority', '—'))}</td></tr>"
        for d in ordered
    ) or "<tr><td colspan='6'>No defects registered against this tunnel.</td></tr>"

    body = (
        _masthead(label, subtitle)
        + basis
        + "<h2>Defect register</h2>"
          "<table><thead><tr><th>Defect</th><th>Type</th><th>Ring</th>"
          "<th>Chainage</th><th>Severity</th><th>Priority</th></tr></thead>"
          f"<tbody>{register_rows}</tbody></table>"
    )

    if ordered:
        body += "<div class='page-break'></div><h2>Defect sheets</h2>"
        body += "".join(_defect_sheet_html(d, graph) for d in ordered)

    if change_rows is not None and tolerance_m is not None:
        counts = cr.summarise(change_rows)
        rows = "".join(
            f"<tr><td>{_e(k)}</td><td class='num'>{v}</td>"
            f"<td class='note'>{_e(cr.STATE_MEANING[k])}</td></tr>"
            for k, v in counts.items()
        )
        body += (
            "<div class='page-break'></div><h2>Inter-cycle change report</h2>"
            "<p>Each defect in the current cycle is classified by comparing its "
            "activated chain against the chain activated at its predecessor. "
            f"Association tolerance in force: {tolerance_m:g} m "
            "(operator-configured).</p>"
            "<table><thead><tr><th>State</th><th class='num'>Count</th>"
            "<th>Operator significance</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
        rate = cr.reintervention_rate(change_rows)
        body += (
            "<p class='note'>Re-intervention rate is not computable: no "
            "repaired predecessor is present in the comparison set.</p>"
            if rate is None else
            f"<p><b>Re-intervention rate:</b> {rate * 100:.1f}% of previously "
            "repaired defects recurred.</p>"
        )
        if change_ambiguities:
            amb = "".join(
                f"<tr><td>{_e(a.defect_id)}</td>"
                f"<td>{_e(', '.join(a.candidates))}</td></tr>"
                for a in change_ambiguities
            )
            body += (
                "<h3>Ambiguous associations — adjudication required</h3>"
                "<p class='note'>More than one predecessor lay within "
                "tolerance. These are <b>not</b> merged; each is deferred to "
                "Investigation_Required pending engineer adjudication.</p>"
                "<table><thead><tr><th>Defect</th>"
                "<th>Candidate predecessors</th></tr></thead>"
                f"<tbody>{amb}</tbody></table>"
            )

    return _shell(f"{label} — condition inspection report", body)


def generate_inspection_html(
    tunnel: Dict[str, Any],
    defects: Sequence[Dict[str, Any]],
    graph: Any = None,
    issued_on: Optional[date] = None,
    inspector: str = "",
    change_rows: Optional[Sequence[Any]] = None,
    change_ambiguities: Optional[Sequence[Any]] = None,
    tolerance_m: Optional[float] = None,
) -> Dict[str, Any]:
    """Build the inspection report and print it to PDF."""
    jobname = f"{tunnel.get('tunnel_id', 'tunnel')}_inspection".replace("-", "_")
    html_source = build_inspection_html(
        tunnel, defects, graph=graph, issued_on=issued_on, inspector=inspector,
        change_rows=change_rows, change_ambiguities=change_ambiguities,
        tolerance_m=tolerance_m)
    pdf, message = html_to_pdf(html_source, jobname)
    return {"html": html_source, "pdf": pdf, "message": message,
            "jobname": jobname}


# =============================================================================
# Slide deck — landscape HTML, one section per page
# =============================================================================
_DECK_CSS = """
@page{ size:A4 landscape; margin:0; }
html,body{margin:0;padding:0;background:#fff}
body{
  font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink);
}
.slide{
  width:297mm; height:209mm; padding:14mm 16mm;
  page-break-after:always; break-after:page;
  display:flex; flex-direction:column; position:relative;
  border-bottom:1px solid #eee;
}
.slide:last-child{page-break-after:auto; break-after:auto}
.slide h2{
  color:var(--line); font-size:20pt; margin:0 0 8px;
  border-bottom:2px solid var(--line); padding-bottom:5px;
}
.slide .fill{flex:1; display:flex; align-items:center; justify-content:center;
             min-height:0}
.slide .fill img{max-width:100%; max-height:100%; object-fit:contain}
.slide .num{
  position:absolute; right:16mm; bottom:8mm;
  font-size:9pt; color:var(--muted);
}
.title-slide{justify-content:center; background:var(--line); color:#fff}
.title-slide h1{font-size:34pt; margin:0 0 6px}
.title-slide .sub{font-size:15pt; opacity:.93}
.title-slide .meta{font-size:11pt; opacity:.85; margin-top:18px}
.slide table{font-size:11pt}
.slide .kpis{margin:10px 0 6px}
.slide .kpi .v{font-size:30pt}
.slide .kpi .c{font-size:10pt}
@media print{
  body{-webkit-print-color-adjust:exact; print-color-adjust:exact}
  .slide{border-bottom:none}
}
"""


def build_deck_html(
    tunnel: Dict[str, Any],
    defects: Sequence[Dict[str, Any]],
    panel_png: bytes,
    bim_png: Optional[bytes] = None,
    issued_on: Optional[date] = None,
) -> str:
    """
    A landscape slide deck as one self-contained page.

    Each `.slide` is exactly one A4 landscape page, so printing from any
    browser yields a deck with no LaTeX and no Beamer.
    """
    issued = (issued_on or date.today()).strftime("%d %B %Y")
    label = tunnel.get("label", tunnel.get("tunnel_id", "Tunnel"))
    t = rf.totals(defects)
    actions = rf.prescribed_actions(defects, limit=8)

    slides: List[str] = []

    slides.append(
        "<section class='slide title-slide'>"
        f"<h1>{_e(label)}</h1>"
        "<div class='sub'>Maintenance status and prescribed actions</div>"
        f"<div class='meta'>Tunnel digital twin · {_e(issued)}</div>"
        "</section>"
    )

    slides.append(
        "<section class='slide'><h2>Where we stand</h2>"
        + _kpis(t)
        + f"<p>{t['high']} of {t['active']} open defects need action within "
          "30 days. Cost exposure blends engineer-recorded estimates with the "
          "transparent unit-rate model.</p>"
        "<div class='num'>2</div></section>"
    )

    slides.append(
        "<section class='slide'><h2>The asset and its defects</h2>"
        f"<div class='fill'><img src='{_b64(panel_png)}' alt='Summary panel'></div>"
        "<div class='num'>3</div></section>"
    )

    if bim_png:
        slides.append(
            "<section class='slide'><h2>Lining model</h2>"
            f"<div class='fill'><img src='{_b64(bim_png)}' alt='Lining model'></div>"
            "<div class='num'>4</div></section>"
        )

    slides.append(
        "<section class='slide'><h2>What we recommend</h2>"
        + _actions_table(actions, t["cost"])
        + f"<div class='num'>{len(slides) + 1}</div></section>"
    )

    slides.append(
        "<section class='slide'><h2>How these figures are produced</h2>"
        "<p>Multimodal survey (RGB, depth, thermal, GPR) → defect extraction → "
        "COBie asset records → ontology knowledge base → seven-level FMEA "
        "reasoning chain → prescribed intervention.</p>"
        "<p>Every recommendation resolves to the defect code, the indicator "
        "that populated it, the threshold that fired, and the standard clause "
        "and edition that states that threshold — so any figure on these "
        "slides can be traced back to its evidence.</p>"
        f"<div class='num'>{len(slides) + 1}</div></section>"
    )

    css = _CSS + _DECK_CSS
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{_e(label)} — slide deck</title><style>{css}</style></head>"
        f"<body>{''.join(slides)}</body></html>"
    )


def generate_deck_html(
    tunnel: Dict[str, Any],
    bim_tunnel: Optional[Dict[str, Any]],
    defects: Sequence[Dict[str, Any]],
    issued_on: Optional[date] = None,
) -> Dict[str, Any]:
    """Build the deck and print it to a landscape PDF."""
    from utils.report import render_bim_png

    panel = rf.render_onepager_panel(tunnel, bim_tunnel, defects)
    bim = render_bim_png(tunnel, bim_tunnel, list(defects))
    jobname = f"{tunnel.get('tunnel_id', 'tunnel')}_deck".replace("-", "_")
    html_source = build_deck_html(tunnel, defects, panel, bim_png=bim,
                                  issued_on=issued_on)
    pdf, message = html_to_pdf(html_source, jobname, landscape=True)
    return {"html": html_source, "panel": panel, "pdf": pdf,
            "message": message, "jobname": jobname}
