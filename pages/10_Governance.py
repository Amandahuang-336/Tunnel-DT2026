"""
Knowledge-base governance — page 10
===================================

Temporal portability: what happens to the knowledge base when the standards
it was built from are revised.

Implements the six mechanisms of the manuscript's governance section:

    (a) Edition-bound, time-boxed thresholds
    (b) Versioning on every axis, asserted in the graph (PROV-O)
    (c) Decision manifest — freeze the configuration behind each prescription
    (d) Impact analysis — which open defects a revision moves
    (e) Regression corpus — pin prescription behaviour across KB changes
    (f) Deprecation and migration policy

Nothing on this page mutates the graph. A revision is modelled as *adding* an
edition, so the state of the knowledge base on any past date stays recoverable.
"""

import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.ontology_loader import load_ontology, load_defects
from utils.styling import apply_custom_css
from utils.explainers import render_plain_guide
from utils import governance as gov

apply_custom_css()

if "graph" not in st.session_state:
    st.session_state.graph = load_ontology()

graph = st.session_state.graph
defects = load_defects(graph)

st.title("Knowledge-base governance")
st.caption(
    "Engineering codes are revised. This page shows how the knowledge base "
    "survives that: every decision threshold is bound to a dated clause of an "
    "identified standard edition, so a revision adds knowledge rather than "
    "overwriting it, and any past prescription remains reconstructible."
)

render_plain_guide(
    "Standards change every few years. Without this, updating a threshold "
    "would silently rewrite the reason a repair was ordered years ago. Here "
    "each rule carries the edition and clause it came from, and its dates."
)

editions = gov.list_editions(graph)
thresholds = gov.list_thresholds(graph)
unbound = gov.unbound_clause_references(graph, defects)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Standard editions", len(editions))
c2.metric("Bound thresholds", len(thresholds))
c3.metric("Open defects", sum(1 for d in defects if str(d.get("status", "Active")).lower() in ("active", "open")))
c4.metric("Unbound citations", len(unbound),
          help="Defect records whose clause reference resolves to no dated edition.")

tabs = st.tabs([
    "Editions & thresholds",
    "Impact analysis",
    "Decision manifest",
    "Regression corpus",
    "Provenance & versions",
])

# =============================================================================
# (a) Editions and time-boxed thresholds
# =============================================================================
with tabs[0]:
    st.subheader("Editions in the knowledge base")
    if not editions:
        st.warning(
            "No standard editions are loaded. Check that "
            "`ontology/standards_governance.ttl` is present."
        )
    else:
        st.dataframe(
            pd.DataFrame([{
                "Edition": e.short,
                "Publisher": e.publisher or "—",
                "Title": e.title or "—",
                "Effective from": e.effective_from or "not stated",
                "Superseded by": gov.local_name(e.superseded_by) if e.superseded_by else "—",
            } for e in editions]),
            use_container_width=True, hide_index=True,
        )

    st.subheader("Thresholds, and the clause each is bound to")
    if thresholds:
        st.dataframe(
            pd.DataFrame([{
                "Threshold": t.label,
                "Applies to": gov.local_name(t.defect_class) if t.defect_class else "—",
                "Criterion": t.criterion(),
                "Tier": t.tier or "—",
                "Clause": t.clause_ref or "—",
                "Edition": gov.local_name(t.edition_iri) if t.edition_iri else "—",
                "Valid from": t.valid_from or "—",
                "Valid to": t.valid_to or "open",
            } for t in thresholds]),
            use_container_width=True, hide_index=True,
        )
        st.caption(
            "`Valid to` is open where no successor edition is published. A "
            "revision closes the interval on the superseded threshold and adds "
            "a new individual; it never edits this row."
        )

    st.divider()
    st.subheader("Reconstruct the criteria in force on a past date")
    st.caption(
        "This is the reconstruction primitive. Asking for a past date returns "
        "the criteria that actually justified a prescription issued then, even "
        "after a later edition has been loaded."
    )
    rc1, rc2 = st.columns([1, 2])
    with rc1:
        as_of = st.date_input("As at", value=date.today())
        classes = sorted({str(d.get("defect_type", "")) for d in defects if d.get("defect_type")})
        chosen = st.selectbox("Defect class", classes) if classes else None
    with rc2:
        if chosen:
            in_force = gov.resolve_thresholds(graph, chosen, as_of)
            if in_force:
                for t in in_force:
                    st.success(
                        f"**{t.criterion()}** → `{t.tier}`  \n"
                        f"{t.clause_ref} · {gov.local_name(t.edition_iri)} · "
                        f"valid from {t.valid_from or '—'}"
                    )
            else:
                st.info(
                    f"No threshold for **{chosen}** was in force on "
                    f"{as_of.isoformat()}. Either the edition post-dates it, or "
                    f"no threshold is bound for this class."
                )

    if unbound:
        st.divider()
        st.subheader("Unbound clause citations")
        st.warning(
            f"{len(unbound)} defect record(s) cite a clause that resolves to no "
            "dated edition. These cannot be reconstructed after a revision — "
            "binding them is the concrete work item this layer creates."
        )
        st.dataframe(pd.DataFrame(unbound), use_container_width=True, hide_index=True)

