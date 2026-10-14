"""Regression verification for manuscript-aligned FMEA ABox population."""

from __future__ import annotations

import sys
import types
from pathlib import Path

from rdflib import Namespace, URIRef
from rdflib.namespace import OWL, RDF


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

streamlit_mock = types.ModuleType("streamlit")
streamlit_mock.warning = lambda *args, **kwargs: None
streamlit_mock.cache_resource = lambda **kwargs: (lambda func: func)
streamlit_mock.cache_data = lambda **kwargs: (lambda func: func)
sys.modules["streamlit"] = streamlit_mock

from utils.ontology_loader import load_ontology  # noqa: E402
from utils.sparql_queries import (  # noqa: E402
    query_clause_traceability_for_defect,
    query_fmea_chain_for_defect,
)


TUN = Namespace("http://w3id.org/tunnel-dt/ontology/v1.2#")
STD = Namespace("http://w3id.org/tunnel-dt/governance#")

CASE_IDS = [
    "D-1247-L", "D-1158-S", "D-0923-C", "D-1402-L",
    "D-0756-C", "D-1089-C", "D-0614-L",
]

EXPECTED_CASE_CLAUSES = {
    "D-1247-L": STD.Clause_16_3_2_2009,
    "D-1158-S": STD.Clause_16_4_3_2009,
    "D-0923-C": STD.Clause_16_5_2009,
    "D-1402-L": STD.Clause_Table_16_1_2009,
    "D-0756-C": STD.Clause_16_5_2009,
    "D-1089-C": STD.Clause_AS3600,
    "D-0614-L": STD.Clause_Table_16_1_2009,
}

