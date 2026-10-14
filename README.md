# Tunnel-DT2026

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23381120.svg)](https://doi.org/10.5281/zenodo.23381120)

Tunnel-DT2026 is the reference build of a serviceability-oriented, prescriptive
digital twin for road-tunnel maintenance. It links an OWL 2 ontology of AASHTO
DCRT, Austroads RADS and COBie to a seven-level FMEA reasoning chain, maps four
inspection modalities (RGB, RGBD, thermal and GPR) to the levels of that chain
they can populate, and turns inspection findings into a prescribed
intervention whose threshold and source clause can be traced and audited.

This repository accompanies the paper

> Huang, M., Rouhani, M. M., Li, Z., Zhu, H., Zhang, Q.-B. (2026).
> *Serviceability-oriented multimodal data integration for prescriptive
> road-tunnel maintenance digital twins.* Tunnelling and Underground Space
> Technology (in press).

and contains the shared data and code supporting it: the ontologies, the
extracted FMEA chains, the SPARQL realisations of all 31 competency questions,
and the Streamlit reference build described in Section 5.2. To cite it, see
[`CITATION.cff`](CITATION.cff); the software is archived on Zenodo,
DOI [10.5281/zenodo.23381120](https://doi.org/10.5281/zenodo.23381120).

The software is a research demonstration. Its outputs are decision support at
the level of intervention category; they do not replace the specifying
maintenance engineer, project-specific assessment or the source standards.

## What is in this repository, and what is not

| Included | Location |
| --- | --- |
| Maintenance ontology (TBox), RADS and COBie alignment modules, standards-governance module | [`ontology/`](ontology/) |
| FMEA ABox: the six reviewed FMEA chains and the demonstration defect records, as asserted triples | [`ontology/fmea_abox.ttl`](ontology/fmea_abox.ttl) |
| Six FMEA chains extracted from AASHTO DCRT Chapter 16, after expert review (Section 3.3) | [`data/fmea_chains_aashto.json`](data/fmea_chains_aashto.json) |
| 31 competency questions as SPARQL (Appendix E) | [`queries/competency/`](queries/competency/), [`docs/COMPETENCY_QUESTIONS.md`](docs/COMPETENCY_QUESTIONS.md) |
| Streamlit reference build (Section 5.2) and container image definition | [`app.py`](app.py), [`pages/`](pages/), [`utils/`](utils/), [`Dockerfile`](Dockerfile) |
| Verification scripts and tests | [`scripts/`](scripts/), [`tests/`](tests/) |
| Synthetic demonstration data for two fictitious tunnels | [`data/`](data/), see [`docs/DATA.md`](docs/DATA.md) |

Not included:

- **Multimodal sensing data from the case-study tunnel** (RGB, RGBD, thermal and
  GPR acquisitions). They are subject to operator confidentiality and cannot be
  released. The case-study tunnel is not identified in this repository.
- **The source standards** (AASHTO, Austroads, COBie guide). They are
  copyrighted; obtain them from the publishers. The app's Standards Library page
  can index your own copies (see [Optional: standards library](#optional-standards-library)).

The two tunnels in the demonstration data, *Tunnel A* and *Tunnel B*, are
fictitious. Their alignments are synthetic and placed near 0° N 0° E, and their
geology, BIM attributes and defect records are generic. See
[`docs/DATA.md`](docs/DATA.md).

## Install and run

The only prerequisite is Python 3.11 or later (3.13 is the tested version). No
commercial software is needed.

```bash
git clone https://github.com/Amandahuang-336/Tunnel-DT2026.git
cd Tunnel-DT2026
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py                               # opens http://localhost:8501
```

**Docker** (any platform; bundles TeX Live so the PDF report compiles in the
container):

```bash
docker compose up --build                          # then open http://localhost:8501
```

The PDF report and slide deck need a TeX engine (TeX Live or MiKTeX) when the
app is run outside Docker. Without one the app offers the `.tex` source instead.

## Reproducing the paper

```bash
pip install pytest
python -m pytest                                   # all checks below
python scripts/verify_owlrl.py                     # OWL 2 RL closure is materialised at load time
python scripts/verify_abox.py                      # FMEA chains and case records are fully populated
python scripts/run_competency_questions.py --show  # answers to the 31 competency questions
python scripts/export_abox.py                      # regenerate ontology/fmea_abox.ttl from data/
```

[`docs/PAPER_TRACEABILITY.md`](docs/PAPER_TRACEABILITY.md) maps each section,
equation and table of the paper to the file that implements it.

## Using the app

The sidebar follows the inspection-to-prescription workflow of Fig. 12:

| Step | Page | Purpose |
| --- | --- | --- |
| – | Overview | The workflow and the ontology stack at a glance |
| 1 | Tunnel Setup | Pick a demonstration tunnel or register your own |
| 2 | 3D Tunnel (BIM) | Parametric precast-segmental lining, defects at their surveyed position, scan-to-BIM overlay, IFC4 export |
| 3 | Ingest a finding | Record a defect manually, or pre-fill the AASHTO-coded fields from a photo or report with a vision-language model for expert confirmation |
| 4 | Defect Register | All defects for the tunnel, on a map and in a table |
| 5 | Defect Detail | The FMEA chain, geological context, prescribed intervention and its source clause; COBie export |
| 6 | Standards Library | The documents behind each threshold (optional, see below) |
| 7 | SPARQL Console | Ready-made queries, including all 31 competency questions, and free SPARQL |
| 8 | CV → COBie Bridge | Map computer-vision detections to COBie rows |
| 9 | Ontology Browser | Classes, properties and individuals |
| 10 | Governance | Edition-bound thresholds, decision manifests and the inter-cycle change report (Section 6.4) |
| – | Report and Presentation | Board-ready PDF report and slide deck |

The optional vision-language ingest step runs either an open-weight model on
your own machine through [Ollama](https://ollama.com) (for example
`ollama pull qwen2.5vl:7b`) or a cloud model with your own API key. Manual entry
needs neither.

### Optional: standards library

To populate the Standards Library page and the report references, put your own
copies of the standards in `library/standards/` (or point the environment
variable `TUNNEL_DT_LIBRARY` at a folder with a `standards/` subfolder). The
folder is git-ignored and the app runs without it.

## Repository layout

```
app.py                  Streamlit entry point and workflow navigation
pages/                  Workflow pages
utils/                  Ontology loading and OWL 2 RL closure, ABox materialisation,
                        FMEA evaluation, governance, BIM/IFC, COBie, GIS, reports
ontology/               tunnel_maintenance.ttl (TBox), austroads_rads.ttl, cobie_ontology.ttl,
                        standards_governance.ttl, fmea_abox.ttl (ABox)
data/                   FMEA chains and synthetic demonstration data
queries/competency/     CQ-01 … CQ-31 SPARQL files
queries/                Further example queries used by the app
scripts/                Verification, ABox export and competency-question runner
tests/                  pytest suite wrapping the scripts
docs/                   Competency questions, paper traceability, data description
```

## Licence

MIT; see [`LICENSE`](LICENSE). The source standards referenced by the ontology
remain the copyright of their publishers and are not distributed here.

## Contact

Corresponding author: Qian-Bing Zhang, qianbing.zhang@monash.edu. Questions about
the code: open an issue on this repository.
