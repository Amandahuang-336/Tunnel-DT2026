"""
Coloured report figures
=======================

Chart and map rendering shared by both report versions:

    A — one-pager      a single dashboard panel plus a prescribed-actions table
    B — comprehensive  the same panel reproduced as its summary section, so the
                       two documents show the same picture and can be read
                       against each other

Everything renders through matplotlib (Agg) to PNG, so no browser, no folium
export, and no network. The palette is shared with the live app via
`gis.PRIORITY_COLOURS`, so a HIGH defect is the same red on the map, in the 3-D
view, in the charts and in the report tables.

All figures degrade rather than raise: a tunnel with no alignment, no defects,
or no costs still produces a panel, with the empty sub-plot carrying a short
explanation instead of an axis full of nothing.
"""

from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.patches import Rectangle

from utils.bim3d import position_to_angle_deg, DEFAULT_DIAMETER_M
from utils.gis import PRIORITY_COLOURS, list_tunnels, _defect_coords
from utils.cost_model import effective_cost

PRIORITY_ORDER = ("HIGH", "MEDIUM", "LOW")

# Neutral furniture colours, kept close to the app's own styling.
INK = "#22223B"
MUTED = "#7A7A8C"
GRID = "#E3E3EC"
TUNNEL_LINE = "#4A4E8F"
PANEL_BG = "#FFFFFF"


def _priority_of(defect: Dict[str, Any]) -> str:
    value = (defect.get("priority") or "LOW").upper()
    return value if value in PRIORITY_ORDER else "LOW"


def _colour_of(defect: Dict[str, Any]) -> str:
    return PRIORITY_COLOURS.get(_priority_of(defect), "#999999")


def _empty(ax, message: str) -> None:
    """Leave a readable note rather than an empty axis."""
    ax.text(0.5, 0.5, message, ha="center", va="center",
            fontsize=8.5, color=MUTED, wrap=True,
            transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _style(ax) -> None:
    ax.set_facecolor(PANEL_BG)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=7.5)


# =============================================================================
# Map — coloured alignment with defect markers
# =============================================================================
def _draw_map(ax, tunnel: Dict[str, Any], defects: Sequence[Dict[str, Any]]) -> None:
    alignment = tunnel.get("alignment") or []
    if len(alignment) < 2:
        _empty(ax, "No alignment geometry for this tunnel.")
        ax.set_title("Alignment", fontsize=9, color=INK, loc="left")
        return

    lats = [float(p[0]) for p in alignment]
    lons = [float(p[1]) for p in alignment]

    ax.plot(lons, lats, color=TUNNEL_LINE, linewidth=3.0,
            solid_capstyle="round", zorder=2, alpha=0.9)
    ax.plot(lons, lats, color="white", linewidth=1.0,
            linestyle=(0, (4, 3)), zorder=3, alpha=0.9)

    # Portals
    ax.scatter([lons[0], lons[-1]], [lats[0], lats[-1]],
               s=55, marker="s", facecolor="white",
               edgecolor=TUNNEL_LINE, linewidths=1.4, zorder=5)
    ax.annotate("portal", (lons[0], lats[0]), textcoords="offset points",
                xytext=(4, 6), fontsize=6.5, color=MUTED)
    ax.annotate("portal", (lons[-1], lats[-1]), textcoords="offset points",
                xytext=(4, 6), fontsize=6.5, color=MUTED)

    tunnels = list_tunnels()
    plotted = 0
    for priority in PRIORITY_ORDER:
        pts = []
        for d in defects:
            if _priority_of(d) != priority:
                continue
            coords = _defect_coords(d, tunnels)
            if coords:
                pts.append(coords)
        if not pts:
            continue
        plotted += len(pts)
        ax.scatter([p[1] for p in pts], [p[0] for p in pts],
                   s=58, color=PRIORITY_COLOURS[priority],
                   edgecolor="white", linewidths=0.9, zorder=6,
                   label=f"{priority} ({len(pts)})")

    if plotted:
        ax.legend(loc="best", fontsize=6.5, framealpha=0.85,
                  labelcolor=INK, handletextpad=0.4, borderpad=0.4)

    ax.set_title("Alignment and defect locations", fontsize=9,
                 color=INK, loc="left")
    ax.set_xlabel("Longitude", fontsize=7, color=MUTED)
    ax.set_ylabel("Latitude", fontsize=7, color=MUTED)
    _style(ax)
    # Keep the corridor from being squashed into a flat line.
    mid_lat = sum(lats) / len(lats)
    ax.set_aspect(1.0 / max(math.cos(math.radians(mid_lat)), 1e-6))