REFERENCE_DEFECT_IDS = [
    "DEF-COR-SPALL-01", "DEF-LEAK-CRACK-01", "DEF-COR-STEEL-PENETRATION-01",
    "DEF-HANG-FAIL-01", "DEF-CRACK-STRUCT-01", "DEF-ROCK-FALL-01",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    graph = load_ontology()

    class_capabilities = {
        (defect_class, modality_class)
        for defect_class, modality_class
        in graph.subject_objects(TUN.isDetectedWith)
        if (defect_class, RDF.type, OWL.Class) in graph
        and (modality_class, RDF.type, OWL.Class) in graph
    }
    expected_class_capabilities = {
        (TUN.Delaminations, TUN.Thermal),
        (TUN.Delaminations, TUN.GPR),
    }
    require(class_capabilities == expected_class_capabilities,
            "Scenario 5 must have exactly the manuscript-supported "
            "Thermal and GPR positive capabilities for Delaminations")

    class_limitations = {
        (modality_class, defect_class)
        for modality_class, defect_class
        in graph.subject_objects(TUN.cannotDetect)
        if (modality_class, RDF.type, OWL.Class) in graph
        and (defect_class, RDF.type, OWL.Class) in graph
    }
    require(len(class_limitations) == 5,
            f"Expected 5 class-level cannotDetect assertions, "
            f"got {len(class_limitations)}")
    contradictions = {
        (defect_class, modality_class)
        for defect_class, modality_class in class_capabilities
        if (modality_class, defect_class) in class_limitations
    }
    require(not contradictions,
            f"Contradictory class-level modality capabilities: "
            f"{sorted(map(str, contradictions))}")

    scenario_5_query = (
        ROOT / "queries" / "modality_capability_delamination.rq"
    ).read_text()
    scenario_5_rows = list(graph.query(scenario_5_query))
    scenario_5_answers = {
        (str(row.capability), row.modality)
        for row in scenario_5_rows
    }
    require(scenario_5_answers == {
        ("can detect", TUN.Thermal),
        ("can detect", TUN.GPR),
        ("cannot detect", TUN.RGB),
        ("cannot detect", TUN.RGBD),
    }, "Scenario 5 SPARQL answer is incomplete or contradictory")

    direct_detection = {
        (defect, technique)
        for defect_id in CASE_IDS
        for defect in [TUN[defect_id]]
        for technique in graph.objects(defect, TUN.isDetectedWith)
    }
    require(len(direct_detection) == 27,
            f"Expected 27 case isDetectedWith assertions, got {len(direct_detection)}")

    for defect_id, expected_clause in EXPECTED_CASE_CLAUSES.items():
        defect = TUN[defect_id]
        clause_links = set(graph.objects(defect, TUN.sourceReference))
        require(clause_links == {expected_clause},
                f"{defect_id}: expected one direct clause IRI, "
                f"got {sorted(map(str, clause_links))}")
        require(all(isinstance(clause, URIRef) for clause in clause_links),
                f"{defect_id}: clause link must be an IRI, not a literal")
        require((expected_clause, RDF.type, STD.Clause) in graph,
                f"{defect_id}: clause IRI is not a std:Clause")
        require(any(graph.objects(expected_clause, STD.clauseRef)),
                f"{defect_id}: clause missing clauseRef")
        require(any(graph.objects(expected_clause, STD.inEdition)),
                f"{defect_id}: clause missing inEdition")
        require(any(graph.objects(expected_clause, STD.textHash)),
                f"{defect_id}: clause missing textHash")

    for defect_id in CASE_IDS:
        defect = TUN[defect_id]
        require(any(graph.objects(defect, TUN.locatedAt)),
                f"{defect_id}: missing L1 locatedAt")
        require(any(graph.objects(defect, TUN.hasMechanism)),
                f"{defect_id}: missing L2 hasMechanism")
        require(any(graph.objects(defect, TUN.hasIndicator)),
                f"{defect_id}: missing L4 hasIndicator")
        require(any(graph.objects(defect, TUN.hasCause)),
                f"{defect_id}: missing L5 hasCause")
        thresholds = list(graph.objects(defect, TUN.hasThreshold))
        require(thresholds, f"{defect_id}: missing L6 hasThreshold")
        require(any(
            any(graph.objects(threshold, TUN.prescribesIntervention))
            for threshold in thresholds
        ), f"{defect_id}: missing L7 prescribesIntervention")

    case_steps = {
        step
        for defect_id in CASE_IDS
        for threshold in graph.objects(TUN[defect_id], TUN.hasThreshold)
        for intervention in graph.objects(threshold, TUN.prescribesIntervention)
        for step in graph.objects(intervention, TUN.hasStep)
    }
    require(len(case_steps) == 18,
            f"Expected 18 case intervention steps, got {len(case_steps)}")

    pending = TUN["Threshold-D-1158-S-SectionLoss30"]
    require(str(graph.value(pending, TUN.status)) == "NotEvaluable",
            "D-1158-S >30% threshold must remain NotEvaluable")

    for defect_id in REFERENCE_DEFECT_IDS:
        defect = TUN[defect_id]
        require(any(graph.objects(defect, TUN.hasIndicator)),
                f"Reference chain {defect_id}: missing indicators")
        require(any(graph.objects(defect, TUN.hasCause)),
                f"Reference chain {defect_id}: missing cause")
        require(any(graph.objects(defect, TUN.hasThreshold)),
                f"Reference chain {defect_id}: missing threshold")

    rows = list(graph.query(query_fmea_chain_for_defect("D-1247-L")))
    require(rows, "Canonical SPARQL chain query returned no rows for D-1247-L")
    require(any(row.threshold and row.intervention for row in rows),
            "SPARQL traversal did not reach L6/L7 for D-1247-L")

    audit_rows = list(graph.query(
        query_clause_traceability_for_defect("D-1158-S")
    ))
    require(len(audit_rows) == 1,
            "CQ-25/CQ-26 must return one audit path for D-1158-S")
    audit = audit_rows[0]
    require(audit.clause == STD.Clause_16_4_3_2009,
            "CQ-25 did not reach AASHTO Ch16 §16.4.3 by IRI")
    require(audit.threshold == TUN["Threshold-D-1158-S"]
            and audit.intervention == TUN["Intervention-D-1158-S"],
            "CQ-26 did not traverse threshold to selected intervention")
    require(str(audit.clauseRef) == "AASHTO Ch16 §16.4.3"
            and str(audit.editionName) == "2009"
            and bool(str(audit.textHash)),
            "Audit path did not reach clause identity and edition metadata")

    print("FMEA ABox verification: PASS")
    print(f"Graph triples after OWL-RL closure: {len(graph):,}")
    print("Case defects: 7")
    print("Defect-level isDetectedWith assertions: 27")
    print("Direct defect-to-clause IRI links: 7")
    print("CQ-25/CQ-26 clause audit path: D-1158-S -> §16.4.3 (2009) -> intervention")
    print("Class-level isDetectedWith assertions: 2 (Delaminations -> Thermal, GPR)")
    print("Class-level cannotDetect assertions: 5")
    print("Scenario 5 delamination capability query: 4 symmetric answers")
    print("Case intervention steps: 18")
    print("Reference FMEA chains: 6")
    print("D-1158-S section-loss threshold: NotEvaluable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
