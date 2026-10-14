# Competency questions

The ontology was validated against 31 competency questions (CQs) drawn from five
maintenance scenarios (paper, Appendix E, Tables 16–20). Each CQ has one SPARQL
file in [`queries/competency/`](../queries/competency/). The header of each file
names its parameters (for example `{DEFECT_ID}`) and the defaults used against
the bundled demonstration data.

Run them all against the populated graph, which is assembled exactly as the app
assembles it (TBox, governance module, ABox and the OWL 2 RL closure):

```bash
python scripts/run_competency_questions.py           # summary
python scripts/run_competency_questions.py --show    # with result rows
python scripts/run_competency_questions.py CQ-14 --show
```

The same queries appear in the app under **SPARQL Console**, where the
parameters can be edited.

Five CQs (04, 05, 14, 28 and 31) reason over the modality evidence profile of
Section 3.4 (which evidence levels RGB, RGBD, thermal and GPR can populate). The
profile is written into those queries as a `VALUES` table so that it is visible
and editable; it matches `MODALITY_LEVELS` in `utils/fmea_chain.py`.


## Scenario 1: Crack with moisture detected during quarterly inspection

| CQ | Question | Category | Defaults | Rows on demo data |
|---|---|---|---|---|
| [CQ-01](../queries/competency/CQ-01.rq) | What type of defect has been identified at this location? | Defect | `RING_ID=1247` | 1 |
| [CQ-02](../queries/competency/CQ-02.rq) | What are the measured dimensions of this defect? | Defect | `DEFECT_ID=D-1247-L` | 2 |
| [CQ-03](../queries/competency/CQ-03.rq) | Which FMEA chain levels have sensor evidence for this defect? | Multimodal | `DEFECT_ID=D-1247-L` | 3 |
| [CQ-04](../queries/competency/CQ-04.rq) | What is the diagnostic completeness score? | Multimodal | `DEFECT_ID=D-1158-S` | 1 |
| [CQ-05](../queries/competency/CQ-05.rq) | Which additional modalities should be deployed to fill evidence gaps? | Multimodal | `DEFECT_ID=D-0923-C` | 1 |
| [CQ-06](../queries/competency/CQ-06.rq) | What condition state does this defect correspond to? | Defect | `DEFECT_ID=D-1247-L` | 1 |
| [CQ-07](../queries/competency/CQ-07.rq) | What intervention is prescribed for this condition state? | Maintenance | `DEFECT_ID=D-1247-L` | 4 |
| [CQ-08](../queries/competency/CQ-08.rq) | What is the deadline for this intervention? | Maintenance | `DEFECT_ID=D-1247-L` | 1 |
| [CQ-09](../queries/competency/CQ-09.rq) | Is the cause of the crack known, or is it inferred? | Multimodal | `DEFECT_ID=D-0923-C` | 1 |

## Scenario 2: Thermal anomaly triggers investigation of hidden moisture path

| CQ | Question | Category | Defaults | Rows on demo data |
|---|---|---|---|---|
| [CQ-10](../queries/competency/CQ-10.rq) | Is there a previously documented defect at this location? | Defect | `RING_ID=1247` | 1 |
| [CQ-11](../queries/competency/CQ-11.rq) | Does the thermal observation provide cause-level evidence for the existing defect? | Multimodal | `DEFECT_ID=D-1247-L` | 1 |
| [CQ-12](../queries/competency/CQ-12.rq) | What potential cause does the thermal anomaly indicate? | Defect | `DEFECT_ID=D-1247-L` | 1 |
| [CQ-13](../queries/competency/CQ-13.rq) | Does the GPR observation provide structure-level evidence? | Multimodal | `DEFECT_ID=D-1247-L` | 1 |
| [CQ-14](../queries/competency/CQ-14.rq) | Has the diagnostic completeness score changed after adding thermal and GPR? | Multimodal | `DEFECT_ID=D-1247-L` | 2 |
| [CQ-15](../queries/competency/CQ-15.rq) | Does the new evidence change the prescribed intervention or its urgency? | Maintenance | `DEFECT_ID=D-1247-L` | 1 |
| [CQ-16](../queries/competency/CQ-16.rq) | Is the rebar cover below the minimum specified in referred Standards for this exposure class? | Compliance | `DEFECT_ID=D-1158-S` | 1 |
| [CQ-17](../queries/competency/CQ-17.rq) | Does the void require a separate intervention (e.g. grout injection)? | Maintenance | `DEFECT_ID=D-1247-L` | 3 |

## Scenario 3: Prioritisation across multiple defects in a tunnel section

| CQ | Question | Category | Defaults | Rows on demo data |
|---|---|---|---|---|
| [CQ-18](../queries/competency/CQ-18.rq) | What are all active defects in a given tunnel section? | Asset | `CH_FROM=600, CH_TO=1000` | 5 |
| [CQ-19](../queries/competency/CQ-19.rq) | What is the condition state and diagnostic completeness for each? | Defect | `CH_FROM=600, CH_TO=1000` | 5 |
| [CQ-20](../queries/competency/CQ-20.rq) | Which defects exceed the serviceability threshold? | Compliance | – | 3 |
| [CQ-21](../queries/competency/CQ-21.rq) | What is the estimated cost of each prescribed intervention? | Maintenance | – | 5 |
| [CQ-22](../queries/competency/CQ-22.rq) | Which defects have multiple failure modes co-occurring at the same asset? | Defect | – | 13 |
| [CQ-23](../queries/competency/CQ-23.rq) | Rank defects by priority considering condition state, completeness, and co-occurrence. | Maintenance | – | 7 |

## Scenario 4: Compliance audit and traceability

| CQ | Question | Category | Defaults | Rows on demo data |
|---|---|---|---|---|
| [CQ-24](../queries/competency/CQ-24.rq) | What sensor data was used to identify this defect? | Multimodal | `DEFECT_ID=D-1247-L` | 4 |
| [CQ-25](../queries/competency/CQ-25.rq) | Which standard clause defines the severity threshold applied? | Compliance | `DEFECT_ID=D-1158-S` | 1 |
| [CQ-26](../queries/competency/CQ-26.rq) | Which standard clause prescribes the selected intervention? | Compliance | `DEFECT_ID=D-1158-S` | 1 |
| [CQ-27](../queries/competency/CQ-27.rq) | What was the diagnostic completeness at the time of decision? | Multimodal | `DEFECT_ID=D-1158-S` | 1 |
| [CQ-28](../queries/competency/CQ-28.rq) | Were there FMEA chain levels with no evidence? If so, was a targeted survey recommended? | Multimodal | `DEFECT_ID=D-0923-C` | 2 |

## Scenario 5: Modality limitation awareness

| CQ | Question | Category | Defaults | Rows on demo data |
|---|---|---|---|---|
| [CQ-29](../queries/competency/CQ-29.rq) | Which modalities can detect delamination? | Multimodal | – | 2 |
| [CQ-30](../queries/competency/CQ-30.rq) | Which modalities cannot detect delamination, and why? | Multimodal | – | 2 |
| [CQ-31](../queries/competency/CQ-31.rq) | For a given defect type, what is the minimum set of modalities needed for a completeness score >= 3/4? | Multimodal | `DEFECT_TYPE=Spalls` | 9 |
