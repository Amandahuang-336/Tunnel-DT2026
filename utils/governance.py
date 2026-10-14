"""
Knowledge-base governance — temporal portability
================================================

Implements the manuscript's governance layer: the mechanisms that let the
knowledge base survive revision of the standards it was built from.

    (a) Edition-bound, time-boxed thresholds   -> resolve_thresholds()
    (b) Versioning on every axis (PROV-O)      -> kb_state()
    (c) Decision manifest                      -> build_manifest()
    (d) Impact analysis on revision            -> impact_analysis()
    (e) Regression corpus                      -> run_regression()
    (f) Deprecation and migration policy       -> migration_actions()

DESIGN NOTES
------------
Nothing here mutates the graph. A revision is modelled as *adding* a second
std:StandardEdition with its own clauses and thresholds; the edition in force
on a given date is then a query, not a state change. That is what makes a past
prescription reconstructible.

The module degrades cleanly. If ontology/standards_governance.ttl is absent, or
if only one edition is loaded, every function returns an empty/neutral result
rather than raising — the rest of the app is unaffected.

No threshold values, tolerances, or counts are invented here. Everything is read
from the graph; where the graph is silent, the function says so.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS

TUN = Namespace("http://w3id.org/tunnel-dt/ontology/v1.2#")
STD = Namespace("http://w3id.org/tunnel-dt/governance#")
ED = Namespace("http://w3id.org/tunnel-dt/governance/edition#")
PROV = Namespace("http://www.w3.org/ns/prov#")

ROOT = Path(__file__).parent.parent
ONTOLOGY_DIR = ROOT / "ontology"

MANIFEST_SCHEMA_VERSION = "1.0.0"

# Ordered so a tier change can be reported as an escalation or a relaxation.
TIER_ORDER = [
    "Acceptable",
    "Monitor_Closely",
    "Investigation_Required",
    "Action_Required",
    "Emergency",
]


def _tier_rank(tier: Optional[str]) -> int:
    try:
        return TIER_ORDER.index(tier) if tier else -1
    except ValueError:
        return -1


def _s(value: Any) -> Optional[str]:
    """Literal / URIRef -> plain string."""
    if value is None:
        return None
    return str(value)


def _local(uri: Any) -> str:
    """Trailing fragment of an IRI, for display."""
    text = str(uri)
    for sep in ("#", "/"):
        if sep in text:
            text = text.rsplit(sep, 1)[-1]
    return text


#: Public alias — UI code should use this rather than the private form.
local_name = _local


# =============================================================================
# (a) Editions and time-boxed thresholds
# =============================================================================
@dataclass
class Edition:
    iri: str
    label: str
    publisher: Optional[str] = None
    title: Optional[str] = None
    edition: Optional[str] = None
    effective_from: Optional[str] = None
    superseded_by: Optional[str] = None

    @property
    def short(self) -> str:
        return self.label or _local(self.iri)


@dataclass
class Threshold:
    iri: str
    label: str
    defect_class: Optional[str]
    indicator: Optional[str]
    operator: Optional[str]
    value: Optional[float]
    unit: Optional[str]
    tier: Optional[str]
    criterion_text: Optional[str]
    clause_ref: Optional[str]
    clause_iri: Optional[str]
    edition_iri: Optional[str]
    valid_from: Optional[str]
    valid_to: Optional[str]

    def in_force_on(self, when: date) -> bool:
        """True if this threshold's validity interval covers `when`."""
        if self.valid_from:
            try:
                if when < date.fromisoformat(self.valid_from[:10]):
                    return False
            except ValueError:
                pass
        if self.valid_to:
            try:
                if when > date.fromisoformat(self.valid_to[:10]):
                    return False
            except ValueError:
                pass
        return True

    def criterion(self) -> str:
        """Human-readable criterion for the report's L6 field."""
        if self.criterion_text:
            return self.criterion_text
        if self.operator and self.value is not None:
            return f"{self.indicator or 'indicator'} {self.operator} {self.value}{self.unit or ''}"
        return self.label