# =============================================================================
# (d) Impact analysis
# =============================================================================
with tabs[1]:
    st.subheader("Which open defects would a revision move?")
    st.caption(
        "Projects a candidate edition onto the live defect population and "
        "returns the records whose activated tier changes. This is the output "
        "manual revision review does not produce, because no manual process "
        "holds the open-defect population and the threshold set in one "
        "queryable structure."
    )

    if len(editions) < 2:
        st.info(
            "**Only one edition is loaded, so there is nothing to compare.**\n\n"
            "This is the honest state of the demonstration knowledge base: no "
            "source standard was revised within the study period, so the "
            "mechanism is specified and executable but has not been run against "
            "a real revision.\n\n"
            "To exercise it, drop a second edition file into "
            "`ontology/editions/` — a Turtle file declaring a new "
            "`std:StandardEdition`, its clauses, and its thresholds — and "
            "reload. Nothing already in the graph is modified."
        )
        with st.expander("Template for a new edition file"):
            st.code(
                "@prefix tun: <http://w3id.org/tunnel-dt/ontology/v1.2#> .\n"
                "@prefix std: <http://w3id.org/tunnel-dt/governance#> .\n"
                "@prefix ed:  <http://w3id.org/tunnel-dt/governance/edition#> .\n"
                "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n"
                "ed:MyEdition a std:StandardEdition ;\n"
                '    std:publisher "..." ; std:edition "..." ;\n'
                '    rdfs:label "..." .\n\n'
                "std:Clause_X_MyEdition a std:Clause ;\n"
                "    std:inEdition ed:MyEdition ;\n"
                '    std:clauseRef "..." .\n\n'
                "std:Thr_X_MyEdition a std:Threshold ;\n"
                "    std:appliesToClass tun:Spalls ;\n"
                '    std:onIndicator "rebar_section_loss_pct" ;\n'
                '    std:operator ">" ; std:value 20 ; std:unit \"%\" ;\n'
                '    std:tier "Action_Required" ;\n'
                "    std:derivedFrom std:Clause_X_MyEdition ;\n"
                '    std:validFrom "2027-07-01"^^xsd:date .\n',
                language="turtle",
            )
    else:
        labels = {e.short: e.iri for e in editions}
        ic1, ic2 = st.columns(2)
        now_label = ic1.selectbox("Edition currently adopted", list(labels), index=0)
        next_label = ic2.selectbox("Incoming edition", list(labels),
                                   index=min(1, len(labels) - 1))

        rows = gov.impact_analysis(graph, defects, labels[now_label], labels[next_label])
        total_open = sum(1 for d in defects
                         if str(d.get("status", "Active")).lower() in ("active", "open"))
        summary = gov.impact_summary(rows, total_open)

        m1, m2, m3 = st.columns(3)
        m1.metric("Defects moved", summary["affected"], f"of {summary['total_open']} open")
        m2.metric("Escalating", summary["escalating"])
        m3.metric("To emergency tier", summary["to_emergency"])

        if rows:
            st.dataframe(
                pd.DataFrame([{
                    "Defect": r.defect_id,
                    "Type": r.defect_type,
                    "Chainage (m)": r.chainage_m,
                    "Criterion now": r.criterion_now,
                    "Tier now": r.tier_now,
                    "Criterion next": r.criterion_next,
                    "Tier next": r.tier_next,
                    "Direction": r.direction,
                } for r in rows]),
                use_container_width=True, hide_index=True,
            )

            st.subheader("Migration actions")
            st.caption(
                "Policy: issued prescriptions are frozen at issue and never "
                "retroactively altered; open defects are re-evaluated at the "
                "next scheduled inspection; anything escalating to the "
                "emergency tier is re-evaluated immediately."
            )
            st.dataframe(pd.DataFrame(gov.migration_actions(rows)),
                         use_container_width=True, hide_index=True)

            st.download_button(
                "Download change register (JSON)",
                data=json.dumps({
                    "edition_now": now_label,
                    "edition_next": next_label,
                    "summary": summary,
                    "rows": [r.__dict__ for r in rows],
                    "actions": gov.migration_actions(rows),
                }, indent=2),
                file_name="revision_impact.json",
                mime="application/json",
            )
        else:
            st.success(
                "No open defect changes tier between these two editions. The "
                "revision is adoptable without re-assessment."
            )

