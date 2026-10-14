# Paper traceability

Where each part of the paper is realised in this repository. Section numbers
follow the published article.

| Paper | Repository |
| --- | --- |
| Eq. (1), seven-level FMEA chain | Object properties `locatedAt`, `hasMechanism`, `hasIndicator`, `hasCause`, `hasThreshold`, `prescribesIntervention` in `ontology/tunnel_maintenance.ttl` |
| §3.3, LLM-assisted extraction; Table 15 | Reviewed output: `data/fmea_chains_aashto.json`; materialised by `utils/abox_materializer.py` |
| §3.4, modality-to-chain mapping; Appendix C, Property 1 | `MODALITY_LEVELS` in `utils/fmea_chain.py`; capability axioms (`isDetectedWith`, `cannotDetect`) in `ontology/tunnel_maintenance.ttl` |
| §3.4, identity resolution, Eq. (2) | `utils/change_report.py` (`same_defect`, `classify_cycle`); `tun:supersedes` in the TBox |
| §4.1, three-ontology architecture | `ontology/tunnel_maintenance.ttl`, `ontology/austroads_rads.ttl`, `ontology/cobie_ontology.ttl` |
| §4.2, AASHTO severity codes with RADS overlay | `ontology/austroads_rads.ttl` |
| §5.1 and §5.3, worked examples | Defect records in `data/defects_tunnel_a.json`; threshold evaluation in `utils/fmea_evaluator.py` |
| §5.2, reference build | `app.py`, `pages/`, `utils/ontology_loader.py` (rdflib graph + `owlrl` OWL 2 RL closure); `Dockerfile` |
| §5.4, serviceability aggregation, Eqs. (3)–(5) | Worked in the paper (Fig. 13); not computed by the reference build |
| §5.2, IFC4 export and lining viewer | `utils/ifc_export.py`, `utils/bim3d.py`, `pages/7_BIM_3D_Viewer.py` |
| §5.2, vision-language ingest (demonstration) | `utils/local_lvm.py`, `utils/cloud_vlm.py`, `pages/0_Ingest.py` |
| §6.4, knowledge-base governance | `ontology/standards_governance.ttl`, `utils/governance.py`, `pages/10_Governance.py` |
| Appendix D, SWRL rule | Evaluated by the Python rule evaluator (`utils/fmea_evaluator.py`); the SWRL text is the migration specification given in the paper |
| Appendix E, 31 competency questions (Tables 16–20) | `queries/competency/CQ-01.rq` … `CQ-31.rq`; [`COMPETENCY_QUESTIONS.md`](COMPETENCY_QUESTIONS.md); `scripts/run_competency_questions.py` |

Verification: `python -m pytest` runs `scripts/verify_owlrl.py`,
`scripts/verify_abox.py` and all 31 competency questions.
