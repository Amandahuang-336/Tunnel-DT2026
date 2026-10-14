"""
Public-demo hardening
=====================

One switch that makes the app safe to expose to untrusted visitors, while
leaving a trusted local / operator deployment completely unchanged.

Enable it with an environment variable::

    TUNNEL_DT_PUBLIC_DEMO=true

or with ``public_demo = true`` in ``.streamlit/secrets.toml``.

When enabled:

* **Session-scoped tunnels** — tunnels registered on the Tunnel Setup page
  are held in the visitor's own session instead of being written to the
  shared ``data/custom_tunnels.json``, so one visitor cannot see, overwrite
  or delete another's work.
* **Pinned model endpoint** — the local-model (Ollama) endpoint is fixed to
  localhost, so a visitor cannot aim the server at an arbitrary URL
  (server-side request forgery).
* **Rate-limited expensive actions** — report/slide-deck compilation and
  other subprocess work are capped per session.
* **No stack traces** — errors show a short message instead of internals.

Everything here is inert unless the flag is set: default behaviour for local
and Docker runs is exactly as before.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Tuple

import streamlit as st

# Endpoint the local-model routes are pinned to when the demo flag is on.
PINNED_OLLAMA_ENDPOINT = "http://localhost:11434"

# Session-state keys owned by this module.
_TUNNELS_KEY = "_demo_session_tunnels"
_RATE_KEY = "_demo_rate_limits"


def is_public_demo() -> bool:
    """True when the app is running as a hardened public demo."""
    env = os.getenv("TUNNEL_DT_PUBLIC_DEMO", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    # Fall back to Streamlit secrets (absent secrets.toml raises; treat as off).
    try:
        return bool(st.secrets.get("public_demo", False))
    except Exception:  # noqa: BLE001
        return False


def persist_tunnels() -> bool:
    """
    Whether user-created tunnels are written to the shared
    ``data/custom_tunnels.json``.

    **Default is False** — every session keeps its own tunnels, so one
    person's test asset never appears for the next visitor (or in the next
    run). Set ``TUNNEL_DT_PERSIST_TUNNELS=true`` for a single-operator
    deployment that wants its registered assets to survive a restart.
    Public-demo mode always wins: it never persists.
    """
    if is_public_demo():
        return False
    env = os.getenv("TUNNEL_DT_PERSIST_TUNNELS", "").strip().lower()
    return env in ("1", "true", "yes", "on")


def notice() -> str:
    """One-line banner text describing the demo restrictions."""
    return (
        "**Public demo.** Tunnels you register are kept in your own session "
        "and are not shared with, or visible to, other visitors. Local-model "
        "inference and some heavy exports are limited on this deployment."
    )


# -----------------------------------------------------------------------------
# Session-scoped custom tunnels (replaces the shared JSON file in demo mode)
# -----------------------------------------------------------------------------
def get_session_tunnels() -> List[Dict[str, Any]]:
    """The visitor's own custom tunnels. Empty list outside a session."""
    try:
        return list(st.session_state.get(_TUNNELS_KEY, []))
    except Exception:  # noqa: BLE001 — no script run context (e.g. tests)
        return []


def set_session_tunnels(tunnels: List[Dict[str, Any]]) -> None:
    """Replace the visitor's own custom tunnels."""
    try:
        st.session_state[_TUNNELS_KEY] = list(tunnels)
    except Exception:  # noqa: BLE001
        pass


# -----------------------------------------------------------------------------
# Rate limiting for expensive, subprocess-backed actions
# -----------------------------------------------------------------------------
def rate_limit(action: str, max_calls: int = 3,
               window_s: int = 300) -> Tuple[bool, int]:
    """
    Sliding-window limiter, per session.

    Returns ``(allowed, retry_after_s)``. Always allows when the demo flag
    is off, so local use is never throttled.
    """
    if not is_public_demo():
        return True, 0
    try:
        buckets: Dict[str, List[float]] = st.session_state.setdefault(
            _RATE_KEY, {})
    except Exception:  # noqa: BLE001
        return True, 0

    now = time.time()
    hits = [t for t in buckets.get(action, []) if now - t < window_s]
    if len(hits) >= max_calls:
        retry = int(window_s - (now - hits[0])) + 1
        buckets[action] = hits
        return False, max(retry, 1)

    hits.append(now)
    buckets[action] = hits
    return True, 0


def show_error(exc: Exception, context: str = "") -> None:
    """
    Render an error. Full traceback for trusted deployments; a short,
    non-revealing message in public-demo mode.
    """
    if is_public_demo():
        st.error(
            (f"{context} " if context else "")
            + "Something went wrong handling that request. Please try again, "
              "or report the issue if it persists."
        )
    else:
        if context:
            st.error(context)
        st.exception(exc)