def list_editions(graph: Graph) -> List[Edition]:
    """Every std:StandardEdition present in the graph, in label order."""
    out: List[Edition] = []
    for subj in graph.subjects(RDF.type, STD.StandardEdition):
        out.append(
            Edition(
                iri=str(subj),
                label=_s(graph.value(subj, RDFS.label)) or _local(subj),
                publisher=_s(graph.value(subj, STD.publisher)),
                title=_s(graph.value(subj, STD.title)),
                edition=_s(graph.value(subj, STD.edition)),
                effective_from=_s(graph.value(subj, STD.effectiveFrom)),
                superseded_by=_s(graph.value(subj, STD.supersededBy)),
            )
        )
    return sorted(out, key=lambda e: e.short)


def list_thresholds(graph: Graph, edition_iri: Optional[str] = None) -> List[Threshold]:
    """
    Thresholds in the graph, optionally restricted to one edition.

    Reads through std:derivedFrom -> std:Clause -> std:inEdition, so a
    threshold with no clause binding is excluded: an unbound threshold is
    exactly what the governance layer exists to prevent.
    """
    out: List[Threshold] = []
    for subj in graph.subjects(RDF.type, STD.Threshold):
        clause = graph.value(subj, STD.derivedFrom)
        edition = graph.value(clause, STD.inEdition) if clause else None
        if edition_iri and str(edition) != edition_iri:
            continue

        raw_value = graph.value(subj, STD.value)
        try:
            numeric = float(raw_value) if raw_value is not None else None
        except (TypeError, ValueError):
            numeric = None

        out.append(
            Threshold(
                iri=str(subj),
                label=_s(graph.value(subj, RDFS.label)) or _local(subj),
                defect_class=_s(graph.value(subj, STD.appliesToClass)),
                indicator=_s(graph.value(subj, STD.onIndicator)),
                operator=_s(graph.value(subj, STD.operator)),
                value=numeric,
                unit=_s(graph.value(subj, STD.unit)),
                tier=_s(graph.value(subj, STD.tier)),
                criterion_text=_s(graph.value(subj, STD.criterionText)),
                clause_ref=_s(graph.value(clause, STD.clauseRef)) if clause else None,
                clause_iri=str(clause) if clause else None,
                edition_iri=str(edition) if edition else None,
                valid_from=_s(graph.value(subj, STD.validFrom)),
                valid_to=_s(graph.value(subj, STD.validTo)),
            )
        )
    return out


def resolve_thresholds(
    graph: Graph,
    defect_class: str,
    as_of: Optional[date] = None,
) -> List[Threshold]:
    """
    Thresholds applying to `defect_class` that were in force on `as_of`.

    This is the reconstruction primitive: asking for a past date returns the
    criteria that actually justified a prescription issued then, even after a
    later edition has been loaded.
    """
    when = as_of or date.today()
    key = defect_class.strip().lower()
    matches = []
    for thr in list_thresholds(graph):
        if not thr.defect_class:
            continue
        if _local(thr.defect_class).lower() != key:
            continue
        if thr.in_force_on(when):
            matches.append(thr)
    return matches


def clause_for_reference(graph: Graph, clause_ref: str) -> Optional[Tuple[str, str]]:
    """
    Map a bare clause string (as carried on legacy defect records) to
    (clause_iri, edition_iri). Returns None when the reference is not bound to
    any edition — which is the condition the Governance page reports as an
    unbound citation.
    """
    if not clause_ref:
        return None
    target = clause_ref.strip().lower()
    for clause in graph.subjects(RDF.type, STD.Clause):
        ref = _s(graph.value(clause, STD.clauseRef))
        if ref and ref.strip().lower() == target:
            edition = graph.value(clause, STD.inEdition)
            return str(clause), str(edition) if edition else ""
    return None