# =============================================================================
# BIM — 3-D lining with defect markers
# =============================================================================
def _draw_bim(ax, tunnel: Dict[str, Any],
              bim_tunnel: Optional[Dict[str, Any]],
              defects: Sequence[Dict[str, Any]]) -> None:
    length = float(tunnel.get("length_m", 1000) or 1000)
    diameter = float((bim_tunnel or {}).get("internal_diameter_m")
                     or DEFAULT_DIAMETER_M)
    r = diameter / 2.0

    xs = np.linspace(0.0, length, 40)
    phi = np.linspace(0.0, 2 * np.pi, 36)
    X, P = np.meshgrid(xs, phi)
    ax.plot_surface(X, r * np.sin(P), r * np.cos(P),
                    alpha=0.13, color=TUNNEL_LINE, linewidth=0)

    for priority in PRIORITY_ORDER:
        pts = [d for d in defects
               if _priority_of(d) == priority and d.get("chainage_m") is not None]
        if not pts:
            continue
        ang = [math.radians(position_to_angle_deg(d.get("position", "")))
               for d in pts]
        ax.scatter(
            [min(float(d["chainage_m"]), length) for d in pts],
            [(r + 0.4) * math.sin(a) for a in ang],
            [(r + 0.4) * math.cos(a) for a in ang],
            color=PRIORITY_COLOURS[priority], s=26, depthshade=False,
            edgecolors="white", linewidths=0.5,
        )

    ax.set_box_aspect((5, 1, 1))
    # No axis label: at this size it lands on top of the tick numbers, and the
    # chainage strip directly below already labels the axis.
    ax.set_xlabel("")
    ax.set_yticks([])
    ax.set_zticks([])
    ax.tick_params(labelsize=6.5, colors=MUTED, pad=0.5)
    ax.view_init(elev=18, azim=-62)
    # 3-D axes float their title high and centred; pin it to the left edge so
    # it lines up with the other panel titles.
    ax.set_title(f"Lining model — Ø{diameter:g} m  ·  chainage (m)",
                 fontsize=9, color=INK, x=0.0, ha="left", y=0.94)


# =============================================================================
# Chainage strip — where the defects sit along the tunnel
# =============================================================================
def _draw_strip(ax, tunnel: Dict[str, Any],
                defects: Sequence[Dict[str, Any]]) -> None:
    length = float(tunnel.get("length_m", 1000) or 1000)
    ax.add_patch(Rectangle((0, 0.35), length, 0.30,
                           facecolor="#EDEDF5", edgecolor=GRID, zorder=1))

    placed = [d for d in defects if d.get("chainage_m") is not None]
    if not placed:
        ax.set_xlim(0, length)
        ax.set_ylim(0, 1)
        _empty(ax, "No defects carry a chainage value.")
        ax.set_title("Defect distribution along the tunnel", fontsize=9,
                     color=INK, loc="left")
        return

    for d in placed:
        x = min(float(d["chainage_m"]), length)
        ax.vlines(x, 0.35, 0.65, color=_colour_of(d), linewidth=2.4, zorder=3)
        ax.scatter([x], [0.72], s=34, color=_colour_of(d),
                   edgecolor="white", linewidths=0.7, zorder=4)

    # Label only the highest-priority handful, so the strip stays readable.
    # Labels hang BELOW the band: above it they collide with the title.
    labelled = sorted(placed,
                      key=lambda d: (PRIORITY_ORDER.index(_priority_of(d)),
                                     float(d.get("chainage_m") or 0)))[:6]
    for d in labelled:
        ax.annotate(str(d.get("defect_id", "")),
                    (min(float(d["chainage_m"]), length), 0.30),
                    rotation=90, fontsize=6, color=INK,
                    ha="center", va="top")

    ax.set_xlim(-length * 0.01, length * 1.01)
    ax.set_ylim(0, 0.95)
    ax.set_yticks([])
    ax.set_xlabel("Chainage (m)", fontsize=7, color=MUTED, labelpad=1)
    ax.set_title("Defect distribution along the tunnel", fontsize=9,
                 color=INK, loc="left", pad=4)
    _style(ax)
    ax.grid(axis="y", visible=False)


