"""
Inspection report and inter-cycle change report
===============================================

Implements the manuscript's reporting layer: FMEA-chain traversal rendered
directly to the authority-format inspection report, and the inter-cycle change
report computed over the identity linkage.

WHY THIS EXISTS SEPARATELY FROM report.py
-----------------------------------------
`utils/report.py` produces a *session/research* report — KPIs, cost model, BIM
figure, knowledge-model verification. That is a different artefact from the
condition-inspection report an operator or inspection contractor is
contractually obliged to produce. This module builds the latter: one defect
sheet per defect, structured by the seven chain levels, so the framework's
output is the operator's deliverable rather than an intermediate data product.

THE MAPPING (manuscript, chain level -> report field)
----------------------------------------------------
    L1 Component   -> Asset header
    L2 Mechanism   -> Deterioration mechanism
    L3 Defect      -> Condition (severity code + expansion)
    L4 Indicator   -> Measurements table, one row per indicator,
                      each carrying its acquiring modality
    L5 Cause       -> Diagnosis (with confidence qualifier)
    L6 Threshold   -> Assessment against standard: criterion, tier, AND the
                      clause and *edition* it derives from
    L7 Intervention-> Recommended action
    ---            -> Endorsement block

The L6 row is the one that needs the governance layer: a clause without an
edition cannot be reconstructed after a revision, and the sheet says so
explicitly where the binding is missing rather than printing a bare citation.

NON-FUNCTIONAL REQUIREMENTS (manuscript)
----------------------------------------
Rendering is deterministic — the same graph state and template produce the same
document, so any difference between two issues is attributable to a change in
the evidence rather than to the renderer. Nothing here calls a clock except the
explicit `issued_on` argument, which the caller supplies.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from utils.report import _esc
from utils import governance as gov
from utils import change_report as cr

# The mapping table, exposed so the UI and the report share one definition.
CHAIN_TO_FIELD: List[Tuple[str, str, str]] = [
    ("L1", "Component", "Asset header — component ID, network location, chainage, element type"),
    ("L2", "Mechanism", "Deterioration mechanism"),
    ("L3", "Defect", "Condition — severity code with plain-language expansion"),
    ("L4", "Indicator", "Measurements table — value, unit, acquiring modality"),
    ("L5", "Cause", "Diagnosis — cause with confidence qualifier"),
    ("L6", "Threshold", "Assessment against standard — criterion, tier, clause AND edition"),
    ("L7", "Intervention", "Recommended action — steps, materials, escalation triggers"),
    ("—", "Endorsement", "Reviewing engineer, date, and any recorded override"),
]


def _fmt_chainage(value: Any) -> str:
    try:
        return f"K{float(value):.0f}m"
    except (TypeError, ValueError):
        return "—"


# =============================================================================
# One defect sheet, structured by the seven chain levels
# =============================================================================
def defect_sheet_tex(defect: Dict[str, Any], graph: Any = None) -> str:
    """Render one defect as a chain-structured defect sheet."""
    did = _esc(defect.get("defect_id", "—"))
    parts: List[str] = [f"\\subsection*{{Defect {did}}}"]

    # ---- L1 Component -> asset header --------------------------------------
    parts.append(
        "\\noindent\\textbf{Asset}\\quad "
        f"Ring {_esc(defect.get('ring_id', '—'))} "
        f"\\textperiodcentered{{}} {_fmt_chainage(defect.get('chainage_m'))} "
        f"\\textperiodcentered{{}} {_esc(defect.get('position', '—'))}"
        "\\par\\smallskip"
    )

    # ---- L2 Mechanism ------------------------------------------------------
    if defect.get("failure_mechanism"):
        parts.append(
            "\\noindent\\textbf{Deterioration mechanism}\\quad "
            f"{_esc(defect['failure_mechanism'])}\\par\\smallskip"
        )

    # ---- L3 Defect / condition --------------------------------------------
    parts.append(
        "\\noindent\\textbf{Condition}\\quad "
        f"{_esc(defect.get('defect_type', '—'))} "
        f"(severity {_esc(defect.get('severity', '—'))})"
        + (f" --- {_esc(defect['description'])}" if defect.get("description") else "")
        + "\\par\\smallskip"
    )

    # ---- L4 Indicators -> measurements table with modality provenance -------
    evidence = defect.get("modality_evidence") or {}
    if evidence:
        rows = "".join(
            f"{_esc(mod)} & {_esc((e or {}).get('fmea_level', '—'))} & "
            f"{_esc((e or {}).get('finding') or '—')} & "
            f"{_esc((e or {}).get('status', '—'))} \\\\\n"
            for mod, e in evidence.items()
        )
        parts.append(
            "\\noindent\\textbf{Measurements}\\par\\smallskip\n"
            "\\begin{tabular}{@{}llp{0.42\\textwidth}l@{}}\\toprule\n"
            "Modality & Chain level & Finding & Status \\\\ \\midrule\n"
            + rows + "\\bottomrule\\end{tabular}\\par\\smallskip"
        )
    elif defect.get("indicators_summary"):
        parts.append(
            "\\noindent\\textbf{Measurements}\\quad "
            f"{_esc(defect['indicators_summary'])}\\par\\smallskip"
        )

    # ---- L5 Cause ----------------------------------------------------------
    if defect.get("potential_cause"):
        parts.append(
            "\\noindent\\textbf{Diagnosis}\\quad "
            f"{_esc(defect['potential_cause'])}\\par\\smallskip"
        )

    # ---- L6 Threshold -> assessment against standard, WITH edition ----------
    clause_ref = defect.get("threshold_reference")
    binding = gov.clause_for_reference(graph, clause_ref) if (graph and clause_ref) else None
    if binding:
        edition_label = gov.local_name(binding[1])
        assessment = (
            f"{_esc(defect.get('threshold_triggered', '—'))} "
            f"\\quad[{_esc(clause_ref)}, edition \\texttt{{{_esc(edition_label)}}}]"
        )
    elif clause_ref:
        assessment = (
            f"{_esc(defect.get('threshold_triggered', '—'))} "
            f"\\quad[{_esc(clause_ref)} --- \\emph{{edition not bound; this "
            "assessment cannot be reconstructed after a revision}}]"
        )
    else:
        assessment = "\\emph{No threshold reference recorded.}"
    parts.append(
        "\\noindent\\textbf{Assessment against standard}\\quad "
        f"{assessment}\\par\\smallskip"
    )

    # ---- L7 Intervention ---------------------------------------------------
    interventions = defect.get("prescribed_interventions") or []
    if interventions:
        items = "".join(
            f"\\item {_esc(iv.get('step', ''))}"
            + (f" \\emph{{({_esc(iv.get('reference'))})}}" if iv.get("reference") else "")
            + "\n"
            for iv in interventions
        )
        parts.append(
            "\\noindent\\textbf{Recommended action}"
            "\\begin{enumerate}\\itemsep2pt\n" + items + "\\end{enumerate}"
        )
    else:
        parts.append(
            "\\noindent\\textbf{Recommended action}\\quad "
            f"Priority {_esc(defect.get('priority', '—'))}"
            + (f", within {_esc(defect.get('deadline_days'))} days"
               if defect.get("deadline_days") else "")
            + "\\par\\smallskip"
        )

    # ---- Endorsement block -------------------------------------------------
    parts.append(
        "\\noindent\\textbf{Endorsement}\\par\\smallskip\n"
        "\\begin{tabular}{@{}p{0.30\\textwidth}p{0.22\\textwidth}p{0.34\\textwidth}@{}}"
        "\\toprule\n"
        "Reviewing engineer & Date & Override recorded \\\\ \\midrule\n"
        "\\rule{0pt}{3.2ex} & & \\\\ \\bottomrule\\end{tabular}\\par\\medskip"
    )
    return "\n".join(parts)


# =============================================================================
# Inter-cycle change report section
# =============================================================================
def change_report_tex(rows: Sequence[cr.ChangeRow],
                      ambiguities: Sequence[cr.Ambiguity],
                      tolerance_m: float) -> str:
    """Render the five-state inter-cycle classification."""
    counts = cr.summarise(rows)
    summary_rows = "".join(
        f"{_esc(state)} & {count} & {_esc(cr.STATE_MEANING[state])} \\\\\n"
        for state, count in counts.items()
    )
    parts = [
        "\\section*{Inter-cycle change report}",
        "\\noindent Each defect in the current cycle is classified by comparing "
        "its activated chain against the chain activated at its predecessor. "
        f"Association tolerance in force: {tolerance_m:g}~m "
        "(operator-configured).\\par\\medskip",
        "\\begin{tabular}{@{}lrp{0.55\\textwidth}@{}}\\toprule\n"
        "State & Count & Operator significance \\\\ \\midrule\n"
        + summary_rows + "\\bottomrule\\end{tabular}\\par\\medskip",
    ]

    rate = cr.reintervention_rate(rows)
    if rate is None:
        parts.append(
            "\\noindent\\emph{Re-intervention rate is not computable: no "
            "repaired predecessor is present in the comparison set.}"
            "\\par\\medskip"
        )
    else:
        parts.append(
            f"\\noindent\\textbf{{Re-intervention rate:}} {rate * 100:.1f}\\% "
            "of previously repaired defects recurred.\\par\\medskip"
        )

    detail = [r for r in rows if r.state != cr.STATE_STABLE]
    if detail:
        detail_rows = "".join(
            f"{_esc(r.defect_id)} & {_esc(r.defect_type)} & "
            f"{_fmt_chainage(r.chainage_m)} & {_esc(r.state)} & "
            f"{_esc(r.tier_previous or '—')} & {_esc(r.tier_current or '—')} \\\\\n"
            for r in detail
        )
        parts.append(
            "\\noindent\\textbf{Defects requiring attention}\\par\\smallskip\n"
            "\\begin{tabular}{@{}llllll@{}}\\toprule\n"
            "Defect & Type & Chainage & State & Tier (prev) & Tier (now) \\\\ \\midrule\n"
            + detail_rows + "\\bottomrule\\end{tabular}\\par\\medskip"
        )

    if ambiguities:
        amb_rows = "".join(
            f"{_esc(a.defect_id)} & {_esc(', '.join(a.candidates))} \\\\\n"
            for a in ambiguities
        )
        parts.append(
            "\\noindent\\textbf{Ambiguous associations --- adjudication required}"
            "\\par\\smallskip\n"
            "\\noindent More than one predecessor lay within tolerance. These "
            "are \\emph{not} merged; each is deferred to "
            "\\texttt{Investigation\\_Required} pending engineer "
            "adjudication.\\par\\smallskip\n"
            "\\begin{tabular}{@{}ll@{}}\\toprule\n"
            "Defect & Candidate predecessors \\\\ \\midrule\n"
            + amb_rows + "\\bottomrule\\end{tabular}\\par\\medskip"
        )
    return "\n".join(parts)


# =============================================================================
# Full inspection report document
# =============================================================================
_PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=2cm]{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{parskip}
\setlength{\emergencystretch}{3em}
\begin{document}
"""


