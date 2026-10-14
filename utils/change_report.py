"""
Inter-cycle change detection
============================

Implements the manuscript's inter-cycle change report: every defect in the
current inspection cycle is classified into exactly one of five states by
comparing its activated chain against the chain activated at its predecessor.

    New                 no predecessor satisfies the identity predicate
    Escalated           urgency tier increased, or operative scope grew
    Stable              same tier, scope change within measurement uncertainty
    Repaired, holding   predecessor carried a completed job; nothing detected now
    Repaired, recurred  predecessor carried a completed job; compatible class again

WHY THIS MATTERS
----------------
A single-cycle assessment yields a state. The change report yields a *rate* —
defect initiation, deterioration, and repair durability — which is what the
re-intervention acceptance criterion is computed from.

IDENTITY RESOLUTION AND ITS PARAMETER
-------------------------------------
Classification depends on binding an observation in cycle t+1 to the defect
instance first recorded in cycle t. The manuscript states this predicate as

    same(o1,o2) <=> same component
                    AND ||x1 - x2|| <= tau
                    AND class-compatible

`tau` is an operator-supplied configuration parameter. **No default is provided
here.** Deriving it requires a registration-accuracy study relating each
modality's positional uncertainty to the survey control available on the asset,
and no such study exists for the demonstration data. `classify_cycle` therefore
requires `tolerance_m` explicitly and raises if it is not supplied — an
unreliable association is worse than a refused one.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Defect classes that may legitimately be the SAME PHYSICAL FEATURE observed
# differently, or that feature having progressed. Symmetric; a class is always
# compatible with itself.
#
# The test is feature identity, NOT a shared cause. Two classes that one
# mechanism can produce are still two defects when they occupy different
# materials or elements: corrosion at a ceiling-hanger anchorage produces both
# a spall in the concrete and a hanger losing tension, and those are two
# records to link, not one record to merge. Pairs that are merely causally
# coupled belong in the adjudication queue, which is where an unlisted pair
# lands by default.
COMPATIBLE_CLASSES: List[frozenset] = [
    # Surface spall and the subsurface delamination of the same damaged volume.
    frozenset({"spalls", "delaminations"}),
    # A leaking joint and the staining it deposits on the same joint face.
    frozenset({"leakingjoints", "staining"}),
]

TIER_ORDER = [
    "Acceptable",
    "Monitor_Closely",
    "Investigation_Required",
    "Action_Required",
    "Emergency",
]

# Mapping from the demonstration data's `priority` field onto tier rank, used
# only when an explicit tier is absent from the record.
PRIORITY_TO_TIER = {
    "low": "Monitor_Closely",
    "medium": "Investigation_Required",
    "high": "Action_Required",
    "critical": "Emergency",
}

STATE_NEW = "New"
STATE_ESCALATED = "Escalated"
STATE_STABLE = "Stable"
STATE_HOLDING = "Repaired, holding"
STATE_RECURRED = "Repaired, recurred"

STATE_MEANING = {
    STATE_NEW: "Defect initiation rate; drives inspection-interval review.",
    STATE_ESCALATED: "Deterioration rate; primary input to forward budget estimation.",
    STATE_STABLE: "Supports extending the re-inspection interval for that component.",
    STATE_HOLDING: "Repair durability evidence; numerator of the re-intervention criterion.",
    STATE_RECURRED: "Re-intervention event; triggers review of the prescribed intervention.",
}


class ToleranceNotConfigured(ValueError):
    """Raised when identity resolution is attempted without a tolerance."""


def _norm(text: Any) -> str:
    return str(text or "").strip().lower().replace(" ", "").replace("_", "")


def _tier_of(record: Dict[str, Any]) -> Optional[str]:
    tier = record.get("tier") or record.get("urgency_tier")
    if tier:
        return str(tier)
    return PRIORITY_TO_TIER.get(str(record.get("priority", "")).strip().lower())


def _tier_rank(tier: Optional[str]) -> int:
    try:
        return TIER_ORDER.index(tier) if tier else -1
    except ValueError:
        return -1


def classes_compatible(a: Any, b: Any) -> bool:
    """gamma(o1) ~ gamma(o2) — TBox-asserted compatibility, symmetric."""
    ka, kb = _norm(a), _norm(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    return any({ka, kb} <= pair for pair in COMPATIBLE_CLASSES)


def _same_component(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """kappa(o1) = kappa(o2). Ring identity where present, else component id."""
    for key in ("component_id", "ring_id"):
        va, vb = a.get(key), b.get(key)
        if va is not None and vb is not None:
            return str(va) == str(vb)
    return False


def _separation_m(a: Dict[str, Any], b: Dict[str, Any]) -> Optional[float]:
    """
    ||x1 - x2||. The demonstration records carry chainage only, so separation
    is one-dimensional. Returns None when either record lacks a position, in
    which case the pair cannot be associated.
    """
    ca, cb = a.get("chainage_m"), b.get("chainage_m")
    if ca is None or cb is None:
        return None
    try:
        return abs(float(ca) - float(cb))
    except (TypeError, ValueError):
        return None


def same_defect(
    current: Dict[str, Any],
    previous: Dict[str, Any],
    tolerance_m: float,
) -> Tuple[bool, Optional[float]]:
    """
    Evaluate the identity predicate. Returns (matched, separation_m).

    Conservative by construction: a missing position or an incompatible class
    is a non-match, never a guess.
    """
    if not _same_component(current, previous):
        return False, None
    if not classes_compatible(current.get("defect_type"), previous.get("defect_type")):
        return False, None
    separation = _separation_m(current, previous)
    if separation is None:
        return False, None
    return separation <= tolerance_m, separation


@dataclass
class ChangeRow:
    defect_id: str
    defect_type: str
    chainage_m: Optional[float]
    state: str
    tier_previous: Optional[str]
    tier_current: Optional[str]
    predecessor_id: Optional[str]
    separation_m: Optional[float]
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Ambiguity:
    defect_id: str
    candidates: List[str]
    note: str


def classify_cycle(
    current: Sequence[Dict[str, Any]],
    previous: Sequence[Dict[str, Any]],
    tolerance_m: Optional[float] = None,
    scope_uncertainty_pct: float = 0.0,
) -> Tuple[List[ChangeRow], List[Ambiguity]]:
    """
    Classify every defect in `current` against `previous`.

    Parameters
    ----------
    tolerance_m
        Association tolerance. **Required** — see the module docstring. Passing
        None raises ToleranceNotConfigured rather than assuming a value.
    scope_uncertainty_pct
        Band within which a change in reported extent counts as no change.
        Defaults to 0, i.e. any change in extent is treated as a change; set it
        from the campaign's measurement uncertainty where that is known.

    Returns
    -------
    (rows, ambiguities)
        Ambiguous matches — more than one candidate predecessor within
        tolerance — are NOT resolved. They are returned for adjudication, as
        the framework's conflict policy requires.
    """
    if tolerance_m is None:
        raise ToleranceNotConfigured(
            "Association tolerance is not configured. Identity resolution "
            "requires an operator-supplied tolerance derived from a "
            "registration-accuracy study on the asset; no default is assumed."
        )

    rows: List[ChangeRow] = []
    ambiguities: List[Ambiguity] = []
    matched_previous: set = set()

    for cur in current:
        candidates = []
        for prev in previous:
            ok, sep = same_defect(cur, prev, tolerance_m)
            if ok:
                candidates.append((prev, sep))

        if len(candidates) > 1:
            ambiguities.append(Ambiguity(
                defect_id=str(cur.get("defect_id", "?")),
                candidates=[str(p.get("defect_id", "?")) for p, _ in candidates],
                note=("More than one predecessor within tolerance. Not merged; "
                      "route to adjudication and defer to Investigation_Required."),
            ))
            continue

        if not candidates:
            rows.append(ChangeRow(
                defect_id=str(cur.get("defect_id", "?")),
                defect_type=str(cur.get("defect_type", "?")),
                chainage_m=cur.get("chainage_m"),
                state=STATE_NEW,
                tier_previous=None,
                tier_current=_tier_of(cur),
                predecessor_id=None,
                separation_m=None,
                note="No predecessor satisfies the identity predicate.",
            ))
            continue

        prev, separation = candidates[0]
        matched_previous.add(str(prev.get("defect_id", "?")))

        prev_repaired = str(prev.get("status", "")).strip().lower() in ("repaired", "closed", "complete", "completed")
        tier_prev, tier_cur = _tier_of(prev), _tier_of(cur)

        if prev_repaired:
            state = STATE_RECURRED
            note = "Predecessor carried a completed job; a compatible defect class is detected again at this anchor."
        else:
            escalated = _tier_rank(tier_cur) > _tier_rank(tier_prev)
            grew = _scope_grew(cur, prev, scope_uncertainty_pct)
            if escalated or grew:
                state = STATE_ESCALATED
                note = ("Urgency tier increased." if escalated
                        else "Operative scope increased beyond measurement uncertainty.")
            else:
                state = STATE_STABLE
                note = "Same tier; scope change within measurement uncertainty."

        rows.append(ChangeRow(
            defect_id=str(cur.get("defect_id", "?")),
            defect_type=str(cur.get("defect_type", "?")),
            chainage_m=cur.get("chainage_m"),
            state=state,
            tier_previous=tier_prev,
            tier_current=tier_cur,
            predecessor_id=str(prev.get("defect_id", "?")),
            separation_m=separation,
            note=note,
        ))

    # Previous-cycle defects that were repaired and are no longer detected.
    for prev in previous:
        pid = str(prev.get("defect_id", "?"))
        if pid in matched_previous:
            continue
        if str(prev.get("status", "")).strip().lower() in ("repaired", "closed", "complete", "completed"):
            rows.append(ChangeRow(
                defect_id=pid,
                defect_type=str(prev.get("defect_type", "?")),
                chainage_m=prev.get("chainage_m"),
                state=STATE_HOLDING,
                tier_previous=_tier_of(prev),
                tier_current=None,
                predecessor_id=pid,
                separation_m=None,
                note="Predecessor carried a completed job; no defect now detected at that anchor.",
            ))

    return rows, ambiguities


def _scope_grew(cur: Dict[str, Any], prev: Dict[str, Any], band_pct: float) -> bool:
    """True if reported extent grew by more than the stated uncertainty band."""
    a, b = cur.get("extent_cm2"), prev.get("extent_cm2")
    if a is None or b is None:
        return False
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    if b <= 0:
        return False
    return ((a - b) / b) * 100.0 > band_pct


def summarise(rows: Sequence[ChangeRow]) -> Dict[str, int]:
    """Counts per state, in the manuscript's table order."""
    order = [STATE_NEW, STATE_ESCALATED, STATE_STABLE, STATE_HOLDING, STATE_RECURRED]
    return {state: sum(1 for r in rows if r.state == state) for state in order}


def reintervention_rate(rows: Sequence[ChangeRow]) -> Optional[float]:
    """
    Proportion of previously repaired defects that recurred.

    Returns None when no repaired predecessors exist — the honest result for a
    single-cycle dataset, rather than a zero that would read as a good outcome.
    """
    holding = sum(1 for r in rows if r.state == STATE_HOLDING)
    recurred = sum(1 for r in rows if r.state == STATE_RECURRED)
    denominator = holding + recurred
    if denominator == 0:
        return None
    return recurred / denominator