# =============================================================================
# Priority mix
# =============================================================================
def _draw_priority(ax, defects: Sequence[Dict[str, Any]]) -> None:
    counts = {p: sum(1 for d in defects if _priority_of(d) == p)
              for p in PRIORITY_ORDER}
    if not sum(counts.values()):
        _empty(ax, "No defects registered.")
        ax.set_title("Defects by priority", fontsize=9, color=INK, loc="left")
        return

    labels = [p for p in PRIORITY_ORDER if counts[p]]
    values = [counts[p] for p in labels]
    colours = [PRIORITY_COLOURS[p] for p in labels]

    wedges, _ = ax.pie(values, colors=colours, startangle=90,
                       wedgeprops=dict(width=0.42, edgecolor="white",
                                       linewidth=1.6))
    ax.text(0, 0, str(sum(values)), ha="center", va="center",
            fontsize=16, color=INK, fontweight="bold")
    ax.text(0, -0.26, "defects", ha="center", va="center",
            fontsize=7, color=MUTED)
    ax.legend(wedges, [f"{l} — {v}" for l, v in zip(labels, values)],
              loc="center left", bbox_to_anchor=(0.92, 0.5),
              fontsize=6.5, frameon=False, labelcolor=INK)
    ax.set_title("Defects by priority", fontsize=9, color=INK, loc="left")


# =============================================================================
# Cost exposure
# =============================================================================
def cost_by_priority(defects: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    totals = {p: 0.0 for p in PRIORITY_ORDER}
    for d in defects:
        try:
            amount, _ = effective_cost(d)
        except Exception:
            amount = 0.0
        totals[_priority_of(d)] += float(amount or 0.0)
    return totals


def _draw_cost(ax, defects: Sequence[Dict[str, Any]]) -> None:
    totals = cost_by_priority(defects)
    labels = [p for p in PRIORITY_ORDER if totals[p] > 0]
    if not labels:
        _empty(ax, "No cost estimate available.")
        ax.set_title("Estimated cost exposure", fontsize=9, color=INK, loc="left")
        return

    values = [totals[p] for p in labels]
    bars = ax.barh(labels[::-1], values[::-1],
                   color=[PRIORITY_COLOURS[p] for p in labels[::-1]],
                   height=0.55, edgecolor="white", linewidth=1.0)
    for bar, value in zip(bars, values[::-1]):
        ax.annotate(f"${value:,.0f}",
                    (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7, color=INK)

    ax.set_xlim(0, max(values) * 1.28)
    ax.set_xlabel("AUD", fontsize=7, color=MUTED)
    ax.set_title(f"Estimated cost exposure — ${sum(values):,.0f} total",
                 fontsize=9, color=INK, loc="left")
    _style(ax)
    ax.grid(axis="y", visible=False)
    # FuncFormatter rather than set_xticklabels: the tick locator is still
    # free to choose its own tick count, so the labels cannot drift out of
    # step with the ticks.
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda t, _: f"{t / 1000:.0f}k" if t >= 1000 else f"{t:.0f}"))


