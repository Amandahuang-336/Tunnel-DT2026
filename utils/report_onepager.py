"""
Version A — the one-pager
=========================

A single coloured A4 page an asset manager can read without opening anything
else: KPI tiles, the alignment map and BIM model, the chainage strip, the
priority mix, the cost exposure, and the prescribed actions with their
estimates.

Relationship to version B
-------------------------
The one-pager and the comprehensive report are generated from the SAME figure
panel and the SAME totals (`report_figures.totals`), so the two documents
cannot disagree with each other. Each carries a pointer to the other by
filename, and the comprehensive report reproduces this panel as its summary
section — so a reader handed either document knows the other exists and what
is in it.

Everything on this page is a view of data already in the register. No figure
here introduces a value that is not in the defect records or the cost model.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Sequence

import io
import zipfile

from utils.report import _esc, compile_latex_to_pdf
from utils import report_figures as rf

# Priority -> LaTeX colour, matching the palette used in the figures.
PRIORITY_TEX = {
    "HIGH": "priHigh",
    "MEDIUM": "priMed",
    "LOW": "priLow",
}

COLOUR_DEFS = r"""
\definecolor{priHigh}{HTML}{D62728}
\definecolor{priMed}{HTML}{FF7F0E}
\definecolor{priLow}{HTML}{999999}
\definecolor{brandInk}{HTML}{22223B}
\definecolor{brandLine}{HTML}{4A4E8F}
\definecolor{brandSoft}{HTML}{EDEDF5}
\definecolor{brandMuted}{HTML}{7A7A8C}
"""


def _money(value: Any) -> str:
    try:
        return f"\\${float(value):,.0f}"
    except (TypeError, ValueError):
        return "---"


def _chainage(value: Any) -> str:
    try:
        return f"K{float(value):.0f}"
    except (TypeError, ValueError):
        return "---"


def _kpi_tile(value: str, caption: str, colour: str) -> str:
    """One coloured KPI tile."""
    return (
        f"\\begin{{minipage}}[t]{{0.235\\textwidth}}\n"
        f"\\colorbox{{{colour}!12}}{{%\n"
        f"\\begin{{minipage}}[t][1.55cm][c]{{\\dimexpr\\linewidth-2\\fboxsep}}\n"
        f"\\centering\n"
        f"{{\\fontsize{{20}}{{22}}\\selectfont\\bfseries\\color{{{colour}}}{value}}}\\\\[2pt]\n"
        f"{{\\footnotesize\\color{{brandInk}}{caption}}}\n"
        f"\\end{{minipage}}}}\n"
        f"\\end{{minipage}}"
    )


def build_onepager_tex(
    tunnel: Dict[str, Any],
    defects: Sequence[Dict[str, Any]],
    panel_png_name: str,
    issued_on: Optional[date] = None,
    full_report_name: Optional[str] = None,
    max_actions: int = 8,
) -> str:
    """
    Assemble the one-page summary.

    `full_report_name` is the filename of the comprehensive report, printed in
    the footer so the reader knows where the detail lives.
    """
    issued = (issued_on or date.today()).strftime("%d %B %Y")
    label = _esc(tunnel.get("label", tunnel.get("tunnel_id", "Tunnel")))
    t = rf.totals(defects)

    actions = rf.prescribed_actions(defects, limit=max_actions)
    hidden = max(0, len([d for d in defects]) - len(actions))

    if actions:
        rows = "".join(
            "\\rowcolor{%s!8}\n" % PRIORITY_TEX[a["priority"]]
            + f"\\textcolor{{{PRIORITY_TEX[a['priority']]}}}{{\\textbf{{$\\bullet$}}}} "
              f"{_esc(a['defect_id'])} & "
              f"{_esc(a['defect_type'])} & "
              f"{_chainage(a['chainage_m'])} & "
              f"{_esc(a['action'])[:78]} & "
              + (f"{int(a['deadline_days'])}\\,d" if a.get("deadline_days") else "---")
              + f" & {_money(a['cost'])} \\\\\n"
            for a in actions
        )
        actions_block = (
            "\\begin{tabularx}{\\textwidth}{@{}l l l X c r@{}}\n"
            "\\arrayrulecolor{brandLine}\\toprule\n"
            "\\rowcolor{brandSoft}\n"
            "\\textbf{Defect} & \\textbf{Type} & \\textbf{Ch.} & "
            "\\textbf{Prescribed action} & \\textbf{Due} & \\textbf{Est.\\ cost} \\\\\n"
            "\\midrule\n" + rows +
            "\\midrule\n"
            "\\multicolumn{5}{@{}r}{\\textbf{Total exposure, all open defects}} & "
            f"\\textbf{{{_money(t['cost'])}}} \\\\\n"
            "\\bottomrule\\arrayrulecolor{black}\n"
            "\\end{tabularx}"
        )
        if hidden:
            actions_block += (
                f"\n\n{{\\footnotesize\\color{{brandMuted}}"
                f"Showing the {len(actions)} most urgent of {len(defects)} "
                f"registered defects; the remaining {hidden} appear in the "
                f"comprehensive report.}}"
            )
    else:
        actions_block = (
            "{\\color{brandMuted}\\emph{No defects registered against this "
            "tunnel yet.}}"
        )

    footer = (
        "{\\footnotesize\\color{brandMuted}"
        "Generated from the tunnel digital twin. Every action shown is derived "
        "by traversal of the seven-level FMEA chain and resolves to the "
        "standard clause that prescribes it."
    )
    if full_report_name:
        footer += (
            f" Full evidence, per-defect case files and cost build-ups: "
            f"\\texttt{{{_esc(full_report_name)}}}."
        )
    footer += "}"

    # Tiles are built here rather than inline in the template below: nesting an
    # f-string inside a replacement field makes the backslash escaping very easy
    # to get wrong, and "\\%" instead of "\%" silently emits a LaTeX line break
    # followed by a comment, which eats the rest of the line.
    tiles = "\\hfill\n".join([
        _kpi_tile(str(t["active"]), "Open defects", "brandLine"),
        _kpi_tile(str(t["high"]), "Need action $\\le$ 30 days", "priHigh"),
        _kpi_tile(f"{t['confidence_pct']}\\%", "Diagnostic confidence", "brandLine"),
        _kpi_tile(_money(t["cost"]), "12-month cost exposure", "priMed"),
    ])

    return f"""\\documentclass[10pt,a4paper]{{article}}
