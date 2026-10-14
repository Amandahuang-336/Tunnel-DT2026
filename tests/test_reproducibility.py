"""Reproducibility checks for the results reported in the paper.

Run with:  python -m pytest
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_owl_rl_closure_materialised():
    """The OWL 2 RL reasoner runs at load time (Section 5.2)."""
    assert _load("verify_owlrl").main() == 0


def test_fmea_abox_population():
    """Case and reference FMEA chains are fully populated (Sections 3.3, 5.1)."""
    assert _load("verify_abox").main() == 0


def test_all_competency_questions_answer():
    """All 31 competency questions of Appendix E return results."""
    assert _load("run_competency_questions").main([]) == 0


@pytest.mark.parametrize("cq", [f"CQ-{n:02d}" for n in range(1, 32)])
def test_competency_question_files_exist(cq):
    assert (SCRIPTS.parent / "queries" / "competency" / f"{cq}.rq").exists()
