"""Regenerate ontology/fmea_abox.ttl from the reviewed JSON sources.

This exports asserted individuals only (no OWL-RL closure), keeping the TBox
and ABox physically inspectable as separate repository artifacts.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

streamlit_mock = types.ModuleType("streamlit")
streamlit_mock.warning = lambda *args, **kwargs: None
streamlit_mock.cache_resource = lambda **kwargs: (lambda func: func)
streamlit_mock.cache_data = lambda **kwargs: (lambda func: func)
sys.modules.setdefault("streamlit", streamlit_mock)

from utils.abox_materializer import (  # noqa: E402
    load_json_records,
    materialise_case_abox,
    materialise_reference_abox,
)
from utils.fmea_evaluator import evaluate_case_thresholds  # noqa: E402
from utils.ontology_loader import _materialise_json_defects_into_graph  # noqa: E402


TUN = Namespace("http://w3id.org/tunnel-dt/ontology/v1.2#")
STD = Namespace("http://w3id.org/tunnel-dt/governance#")


def main() -> int:
    working = Graph()
    for filename in ("tunnel_maintenance.ttl", "standards_governance.ttl"):
        working.parse(ROOT / "ontology" / filename, format="turtle")

    _materialise_json_defects_into_graph(working)
    materialise_reference_abox(
        working, ROOT / "data" / "fmea_chains_aashto.json"
    )
    materialise_case_abox(
        working, load_json_records(ROOT / "data" / "defects_tunnel_a.json")
    )
    evaluate_case_thresholds(working)

    exported = Graph()
    exported.bind("tun", TUN)
    exported.bind("std", STD)
    exported.bind("owl", OWL)

    individuals = {
        subject
        for subject in working.subjects(RDF.type, OWL.NamedIndividual)
        if str(subject).startswith(str(TUN)) or str(subject).startswith(str(STD))
    }
    for subject in individuals:
        for triple in working.triples((subject, None, None)):
            exported.add(triple)

    output = ROOT / "ontology" / "fmea_abox.ttl"
    exported.serialize(output, format="turtle")
    print(f"Wrote {len(exported):,} asserted ABox triples to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