\\usepackage[margin=1.2cm,bottom=1.1cm,top=1.1cm]{{geometry}}
\\usepackage{{graphicx,xcolor,booktabs,tabularx,colortbl,array}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{parskip}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\setlength{{\\tabcolsep}}{{4pt}}
\\renewcommand{{\\arraystretch}}{{1.18}}
\\pagestyle{{empty}}
{COLOUR_DEFS}
\\begin{{document}}

%% ---- coloured masthead -------------------------------------------------
\\noindent\\colorbox{{brandLine}}{{%
\\begin{{minipage}}[c][1.25cm][c]{{\\dimexpr\\textwidth-2\\fboxsep}}
\\hspace{{4pt}}{{\\color{{white}}\\LARGE\\bfseries {label}}}\\hfill
{{\\color{{white}}\\small Maintenance summary \\;\\textbullet\\; {_esc(issued)}}}\\hspace{{4pt}}
\\end{{minipage}}}}

\\vspace{{6pt}}

%% ---- KPI tiles ---------------------------------------------------------
\\noindent
{tiles}

\\vspace{{8pt}}

%% ---- the dashboard panel ----------------------------------------------
\\noindent\\includegraphics[width=\\textwidth]{{{panel_png_name}}}

\\vspace{{4pt}}

%% ---- prescribed actions -----------------------------------------------
\\noindent{{\\color{{brandInk}}\\large\\bfseries Prescribed actions}}
\\vspace{{3pt}}

\\noindent {actions_block}

\\vfill
\\noindent\\textcolor{{brandLine}}{{\\rule{{\\textwidth}}{{0.6pt}}}}\\\\[2pt]
\\noindent {footer}

\\end{{document}}
"""


def generate_onepager(
    tunnel: Dict[str, Any],
    bim_tunnel: Optional[Dict[str, Any]],
    defects: Sequence[Dict[str, Any]],
    issued_on: Optional[date] = None,
    full_report_name: Optional[str] = None,
    max_actions: int = 8,
) -> Dict[str, Any]:
    """
    Version A — render the panel, build the page, compile, bundle a fallback.

    Mirrors `report.generate_report`'s return shape so the page can treat the
    two documents interchangeably.
    """
    panel = rf.render_onepager_panel(tunnel, bim_tunnel, defects)
    panel_name = "summary_panel.png"

    tex = build_onepager_tex(
        tunnel=tunnel,
        defects=defects,
        panel_png_name=panel_name,
        issued_on=issued_on,
        full_report_name=full_report_name,
        max_actions=max_actions,
    )

    jobname = f"{tunnel.get('tunnel_id', 'tunnel')}_onepager".replace("-", "_")
    pdf, message = compile_latex_to_pdf(tex, [(panel_name, panel)], jobname)

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{jobname}.tex", tex)
        z.writestr(panel_name, panel)

    return {
        "tex": tex,
        "panel": panel,
        "pdf": pdf,
        "message": message,
        "zip": zbuf.getvalue(),
        "jobname": jobname,
    }
