"""Deterministic graph-side threshold activation for the case ABox.

The evaluator reads manuscript-aligned ABox assertions and materialises the
L6 -> L7 links.  It deliberately distinguishes an activated criterion from a
criterion that cannot yet be evaluated (notably the 30% rebar-section-loss
test for D-1158-S).
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS


TUN = Namespace("http://w3id.org/tunnel-dt/ontology/v1.2#")
PROV = Namespace("http://www.w3.org/ns/prov#")


def _named(graph: Graph, uri: URIRef, cls: URIRef) -> None:
    graph.add((uri, RDF.type, cls))
    graph.add((uri, RDF.type, OWL.NamedIndividual))


def _case_text(graph: Graph, defect: URIRef) -> str:
    values = []
    for prop in (TUN.hasDescription, TUN.hasSeverity, TUN.hasType):
        values.extend(str(value) for value in graph.objects(defect, prop))
    for indicator in graph.objects(defect, TUN.hasIndicator):
        values.extend(str(value) for value in graph.objects(indicator, TUN.hasValue))
    for cause in graph.objects(defect, TUN.hasCause):
        values.extend(str(value) for value in graph.objects(cause, RDFS.comment))
        values.extend(str(value) for value in graph.objects(cause, RDFS.label))
    return " | ".join(values)


def _has_code(text: str, code: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])", text))


def _decision(defect_type: str, text: str) -> Tuple[str, Optional[str], str]:
    """Return status, reference-threshold ID, and manuscript urgency tier."""
    lowered = text.lower()

    if defect_type == "Spalls":
        if any(_has_code(text, code) for code in ("S-2", "S-3", "S-4")):
            return "Activated", "THRESH-COR-SPALL-S2", "Action_Required"
        return "Activated", None, "Monitor_Closely"

    if defect_type == "LeakingJoints":
        if _has_code(text, "GS") or _has_code(text, "F"):
            return "Activated", "THRESH-LEAK-GS", "Action_Required"
        return "Activated", None, "Monitor_Closely"

    if defect_type == "Cracks":
        if "active" in lowered and "inactive" not in lowered:
            return "Activated", "THRESH-CRACK-ACTIVE", "Investigation_Required"
        if "dormant" in lowered or "no movement" in lowered:
            return "Activated", "THRESH-CRACK-DORMANT", "Action_Required"
        return "Activated", None, "Monitor_Closely"

    if defect_type == "Staining":
        return "Activated", None, "Monitor_Closely"

    return "NotEvaluable", None, "Investigation_Required"


def evaluate_case_thresholds(graph: Graph) -> None:
    """Materialise each case defect's L6 threshold and L7 prescription link."""
    for defect, defect_type_literal in graph.subject_objects(TUN.hasType):
        defect_id = str(defect).rsplit("#", 1)[-1]
        if not defect_id.startswith("D-"):
            continue
        defect_type = str(defect_type_literal)
        text = _case_text(graph, defect)
        status, reference_id, tier = _decision(defect_type, text)

        threshold = TUN[f"Threshold-{defect_id}"]
        intervention = TUN[f"Intervention-{defect_id}"]
        _named(graph, threshold, TUN.Threshold)
        graph.remove((threshold, TUN.status, Literal("Candidate")))
        graph.add((threshold, TUN.status, Literal(status)))
        graph.add((threshold, TUN.tier, TUN[tier]))
        graph.add((defect, TUN.hasThreshold, threshold))

        if reference_id:
            graph.add((threshold, PROV.wasDerivedFrom, TUN[reference_id]))

        if status == "Activated" and (intervention, RDF.type, TUN.Intervention) in graph:
            graph.add((threshold, TUN.prescribesIntervention, intervention))

        # D-1158-S has an S-3 repair criterion that is activated, but the
        # separate >30% section-loss escalation cannot be evaluated until
        # the exposed bar is measured.  Do not assert that it has fired.
        if defect_type == "Spalls" and "suspected section loss" in text.lower():
            pending = TUN[f"Threshold-{defect_id}-SectionLoss30"]
            _named(graph, pending, TUN.Threshold)
            graph.add((pending, RDFS.label,
                       Literal("Rebar section loss > 30%")))
            graph.add((pending, RDFS.comment, Literal(
                "Not evaluable: actual rebar section loss has not been measured."
            )))
            graph.add((pending, TUN.status, Literal("NotEvaluable")))
            graph.add((pending, TUN.operator, Literal(">")))
            graph.add((pending, TUN.value, Literal(30)))
            graph.add((pending, TUN.unit, Literal("%")))
            graph.add((pending, TUN.tier, TUN.Investigation_Required))
            graph.add((pending, PROV.wasDerivedFrom,
                       TUN["THRESH-COR-REBAR-30PCT"]))
            graph.add((defect, TUN.hasThreshold, pending))