def build_inspection_report_tex(
    tunnel: Dict[str, Any],
    defects: Sequence[Dict[str, Any]],
    graph: Any = None,
    issued_on: Optional[date] = None,
    inspector: str = "",
    change_rows: Optional[Sequence[cr.ChangeRow]] = None,
    change_ambiguities: Optional[Sequence[cr.Ambiguity]] = None,
    tolerance_m: Optional[float] = None,
) -> str:
    """
    Assemble the condition-inspection report.

    `issued_on` is supplied by the caller rather than read from the clock, so
    the render is deterministic and two issues of the same report differ only
    where the evidence differs.
    """
    issued = (issued_on or date.today()).isoformat()
    label = _esc(tunnel.get("label", tunnel.get("tunnel_id", "Tunnel")))

    ordered = sorted(
        defects,
        key=lambda d: ({"HIGH": 0, "MEDIUM": 1}.get(d.get("priority"), 2),
                       str(d.get("defect_id", ""))),
    )

    # Provenance of the knowledge base that produced these assessments.
    state = gov.kb_state(graph)
    unbound = gov.unbound_clause_references(graph, list(defects)) if graph else []

    body = [
        _PREAMBLE,
        f"\\begin{{center}}\\Large\\textbf{{Condition inspection report}}\\\\[2pt]",
        f"\\large {label}\\\\[2pt]",
        f"\\normalsize Issued {_esc(issued)}"
        + (f" \\textperiodcentered{{}} Inspector: {_esc(inspector)}" if inspector else "")
        + "\\end{center}\\vspace{4pt}",

        "\\section*{Basis of assessment}",
        "\\noindent Each assessment below is produced by traversal of the "
        "seven-level FMEA reasoning chain over the evidence recorded for that "
        "defect. Every recommended action resolves to the defect code, the "
        "indicator that populated it, the threshold that fired, and the clause "
        "and edition that states that threshold.\\par\\smallskip",
        "\\noindent\\begin{tabular}{@{}ll@{}}\\toprule\n"
        f"Knowledge base & \\texttt{{{_esc(state.get('ontology_version_iri') or 'not versioned')}}} \\\\\n"
        f"Rule set & \\texttt{{{_esc((state.get('ruleset_hash') or '')[:23])}...}} \\\\\n"
        f"Reasoner & {_esc(state['reasoner']['name'])} ({_esc(state['reasoner']['profile'])}) \\\\\n"
        f"Defects assessed & {len(ordered)} \\\\\n"
        "\\bottomrule\\end{tabular}\\par\\medskip",
    ]

    if unbound:
        body.append(
            "\\noindent\\textbf{Note.} "
            f"{len(unbound)} assessment(s) cite a clause that is not bound to a "
            "dated standard edition. Those assessments are marked in the sheets "
            "below and cannot be reconstructed after a revision of the source "
            "standard.\\par\\medskip"
        )

    if ordered:
        register_rows = "".join(
            f"{_esc(d.get('defect_id'))} & {_esc(d.get('defect_type'))} & "
            f"{_esc(d.get('ring_id'))} & {_fmt_chainage(d.get('chainage_m'))} & "
            f"{_esc(d.get('severity', '—'))} & {_esc(d.get('priority', '—'))} \\\\\n"
            for d in ordered
        )
        body.append(
            "\\section*{Defect register}"
            "\\begin{longtable}{@{}llllll@{}}\\toprule\n"
            "Defect & Type & Ring & Chainage & Severity & Priority \\\\ \\midrule\n"
            f"{register_rows}\\bottomrule\n\\end{{longtable}}"
        )
        body.append("\\section*{Defect sheets}")
        body.extend(defect_sheet_tex(d, graph) for d in ordered)
    else:
        body.append(
            "\\section*{Defect register}"
            "\\noindent\\emph{No defects registered against this tunnel.}"
        )

    if change_rows is not None and tolerance_m is not None:
        body.append(change_report_tex(change_rows, change_ambiguities or [], tolerance_m))

    body.append("\\end{document}")
    return "\n\n".join(body)


def chain_mapping_rows() -> List[Dict[str, str]]:
    """The chain-to-field mapping, for display in the UI."""
    return [{"Chain level": lvl, "Element": name, "Report field": field}
            for lvl, name, field in CHAIN_TO_FIELD]
