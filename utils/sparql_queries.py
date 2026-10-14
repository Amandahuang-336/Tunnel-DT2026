"""
Pre-built SPARQL queries for common dashboard operations.

Each query is a function returning the query string, so namespaces can
be substituted if your ontology uses different URIs. The raw .rq files
in queries/ mirror these for reference and reuse in other tools.

REVISIONS (Rev 4)
-----------------
- Namespace migrated to http://w3id.org/tunnel-dt/...
- Queries that match defects by class now use the property path
  rdf:type/rdfs:subClassOf* to traverse subclass relationships, since
  defects are typed as subclasses (Cracks, Spalls, LeakingJoints) of
  DefectCondition. Without this path, rdflib's SPARQL engine returns
  zero rows even when instances are present.
"""

from pathlib import Path

QUERIES_DIR = Path(__file__).parent.parent / "queries"


PREFIX_BLOCK = """
PREFIX tun:  <http://w3id.org/tunnel-dt/ontology/v1.2#>
PREFIX cobie: <http://w3id.org/tunnel-dt/cobie#>
PREFIX rads: <http://w3id.org/tunnel-dt/rads#>
PREFIX std:  <http://w3id.org/tunnel-dt/governance#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
"""


def query_all_defects_by_ring(ring_id: int) -> str:
    """List defects at a specific ring, traversing the subclass hierarchy."""
    return PREFIX_BLOCK + f"""
    SELECT DISTINCT ?defect ?type ?severity ?priority
    WHERE {{
        ?defect rdf:type/rdfs:subClassOf* tun:DefectCondition ;
                tun:atRingID {ring_id} .
        OPTIONAL {{ ?defect tun:hasType ?type . }}
        OPTIONAL {{ ?defect tun:hasSeverity ?severity . }}
        OPTIONAL {{ ?defect tun:hasPriority ?priority . }}
    }}
    ORDER BY DESC(?priority)
    """


def query_all_defects() -> str:
    """List every defect, regardless of ring. Useful as a sanity check.

    The two FILTER NOT EXISTS clauses exclude TBox class nodes, which
    otherwise match the property path once the OWL 2 RL closure makes
    rdfs:subClassOf reflexive (same fix as Rev 11b in the loader).
    """
    return PREFIX_BLOCK + """
    SELECT DISTINCT ?defect ?type ?ring ?priority
    WHERE {
        ?defect rdf:type/rdfs:subClassOf* tun:DefectCondition .
        FILTER NOT EXISTS { ?defect rdf:type owl:Class . }
        FILTER NOT EXISTS { ?defect rdf:type rdfs:Class . }
        OPTIONAL { ?defect tun:hasType ?type . }
        OPTIONAL { ?defect tun:atRingID ?ring . }
        OPTIONAL { ?defect tun:hasPriority ?priority . }
    }
    ORDER BY ?ring
    """


def query_completeness_score(defect_id: str) -> str:
    return PREFIX_BLOCK + f"""
    SELECT ?completenessScore
    WHERE {{
        tun:{defect_id} tun:completenessScore ?completenessScore .
    }}
    """


def query_high_priority_defects() -> str:
    return PREFIX_BLOCK + """
    SELECT DISTINCT ?defect ?ring ?chainage ?type ?priority ?cost
    WHERE {
        ?defect rdf:type/rdfs:subClassOf* tun:DefectCondition ;
                tun:hasPriority "HIGH" .
        OPTIONAL { ?defect tun:atRingID ?ring . }
        OPTIONAL { ?defect tun:atChainage ?chainage . }
        OPTIONAL { ?defect tun:hasType ?type . }
        OPTIONAL { ?defect tun:estimatedCost ?cost . }
        BIND("HIGH" AS ?priority)
    }
    ORDER BY ?chainage
    """


def query_fmea_chain_for_defect(defect_id: str) -> str:
    return PREFIX_BLOCK + f"""
    SELECT ?component ?mechanism ?indicator ?indValue ?modality
           ?cause ?threshold ?thresholdStatus ?intervention ?sourceRef
    WHERE {{
        OPTIONAL {{ tun:{defect_id} tun:locatedAt ?component . }}
        OPTIONAL {{ tun:{defect_id} tun:hasMechanism ?mechanism . }}
        OPTIONAL {{
            tun:{defect_id} tun:hasIndicator ?indicator .
            ?indicator tun:hasValue ?indValue ;
                       tun:isDetectedWith ?modality .
        }}
        OPTIONAL {{ tun:{defect_id} tun:hasCause ?cause . }}
        OPTIONAL {{
            tun:{defect_id} tun:hasThreshold ?threshold .
            OPTIONAL {{ ?threshold tun:status ?thresholdStatus . }}
            OPTIONAL {{ ?threshold tun:sourceReference ?sourceRef . }}
            OPTIONAL {{ ?threshold tun:prescribesIntervention ?intervention . }}
        }}
    }}
    ORDER BY ?indicator ?threshold ?intervention
    """


