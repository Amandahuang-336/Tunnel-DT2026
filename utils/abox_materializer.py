"""Materialise the standards-reference graph and Tunnel A case ABox.

The manuscript is the terminology authority.  This module therefore writes
the singular class names and chain properties used in Section 4.3:

    Structure -> DefectCondition -> MeasuredIndicator -> PotentialCause
              -> Threshold -> Intervention

JSON remains the reviewed ingest/audit representation.  The graph produced
here is the queryable ABox used by the evaluator and SPARQL console.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD


TUN = Namespace("http://w3id.org/tunnel-dt/ontology/v1.2#")
STD = Namespace("http://w3id.org/tunnel-dt/governance#")
PROV = Namespace("http://www.w3.org/ns/prov#")

TECHNIQUE_URIS = {
    "RGB": TUN["Technique-RGB"],
    "RGBD": TUN["Technique-RGBD"],
    "Thermal": TUN["Technique-Thermal"],
    "GPR": TUN["Technique-GPR"],
}

TECHNIQUE_CLASSES = {
    "RGB": TUN.RGB,
    "RGBD": TUN.RGBD,
    "Thermal": TUN.Thermal,
    "GPR": TUN.GPR,
}

KNOWN_CLAUSES = {
    "AASHTO Ch16 §16.3.2": STD.Clause_16_3_2_2009,
    "AASHTO Ch16 §16.4.3": STD.Clause_16_4_3_2009,
    "AASHTO Ch16 §16.5": STD.Clause_16_5_2009,
    "AASHTO Ch16 Table 16-1": STD.Clause_Table_16_1_2009,
    "AS 3600": STD.Clause_AS3600,
}


def _named(graph: Graph, uri: URIRef, cls: URIRef) -> None:
    graph.add((uri, RDF.type, cls))
    graph.add((uri, RDF.type, OWL.NamedIndividual))


def _literal(graph: Graph, subject: URIRef, prop: URIRef, value: Any,
             datatype: Optional[URIRef] = None) -> None:
    if value is None or value == "":
        return
    graph.add((subject, prop, Literal(value, datatype=datatype)))


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return text[:96] or "Unspecified"


def _source_uri(graph: Graph, reference: Optional[str]) -> Optional[URIRef]:
    """Return a clause/source individual without pretending every source is a standard."""
    if not reference:
        return None
    if reference in KNOWN_CLAUSES:
        return KNOWN_CLAUSES[reference]

    if reference.startswith("AASHTO"):
        uri = STD[f"Clause-{_slug(reference)}"]
        _named(graph, uri, STD.Clause)
        _literal(graph, uri, STD.clauseRef, reference)
        graph.add((uri, RDFS.label, Literal(reference)))
        return uri

    # Non-standard sources (supplier specifications, QA protocols, and
    # domain practice) remain literal provenance via dcterms:source.
    return None


def _techniques(graph: Graph) -> None:
    for name, uri in TECHNIQUE_URIS.items():
        _named(graph, uri, TECHNIQUE_CLASSES[name])
        graph.add((uri, RDF.type, TUN.MeasurementTechnique))
        graph.add((uri, RDFS.label, Literal(name)))


def _threshold_parts(text: str) -> Tuple[str, Any, str]:
    """Normalise the extracted criterion enough for graph-side evaluation."""
    match = re.search(r">\s*(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return ">", Decimal(match.group(1)), "%"
    if "GS" in text and "F" in text:
        return "in", "GS|F", "code"
    if "No measurable movement" in text or "dormant" in text.lower():
        return "=", "Dormant", "state"
    if "movement" in text.lower() or text.startswith("Any "):
        return "exists", text, "categorical"
    return "=", text, "categorical"


def materialise_reference_abox(graph: Graph, json_path: Path) -> None:
    """Populate the six expert-validated, standards-derived FMEA records."""
    if not json_path.exists():
        return
    records = json.loads(json_path.read_text(encoding="utf-8"))
    _techniques(graph)

    for record in records:
        component_data = record.get("component") or {}
        mechanism_data = record.get("mechanism") or {}
        defect_data = record.get("defect") or {}
        cause_data = record.get("cause") or {}
        intervention_data = record.get("intervention") or {}

        component = TUN[component_data.get("component_id") or
                        f"Component-{_slug(record['fmea_chain_id'])}"]
        mechanism = TUN[mechanism_data.get("mechanism_id") or
                        f"Mechanism-{_slug(record['fmea_chain_id'])}"]
        defect = TUN[defect_data.get("defect_id") or
                     f"Defect-{_slug(record['fmea_chain_id'])}"]
        cause = TUN[cause_data.get("cause_id") or
                    f"Cause-{_slug(record['fmea_chain_id'])}"]
        intervention = TUN[intervention_data.get("intervention_id") or
                           f"Intervention-{_slug(record['fmea_chain_id'])}"]

        _named(graph, component, TUN.Structure)
        _literal(graph, component, RDFS.label, component_data.get("component_name"))
        _literal(graph, component, RDFS.comment,
                 component_data.get("material_system"))

        _named(graph, mechanism, TUN.FailureMechanism)
        _literal(graph, mechanism, RDFS.label,
                 mechanism_data.get("mechanism_category"))
        _literal(graph, mechanism, RDFS.comment,
                 mechanism_data.get("mechanism_description"))

        _named(graph, defect, TUN.DefectCondition)
        _literal(graph, defect, RDFS.label, defect_data.get("defect_name"))
        _literal(graph, defect, TUN.hasDescription,
                 defect_data.get("defect_description"))
        graph.add((defect, TUN.locatedAt, component))
        graph.add((defect, TUN.hasMechanism, mechanism))

        indicator_by_id: Dict[str, URIRef] = {}
        for indicator_data in record.get("indicators") or []:
            indicator = TUN[indicator_data["indicator_id"]]
            indicator_by_id[indicator_data["indicator_id"]] = indicator
            _named(graph, indicator, TUN.MeasuredIndicator)
            _literal(graph, indicator, RDFS.label,
                     indicator_data.get("indicator_name"))
            _literal(graph, indicator, TUN.indicatorType,
                     indicator_data.get("indicator_type"))
            _literal(graph, indicator, TUN.unit, indicator_data.get("unit"))
            _literal(graph, indicator, RDFS.comment,
                     indicator_data.get("measurement_method"))
            graph.add((defect, TUN.hasIndicator, indicator))

        _named(graph, cause, TUN.PotentialCause)
        _literal(graph, cause, RDFS.label, cause_data.get("cause_category"))
        _literal(graph, cause, RDFS.comment,
                 cause_data.get("cause_description"))
        _literal(graph, cause, TUN.status,
                 cause_data.get("inference_confidence"))
        graph.add((defect, TUN.hasCause, cause))

        _named(graph, intervention, TUN.Intervention)
        _literal(graph, intervention, RDFS.label,
                 intervention_data.get("intervention_name"))
        _literal(graph, intervention, TUN.status,
                 intervention_data.get("intervention_category"))
        _literal(graph, intervention, RDFS.comment,
                 intervention_data.get("intervention_name"))
        intervention_source = _source_uri(
            graph, intervention_data.get("source_reference")
        )
        if intervention_source:
            graph.add((intervention, TUN.sourceReference, intervention_source))

        for order, step_text in enumerate(
            intervention_data.get("intervention_steps") or [], start=1
        ):
            step = TUN[f"{intervention_data.get('intervention_id', 'Intervention')}-Step-{order:02d}"]
            _named(graph, step, TUN.InterventionStep)
            _literal(graph, step, TUN.stepOrder, order, XSD.integer)
            _literal(graph, step, RDFS.comment, step_text)
            graph.add((intervention, TUN.hasStep, step))

        for threshold_data in record.get("thresholds") or []:
            threshold = TUN[threshold_data["threshold_id"]]
            _named(graph, threshold, TUN.Threshold)
            criterion = threshold_data.get("threshold_value") or ""
            operator, value, unit = _threshold_parts(criterion)
            _literal(graph, threshold, RDFS.label, criterion)
            _literal(graph, threshold, RDFS.comment,
                     threshold_data.get("threshold_consequence"))
            _literal(graph, threshold, TUN.operator, operator)
            _literal(graph, threshold, TUN.value, value)
            _literal(graph, threshold, TUN.unit,
                     threshold_data.get("threshold_unit") or unit)
            tier_name = threshold_data.get("threshold_type")
            if tier_name:
                graph.add((threshold, TUN.tier, TUN[tier_name]))
            indicator_ref = indicator_by_id.get(threshold_data.get("indicator_ref"))
            if indicator_ref:
                graph.add((threshold, TUN.onIndicator, indicator_ref))
            source = _source_uri(graph, threshold_data.get("source_reference"))
            if source:
                graph.add((threshold, TUN.derivedFrom, source))
                graph.add((threshold, TUN.sourceReference, source))
            graph.add((defect, TUN.hasThreshold, threshold))
            graph.add((threshold, TUN.prescribesIntervention, intervention))


def _indicator_unit(finding: str) -> str:
    units = []
    for token, label in [
        ("mm", "mm"), ("cm²", "cm2"), ("cm", "cm"), ("m", "m"),
        ("°C", "degC"), ("%", "%"),
    ]:
        if token in finding:
            units.append(label)
    return "|".join(dict.fromkeys(units)) if units else "categorical"


def materialise_case_abox(graph: Graph, defects: Iterable[Dict[str, Any]]) -> None:
    """Populate the Tunnel A inspection ABox, including FMEA levels 4, 5 and 7.

    Level 6 activation is deliberately left to ``evaluate_case_thresholds``
    so that the threshold link is produced by graph-side evaluation rather
    than copied uncritically from display text.
    """
    _techniques(graph)

    for data in defects:
        defect_id = data.get("defect_id")
        if not defect_id:
            continue
        defect = TUN[defect_id]
        ring_id = data.get("ring_id")
        component = TUN[f"Structure-Ring-{ring_id}"]
        _named(graph, component, TUN.Structure)
        _literal(graph, component, RDFS.label,
                 f"Concrete lining at Ring {ring_id}")
        graph.add((defect, TUN.locatedAt, component))

        mechanism = TUN[f"Mechanism-{defect_id}"]
        _named(graph, mechanism, TUN.FailureMechanism)
        _literal(graph, mechanism, RDFS.label, data.get("failure_mechanism"))
        _literal(graph, mechanism, RDFS.comment,
                 data.get("failure_mechanism"))
        graph.add((defect, TUN.hasMechanism, mechanism))

        direct_techniques = set(graph.objects(defect, TUN.isDetectedWith))
        evidence = data.get("modality_evidence") or {}
        for modality, observation_data in evidence.items():
            technique = TECHNIQUE_URIS.get(modality)
            if technique is None or technique not in direct_techniques:
                continue

            observation = TUN[f"Observation-{defect_id}-{modality}"]
            _named(graph, observation, TUN.DefectObservation)
            graph.add((observation, TUN.locatedAt, component))
            graph.add((observation, TUN.isDetectedWith, technique))
            graph.add((defect, TUN.hasObservation, observation))
            _literal(graph, observation, TUN.status,
                     observation_data.get("status") or "Unspecified")
            _literal(graph, observation, TUN.provisionalClass,
                     data.get("defect_type"))
            _literal(graph, observation, TUN.confidence,
                     Decimal(str(observation_data.get("confidence", 0))),
                     XSD.decimal)
            finding = observation_data.get("finding")
            _literal(graph, observation, RDFS.comment, finding)

            if not finding:
                continue
            indicator = TUN[f"Indicator-{defect_id}-{modality}"]
            _named(graph, indicator, TUN.MeasuredIndicator)
            _literal(graph, indicator, RDFS.label,
                     f"{modality} indicator for {defect_id}")
            _literal(graph, indicator, TUN.indicatorType,
                     observation_data.get("fmea_level") or "Indicator")
            _literal(graph, indicator, TUN.hasValue, finding)
            _literal(graph, indicator, TUN.unit, _indicator_unit(finding))
            _literal(graph, indicator, TUN.confidence,
                     Decimal(str(observation_data.get("confidence", 0))),
                     XSD.decimal)
            graph.add((indicator, TUN.isDetectedWith, technique))
            level = observation_data.get("fmea_level")
            level_uri = {
                "Indicator": TUN.MeasuredIndicatorLevel,
                "Cause": TUN.PotentialCauseLevel,
                "Structure": TUN.StructureLevel,
            }.get(level, TUN.MeasuredIndicatorLevel)
            graph.add((indicator, TUN.atFMEALevel, level_uri))
            graph.add((defect, TUN.hasIndicator, indicator))

        cause = TUN[f"Cause-{defect_id}"]
        _named(graph, cause, TUN.PotentialCause)
        _literal(graph, cause, RDFS.label, data.get("potential_cause"))
        _literal(graph, cause, RDFS.comment, data.get("potential_cause"))
        graph.add((defect, TUN.hasCause, cause))

        threshold = TUN[f"Threshold-{defect_id}"]
        _named(graph, threshold, TUN.Threshold)
        _literal(graph, threshold, RDFS.label, data.get("threshold_triggered"))
        _literal(graph, threshold, RDFS.comment,
                 data.get("threshold_triggered"))
        _literal(graph, threshold, TUN.value, data.get("threshold_triggered"))
        _literal(graph, threshold, TUN.status, "Candidate")
        source = _source_uri(graph, data.get("threshold_reference"))
        if source:
            # Direct final hop for CQ-25/CQ-26. The JSON reference is a
            # human-readable import value; the ABox relation is an IRI.
            graph.add((defect, TUN.sourceReference, source))
            graph.add((threshold, TUN.derivedFrom, source))
            graph.add((threshold, TUN.sourceReference, source))

        intervention = TUN[f"Intervention-{defect_id}"]
        _named(graph, intervention, TUN.Intervention)
        _literal(graph, intervention, RDFS.label,
                 f"Case prescription for {defect_id}")
        _literal(graph, intervention, RDFS.comment,
                 f"Ordered intervention plan for {defect_id}")

        for order, step_data in enumerate(
            data.get("prescribed_interventions") or [], start=1
        ):
            step = TUN[f"Intervention-{defect_id}-Step-{order:02d}"]
            _named(graph, step, TUN.InterventionStep)
            _literal(graph, step, TUN.stepOrder, order, XSD.integer)
            _literal(graph, step, RDFS.comment, step_data.get("step"))
            _literal(graph, step, TUN.rationale, step_data.get("rationale"))
            graph.add((intervention, TUN.hasStep, step))
            step_source = _source_uri(graph, step_data.get("reference"))
            if step_source:
                graph.add((step, TUN.sourceReference, step_source))
            elif step_data.get("reference"):
                _literal(graph, step, DCTERMS.source, step_data["reference"])


def load_json_records(path: Path) -> list[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