def unbound_clause_references(
    graph: Graph, defects: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Defect records whose threshold_reference resolves to no dated clause.

    These are the records that cannot be reconstructed after a revision, and
    they are the concrete work item the governance layer creates.
    """
    out = []
    for d in defects:
        ref = (d.get("threshold_reference") or "").strip()
        if not ref:
            out.append({"defect_id": d.get("defect_id", "?"), "reference": "(none)"})
            continue
        if clause_for_reference(graph, ref) is None:
            out.append({"defect_id": d.get("defect_id", "?"), "reference": ref})
    return out


# =============================================================================
# (b) Versioning on every axis
# =============================================================================
def _hash_files(paths: List[Path]) -> str:
    """Stable SHA-256 over a set of files, order-independent."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.name):
        if path.exists():
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def kb_state(graph: Optional[Graph] = None) -> Dict[str, Any]:
    """
    The versioned configuration currently in force.

    Every field is read from the environment rather than asserted: the ontology
    version comes from owl:versionIRI where present, the rule-set hash from the
    ontology files on disk. Where a value is genuinely unknown it is reported as
    None rather than filled in.
    """
    ttl_files = sorted(ONTOLOGY_DIR.glob("*.ttl")) if ONTOLOGY_DIR.exists() else []

    version_iri = None
    vocab_version = None
    if graph is not None:
        for _, _, obj in graph.triples((None, URIRef("http://www.w3.org/2002/07/owl#versionIRI"), None)):
            if "governance" not in str(obj):
                version_iri = str(obj)
                break
        if version_iri is None:
            for _, _, obj in graph.triples((None, URIRef("http://www.w3.org/2002/07/owl#versionIRI"), None)):
                version_iri = str(obj)
                break
        for run in graph.subjects(RDF.type, STD.ExtractionRun):
            vocab_version = _s(graph.value(run, STD.vocabVersion))
            break

    return {
        "ontology_version_iri": version_iri,
        "vocabulary_version": vocab_version,
        "threshold_set_id": _hash_files([p for p in ttl_files if "governance" in p.name]),
        "ruleset_hash": _hash_files(ttl_files),
        "ontology_files": [p.name for p in ttl_files],
        "reasoner": {"name": "owlrl", "profile": "OWL 2 RL"},
        "captured_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def extraction_provenance(graph: Graph) -> List[Dict[str, Any]]:
    """PROV-O extraction runs asserted in the graph."""
    out = []
    for run in graph.subjects(RDF.type, STD.ExtractionRun):
        used = graph.value(run, PROV.used)
        agent = graph.value(run, PROV.wasAssociatedWith)
        out.append({
            "run": _local(run),
            "label": _s(graph.value(run, RDFS.label)),
            "used_edition": _local(used) if used else None,
            "engine_id": _s(graph.value(run, STD.engineId)),
            "engine_version": _s(graph.value(run, STD.engineVersion)),
            "decoding_config": _s(graph.value(run, STD.decodingConfig)),
            "prompt_hash": _s(graph.value(run, STD.promptHash)),
            "vocab_version": _s(graph.value(run, STD.vocabVersion)),
            "reviewer": _s(graph.value(agent, RDFS.label)) if agent else None,
        })
    return out


# =============================================================================
# (c) Decision manifest
# =============================================================================
@dataclass
class DecisionManifest:
    manifest_version: str
    manifest_id: str
    issued_at: str
    defect_id: str
    knowledge_base: Dict[str, Any]
    inputs: List[Dict[str, Any]]
    output: Dict[str, Any]
    endorsement: Dict[str, Any]
    manifest_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)


def build_manifest(
    defect: Dict[str, Any],
    graph: Optional[Graph] = None,
    endorsed_by: Optional[str] = None,
    assurance_stage: int = 2,
) -> DecisionManifest:
    """
    Freeze the configuration that produced one prescription.

    Re-running against a stored manifest either reproduces the prescription or
    returns a diff — the property that turns traceability from citation into
    reconstruction.
    """
    defect_id = str(defect.get("defect_id", "UNKNOWN"))
    issued = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    inputs = []
    for modality, ev in (defect.get("modality_evidence") or {}).items():
        if not isinstance(ev, dict):
            continue
        inputs.append({
            "modality": modality,
            "fmea_level": ev.get("fmea_level"),
            "finding": ev.get("finding"),
            "status": ev.get("status"),
            "confidence": ev.get("confidence"),
        })

    clause_ref = defect.get("threshold_reference")
    binding = clause_for_reference(graph, clause_ref) if (graph and clause_ref) else None

    output = {
        "defect_type": defect.get("defect_type"),
        "failure_mechanism": defect.get("failure_mechanism"),
        "potential_cause": defect.get("potential_cause"),
        "criterion": defect.get("threshold_triggered"),
        "clause_ref": clause_ref,
        "clause_iri": binding[0] if binding else None,
        "standard_edition_iri": binding[1] if binding else None,
        "edition_bound": binding is not None,
        "severity": defect.get("severity"),
        "priority": defect.get("priority"),
        "completeness_score": defect.get("completeness_score"),
    }

    manifest = DecisionManifest(
        manifest_version=MANIFEST_SCHEMA_VERSION,
        manifest_id=f"DM-{defect_id}",
        issued_at=issued,
        defect_id=defect_id,
        knowledge_base=kb_state(graph),
        inputs=inputs,
        output=output,
        endorsement={
            "mode": "endorsed_unchanged" if endorsed_by else "unendorsed",
            "endorsed_by": endorsed_by,
            "assurance_stage": assurance_stage,
        },
    )

    # Hash over the canonical serialisation with the hash field removed, so any
    # later edit to the manifest is detectable.
    body = manifest.to_dict()
    body.pop("manifest_hash", None)
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    manifest.manifest_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return manifest


def verify_manifest(manifest_json: str) -> Tuple[bool, str]:
    """Recompute a stored manifest's hash. Returns (ok, message)."""
    try:
        body = json.loads(manifest_json)
    except json.JSONDecodeError as exc:
        return False, f"Not valid JSON: {exc}"

    stored = body.pop("manifest_hash", None)
    if not stored:
        return False, "No manifest_hash present."
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    recomputed = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if recomputed == stored:
        return True, "Hash matches — manifest is unaltered."
    return False, f"Hash mismatch.\n  stored:     {stored}\n  recomputed: {recomputed}"


# =============================================================================
# (d) Impact analysis on revision
# =============================================================================
@dataclass
class ImpactRow:
    defect_id: str
    defect_type: str
    chainage_m: Optional[float]
    criterion_now: str
    tier_now: Optional[str]
    criterion_next: str
    tier_next: Optional[str]
    direction: str          # "escalates" | "relaxes" | "changes"


def impact_analysis(
    graph: Graph,
    defects: List[Dict[str, Any]],
    edition_now_iri: str,
    edition_next_iri: str,
) -> List[ImpactRow]:
    """
    Open defects whose activated tier would change if `edition_next` replaced
    `edition_now`.

    Returns an empty list when only one edition is loaded — which is the honest
    result, not a failure. Load a second edition file to exercise this.
    """
    if not edition_now_iri or not edition_next_iri or edition_now_iri == edition_next_iri:
        return []

    now_by_class: Dict[str, Threshold] = {}
    next_by_class: Dict[str, Threshold] = {}
    for thr in list_thresholds(graph, edition_now_iri):
        if thr.defect_class:
            now_by_class[_local(thr.defect_class).lower()] = thr
    for thr in list_thresholds(graph, edition_next_iri):
        if thr.defect_class:
            next_by_class[_local(thr.defect_class).lower()] = thr

    rows: List[ImpactRow] = []
    for d in defects:
        if str(d.get("status", "Active")).lower() not in ("active", "open"):
            continue
        key = str(d.get("defect_type", "")).strip().lower()
        thr_now = now_by_class.get(key)
        thr_next = next_by_class.get(key)
        if not thr_now or not thr_next:
            continue
        if _tier_rank(thr_now.tier) == _tier_rank(thr_next.tier) and \
           thr_now.criterion() == thr_next.criterion():
            continue

        delta = _tier_rank(thr_next.tier) - _tier_rank(thr_now.tier)
        direction = "escalates" if delta > 0 else ("relaxes" if delta < 0 else "changes")

        rows.append(ImpactRow(
            defect_id=str(d.get("defect_id", "?")),
            defect_type=str(d.get("defect_type", "?")),
            chainage_m=d.get("chainage_m"),
            criterion_now=thr_now.criterion(),
            tier_now=thr_now.tier,
            criterion_next=thr_next.criterion(),
            tier_next=thr_next.tier,
            direction=direction,
        ))

    rows.sort(key=lambda r: (-_tier_rank(r.tier_next), r.defect_id))
    return rows


def impact_summary(rows: List[ImpactRow], total_open: int) -> Dict[str, Any]:
    """Headline counts for the change register. No example figures are invented."""
    return {
        "affected": len(rows),
        "total_open": total_open,
        "escalating": sum(1 for r in rows if r.direction == "escalates"),
        "relaxing": sum(1 for r in rows if r.direction == "relaxes"),
        "to_emergency": sum(1 for r in rows if r.tier_next == "Emergency"),
        "by_tier": {
            tier: sum(1 for r in rows if r.tier_next == tier)
            for tier in TIER_ORDER
            if any(r.tier_next == tier for r in rows)
        },
    }


# =============================================================================
# (e) Regression corpus
# =============================================================================
CORPUS_PATH = ROOT / "data" / "regression_corpus.json"


def load_corpus() -> List[Dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    try:
        with CORPUS_PATH.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload.get("cases", []) if isinstance(payload, dict) else payload
    except (json.JSONDecodeError, OSError):
        return []


def run_regression(graph: Graph, cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Re-evaluate the corpus against the knowledge base currently loaded.

    A case fails when the tier the graph now activates differs from the tier the
    reviewer adjudicated. A tier change is the definition of a regression: it
    must be explained and signed off before the knowledge base is released.
    """
    cases = cases if cases is not None else load_corpus()
    results = []
    for case in cases:
        expected = (case.get("expected") or {})
        want_tier = expected.get("tier")
        defect_class = case.get("defect_class", "")
        as_of = case.get("as_of")
        when = date.fromisoformat(as_of) if as_of else date.today()

        matches = resolve_thresholds(graph, defect_class, when)
        got_tier = matches[0].tier if matches else None

        if not matches:
            status = "no_threshold"
        elif got_tier == want_tier:
            status = "pass"
        else:
            status = "fail"

        results.append({
            "case_id": case.get("case_id", "?"),
            "category": case.get("category", ""),
            "defect_class": defect_class,
            "expected_tier": want_tier,
            "actual_tier": got_tier,
            "status": status,
        })

    return {
        "total": len(results),
        "passed": sum(1 for r in results if r["status"] == "pass"),
        "failed": sum(1 for r in results if r["status"] == "fail"),
        "unresolved": sum(1 for r in results if r["status"] == "no_threshold"),
        "results": results,
    }


# =============================================================================
# (f) Deprecation and migration policy
# =============================================================================
def migration_actions(rows: List[ImpactRow]) -> List[Dict[str, str]]:
    """
    Translate an impact set into the actions the migration policy requires.

    Policy, per the manuscript:
      - issued prescriptions are frozen at issue and never retroactively altered;
      - open defects are re-evaluated at the next scheduled inspection;
      - any defect escalating to the emergency tier is re-evaluated immediately.
    """
    actions = []
    for row in rows:
        if row.tier_next == "Emergency":
            when, why = "Immediately", "Escalates to emergency tier under the incoming edition."
        elif row.direction == "escalates":
            when, why = "Next scheduled inspection", "Tier escalates; prescription in force remains valid until re-assessed."
        else:
            when, why = "Next scheduled inspection", "Criterion changes; no escalation."
        actions.append({
            "defect_id": row.defect_id,
            "action": "Re-evaluate",
            "when": when,
            "rationale": why,
        })
    return actions
