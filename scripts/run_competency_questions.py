"""Run the 31 competency-question SPARQL queries against the populated graph.

Usage:
    python scripts/run_competency_questions.py            # summary table
    python scripts/run_competency_questions.py --show     # also print result rows
    python scripts/run_competency_questions.py CQ-07 CQ-16 --show

Each query in queries/competency/ declares its parameters and default
values in its header ("# Defaults: DEFECT_ID=D-1247-L"); the defaults point
at records in the bundled demonstration data. The graph is assembled
exactly as the app assembles it (TBox + governance module + ABox, with the
OWL 2 RL closure). Exits non-zero if any query fails or returns no rows.
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The loader uses Streamlit caching decorators; stub them for CLI use.
_st = types.ModuleType("streamlit")
_st.warning = lambda *a, **k: None
_st.cache_resource = lambda **k: (lambda f: f)
_st.cache_data = lambda **k: (lambda f: f)
sys.modules.setdefault("streamlit", _st)

from utils.ontology_loader import load_ontology  # noqa: E402

CQ_DIR = ROOT / "queries" / "competency"
_NS = {
    "http://w3id.org/tunnel-dt/ontology/v1.2#": "tun:",
    "http://w3id.org/tunnel-dt/governance#": "std:",
}


def _short(value) -> str:
    if value is None:
        return "-"
    text = str(value)
    for long, short in _NS.items():
        text = text.replace(long, short)
    return text


def load_cq(path: Path) -> tuple[str, str]:
    """Return (question, query text with default parameters substituted)."""
    text = path.read_text(encoding="utf-8")
    question = text.splitlines()[0].lstrip("# ").split("  ", 1)[-1]
    match = re.search(r"^# Defaults:\s*(.+)$", text, re.MULTILINE)
    if match:
        for pair in match.group(1).split(","):
            key, value = pair.strip().split("=", 1)
            text = text.replace("{" + key + "}", value)
    return question, text


def main(argv: list[str]) -> int:
    show = "--show" in argv
    wanted = {a.upper() for a in argv if a.upper().startswith("CQ-")}
    graph = load_ontology()
    failures = 0
    for path in sorted(CQ_DIR.glob("CQ-*.rq")):
        cq_id = path.stem
        if wanted and cq_id not in wanted:
            continue
        question, query = load_cq(path)
        try:
            result = graph.query(query)
            rows = list(result)
            status = "ok" if rows else "NO ROWS"
        except Exception as exc:  # report and continue
            rows, status = [], f"ERROR: {exc}"
        if status != "ok":
            failures += 1
        print(f"{cq_id}  {len(rows):>3} rows  {status:<8} {question}")
        if show and rows:
            print("        " + " | ".join(str(v) for v in result.vars))
            for row in rows:
                print("        " + " | ".join(_short(x) for x in row))
            print()
    print(f"\n{failures} of the selected queries failed or returned no rows.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
