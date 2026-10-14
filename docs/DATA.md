# Data

## Released

| File | Content | Origin |
| --- | --- | --- |
| `data/fmea_chains_aashto.json` | The six FMEA chains (component → mechanism → defect → indicator → cause → threshold → intervention) extracted from AASHTO DCRT Chapter 16 and accepted after expert review | Section 3.3; Table 15 |
| `ontology/fmea_abox.ttl` | The same chains and the demonstration defect records as asserted OWL individuals; regenerate with `python scripts/export_abox.py` | Section 4 |
| `data/defects_tunnel_a.json` | Seven demonstration defect records with per-modality evidence, thresholds and intervention steps | Synthetic |
| `data/tunnel_geometry.json` | Alignments and portals of the two demonstration tunnels | Synthetic |
| `data/geological_context.json` | Geological zones and stratigraphy along each tunnel | Synthetic |
| `data/bim_as_built.json` | As-built lining attributes per segment | Synthetic |
| `data/cv_detections_sample.json`, `data/cobie_rows_sample.csv` | Example computer-vision output and the COBie rows it maps to | Synthetic |
| `data/regression_corpus.json` | Template for the expert-adjudicated regression corpus used by the governance layer; ships empty by design | Section 6.4 |

## Demonstration tunnels

*Tunnel A* and *Tunnel B* are fictitious. Their alignments are generated
curves placed near 0° N 0° E (the "Null Island" placeholder used in GIS), so the
map in the app shows open sea rather than a real site. Their geology is generic
(estuarine soft sediments over basalt over Palaeozoic mudstone), and their BIM
attributes and defect records are synthetic but consistent with published
precast-segmental-lining practice. No record in this repository describes a
real tunnel.

## Withheld

Multimodal sensing data from the case-study tunnel (RGB images, RGBD point
clouds, infrared thermography and GPR radargrams) are subject to operator
confidentiality and are not released. The case-study tunnel is not identified.

The standards from which the FMEA chains were extracted (AASHTO, Austroads,
COBie guide) are copyrighted and are not redistributed.