def query_clause_traceability_for_defect(defect_id: str) -> str:
    """CQ-25/CQ-26: follow a decision to its dated governing clause."""
    return PREFIX_BLOCK + f"""
    SELECT DISTINCT ?defect ?threshold ?intervention ?clause
                    ?clauseRef ?edition ?editionName ?textHash
    WHERE {{
        BIND(tun:{defect_id} AS ?defect)
        ?defect tun:sourceReference ?clause ;
                tun:hasThreshold ?threshold .
        ?threshold tun:derivedFrom ?clause ;
                   tun:prescribesIntervention ?intervention .
        ?clause std:clauseRef ?clauseRef ;
                std:inEdition ?edition ;
                std:textHash ?textHash .
        ?edition std:edition ?editionName .
    }}
    ORDER BY ?threshold ?intervention
    """


def query_modality_coverage_stats() -> str:
    return PREFIX_BLOCK + """
    SELECT ?modality (COUNT(DISTINCT ?defect) AS ?defectCount)
    WHERE {
        ?defect rdf:type/rdfs:subClassOf* tun:DefectCondition ;
                tun:isDetectedWith ?modality .
    }
    GROUP BY ?modality
    ORDER BY DESC(?defectCount)
    """


def query_defects_missing_cause_level() -> str:
    """Find defects with incomplete FMEA — missing cause-level evidence.

    Class nodes are excluded for the same Rev 11b reason as in
    query_all_defects — they have no hasCause, so without the
    filters every TBox class would appear as a 'defect missing cause'.
    """
    return PREFIX_BLOCK + """
    SELECT DISTINCT ?defect ?ring ?type
    WHERE {
        ?defect rdf:type/rdfs:subClassOf* tun:DefectCondition .
        FILTER NOT EXISTS { ?defect rdf:type owl:Class . }
        FILTER NOT EXISTS { ?defect rdf:type rdfs:Class . }
        OPTIONAL { ?defect tun:atRingID ?ring . }
        OPTIONAL { ?defect tun:hasType ?type . }
        FILTER NOT EXISTS {
            ?defect tun:hasCause ?c .
        }
    }
    """


def query_interventions_per_standard() -> str:
    """Count prescribed interventions grouped by standard reference."""
    return PREFIX_BLOCK + """
    SELECT ?standard (COUNT(?intervention) AS ?count)
    WHERE {
        ?intervention rdf:type tun:Intervention ;
                      tun:sourceReference ?standard .
    }
    GROUP BY ?standard
    ORDER BY DESC(?count)
    """


def load_competency_questions() -> dict:
    """The 31 competency questions in queries/competency/, keyed by
    "CQ-xx  question", with each file's default parameters substituted."""
    out = {}
    for path in sorted((QUERIES_DIR / "competency").glob("CQ-*.rq")):
        text = path.read_text(encoding="utf-8")
        question = text.splitlines()[0].lstrip("# ")
        for line in text.splitlines():
            if line.startswith("# Defaults:"):
                for pair in line.split(":", 1)[1].split(","):
                    key, value = pair.strip().split("=", 1)
                    text = text.replace("{" + key + "}", value)
        out[question] = text
    return out


def load_query_from_file(filename: str) -> str:
    """Load a .rq query file from the queries/ directory."""
    path = QUERIES_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


# -----------------------------------------------------------------------------
# Example queries for the SPARQL console dropdown
# -----------------------------------------------------------------------------
EXAMPLE_QUERIES = {
    "All defects (subclass-aware)": query_all_defects(),
    "All defects at Ring 1247": query_all_defects_by_ring(1247),
    "High priority defects": query_high_priority_defects(),
    "FMEA chain for D-1247-L": query_fmea_chain_for_defect("D-1247-L"),
    "Clause traceability for D-1158-S":
        query_clause_traceability_for_defect("D-1158-S"),
    "Modality coverage stats": query_modality_coverage_stats(),
    "Defects missing cause-level evidence": query_defects_missing_cause_level(),
    "Interventions per standard": query_interventions_per_standard(),
}