# =============================================================================
# (c) Decision manifest
# =============================================================================
with tabs[2]:
    st.subheader("Freeze the configuration behind a prescription")
    st.caption(
        "Re-running against a stored manifest either reproduces the "
        "prescription or returns a diff. That property, not the presence of a "
        "clause citation, is what makes traceability a reconstruction rather "
        "than a reference."
    )

    if not defects:
        st.info("No defects loaded.")
    else:
        ids = [str(d.get("defect_id")) for d in defects]
        chosen_id = st.selectbox("Defect", ids)
        record = next((d for d in defects if str(d.get("defect_id")) == chosen_id), None)

        mc1, mc2 = st.columns(2)
        endorser = mc1.text_input("Endorsing engineer", value="",
                                  placeholder="Leave blank for unendorsed")
        stage = mc2.selectbox(
            "Assurance stage", [1, 2, 3], index=1,
            format_func=lambda s: {1: "1 — Shadow", 2: "2 — Assisted", 3: "3 — Delegated"}[s],
        )

        if record:
            manifest = gov.build_manifest(record, graph,
                                          endorsed_by=endorser or None,
                                          assurance_stage=stage)
            if manifest.output["edition_bound"]:
                st.success(
                    f"Clause **{manifest.output['clause_ref']}** resolves to "
                    f"`{gov.local_name(manifest.output['standard_edition_iri'])}`."
                )
            else:
                st.warning(
                    f"Clause **{manifest.output['clause_ref'] or '(none)'}** is "
                    "not bound to a dated edition. This prescription cannot be "
                    "reconstructed after a revision."
                )
            st.code(manifest.to_json(), language="json")
            st.download_button(
                "Download manifest (JSON)",
                data=manifest.to_json(),
                file_name=f"{manifest.manifest_id}.json",
                mime="application/json",
            )

    st.divider()
    st.subheader("Verify a stored manifest")
    uploaded = st.file_uploader("Manifest JSON", type=["json"], key="manifest_verify")
    if uploaded is not None:
        ok, message = gov.verify_manifest(uploaded.getvalue().decode("utf-8"))
        (st.success if ok else st.error)(message)

# =============================================================================
# (e) Regression corpus
# =============================================================================
with tabs[3]:
    st.subheader("Pin prescription behaviour across knowledge-base changes")
    st.caption(
        "A fixed corpus of cases with adjudicated expected tiers, re-run "
        "whenever the ontology, vocabularies, rules, or extraction engine "
        "change. A changed prescription must be explained and signed off "
        "before release."
    )

    corpus = gov.load_corpus()
    if not corpus:
        st.info(
            "No regression corpus is present. Create "
            "`data/regression_corpus.json` with adjudicated cases — the "
            "schema is in the manuscript's supplementary material "
            "(`regression_corpus.schema.json`). Boundary cases at each "
            "threshold carry the diagnostic load; a corpus of typical cases "
            "rarely detects a regression."
        )
    else:
        outcome = gov.run_regression(graph, corpus)
        r1, r2, r3 = st.columns(3)
        r1.metric("Passed", outcome["passed"], f"of {outcome['total']}")
        r2.metric("Failed", outcome["failed"])
        r3.metric("No threshold", outcome["unresolved"])
        st.dataframe(pd.DataFrame(outcome["results"]),
                     use_container_width=True, hide_index=True)
        if outcome["failed"]:
            st.error(
                "A tier changed against the adjudicated expectation. Under the "
                "assurance policy this reverts the deployment to Stage 2 "
                "(engineer endorsement on every prescription) until explained."
            )

# =============================================================================
# (b) Provenance and versions
# =============================================================================
with tabs[4]:
    st.subheader("The configuration currently in force")
    state = gov.kb_state(graph)
    st.json(state)
    st.caption(
        "Every field is read from the environment rather than asserted. Where a "
        "value is genuinely unknown it is reported as null rather than filled in."
    )

    st.subheader("Extraction provenance (PROV-O)")
    runs = gov.extraction_provenance(graph)
    if runs:
        st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)
        st.caption(
            "Values shown in angle brackets are build-time placeholders, not "
            "recorded data."
        )
    else:
        st.info("No extraction runs asserted in the graph.")