# =============================================================================
# The composite panel
# =============================================================================
def render_onepager_panel(tunnel: Dict[str, Any],
                          bim_tunnel: Optional[Dict[str, Any]],
                          defects: Sequence[Dict[str, Any]]) -> bytes:
    """
    One PNG carrying map, BIM, chainage strip, priority mix and cost.

    Composed as a single figure rather than five separate includes so the
    one-pager's layout is guaranteed — the block either fits or is scaled as a
    unit, and never reflows into a second page.
    """
    # Aspect matters: at A4 content width (~186 mm) this panel is ~113 mm
    # tall, which leaves room for the masthead, KPI tiles, actions table and
    # footer on a single page. A squarer panel pushes the one-pager onto a
    # second page, which defeats the point of it.
    fig = plt.figure(figsize=(12.6, 7.6), dpi=170, facecolor=PANEL_BG)
    grid = gridspec.GridSpec(
        3, 2, figure=fig,
        height_ratios=[1.10, 0.40, 0.80], width_ratios=[1.0, 1.0],
        hspace=0.48, wspace=0.20,
        left=0.055, right=0.975, top=0.945, bottom=0.075,
    )

    _draw_map(fig.add_subplot(grid[0, 0]), tunnel, defects)
    _draw_bim(fig.add_subplot(grid[0, 1], projection="3d"),
              tunnel, bim_tunnel, defects)
    _draw_strip(fig.add_subplot(grid[1, :]), tunnel, defects)
    _draw_priority(fig.add_subplot(grid[2, 0]), defects)
    _draw_cost(fig.add_subplot(grid[2, 1]), defects)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=PANEL_BG, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# =============================================================================
# Action list used by both documents
# =============================================================================
def prescribed_actions(defects: Sequence[Dict[str, Any]],
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Defects ordered by urgency then cost, with the action and its estimate.

    `limit` trims the list for the one-pager; the comprehensive report passes
    None so nothing is hidden.
    """
    rows = []
    for d in defects:
        try:
            amount, basis = effective_cost(d)
        except Exception:
            amount, basis = 0.0, "—"

        steps = d.get("prescribed_interventions") or []
        if steps:
            action = str(steps[0].get("step", "")).strip()
            if len(steps) > 1:
                action += f" (+{len(steps) - 1} further step"
                action += "s)" if len(steps) > 2 else ")"
        else:
            action = str(d.get("threshold_triggered") or "Assessment required")

        rows.append({
            "defect_id": d.get("defect_id", "—"),
            "defect_type": d.get("defect_type", "—"),
            "chainage_m": d.get("chainage_m"),
            "priority": _priority_of(d),
            "severity": d.get("severity", "—"),
            "action": action,
            "deadline_days": d.get("deadline_days"),
            "cost": float(amount or 0.0),
            "cost_basis": basis,
        })

    rows.sort(key=lambda r: (PRIORITY_ORDER.index(r["priority"]), -r["cost"]))
    return rows[:limit] if limit else rows


def totals(defects: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Headline numbers shared by both documents, so they cannot disagree."""
    active = [d for d in defects
              if str(d.get("status", "Active")).lower() in ("active", "open")]
    by_priority = {p: sum(1 for d in active if _priority_of(d) == p)
                   for p in PRIORITY_ORDER}
    cost = sum(cost_by_priority(active).values())
    scores = [float(d.get("completeness_score") or 0.0) for d in active]
    return {
        "total": len(defects),
        "active": len(active),
        "high": by_priority["HIGH"],
        "medium": by_priority["MEDIUM"],
        "low": by_priority["LOW"],
        "cost": cost,
        "confidence_pct": int(round(100 * sum(scores) / len(scores))) if scores else 0,
    }
