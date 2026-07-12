"""
On-demand report generation for the Telegram ``/report`` command.

Renders the same views the web dashboard shows — a daily trend, the per-task
composition, each task's share and a GitHub-style activity heatmap — as PNG
images with matplotlib, computed off the shared aggregation in
:mod:`ticktask.services`. Kept separate from :mod:`ticktask.telegram` (which
sends the images) so it has no bot dependencies and is easy to test in isolation.
"""

import io
from datetime import date, datetime, timedelta

import matplotlib

matplotlib.use("Agg")  # headless: render to a buffer, never to a display.

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from django.utils import timezone  # noqa: E402

from ticktask import services  # noqa: E402

# The trend/composition/share charts look at the trailing month; the heatmap at
# a trailing year of daily data (like the web dashboard's heatmap).
REPORT_DAYS = 30
HEATMAP_DAYS = 53 * 7

# Same qualitative palette as the frontend, so a task keeps its color.
PALETTE = [
    "#007CBF",
    "#5EA611",
    "#D30F4B",
    "#9333EA",
    "#F59E0B",
    "#0EA5E9",
    "#14B8A6",
    "#EC4899",
]
_EMPTY = "#E2E8F0"  # muted fill for zero/idle cells
_TEXT = "#334155"

_DPI = 150


def _color(index: int) -> str:
    """Stable color for the series at ``index`` (cycles the palette)."""
    return PALETTE[index % len(PALETTE)]


def _fmt_hours(hours: float) -> str:
    """Formats decimal hours as a compact ``Xh Ym`` label (``0h`` when empty)."""
    minutes = round((hours or 0) * 60)
    if minutes <= 0:
        return "0h"
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    return f"{h}h" if h else f"{m}m"


def _fmt_td(delta: timedelta) -> str:
    """Formats a duration as a compact ``Xh Ym`` label."""
    return _fmt_hours(delta.total_seconds() / 3600)


def _fig_to_png(fig) -> bytes:
    """Serializes a figure to PNG bytes and releases it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _style(ax, title: str) -> None:
    """Applies the shared minimal chart styling."""
    ax.set_title(title, fontsize=12, fontweight="bold", color=_TEXT, pad=10)
    ax.tick_params(colors=_TEXT, labelsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#CBD5E1")
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.set_axisbelow(True)


def _dates(buckets) -> list:
    """The buckets' ``period_start`` values as ``date`` objects."""
    out = []
    for b in buckets:
        ps = b["period_start"]
        out.append(ps if isinstance(ps, date) else datetime.fromisoformat(str(ps)).date())
    return out


# --------------------------------------------------------------------------- #
# Individual charts (each takes a `time_series`-shaped dict, returns PNG bytes)
# --------------------------------------------------------------------------- #


def render_trend(series: dict) -> bytes:
    """Daily total tracked hours over the range, as a bar chart."""
    days = _dates(series["buckets"])
    hours = [b["hours"] for b in series["buckets"]]

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.bar(days, hours, color=PALETTE[0], width=0.9)
    _style(ax, "Tracked hours per day — last 30 days")
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_ylabel("hours", fontsize=8, color=_TEXT)
    fig.autofmt_xdate(rotation=0, ha="center")
    return _fig_to_png(fig)


def render_composition(series: dict) -> bytes:
    """Stacked bar per day, one segment per task."""
    days = _dates(series["buckets"])
    tasks = [t for t in series["by_task"] if any(h > 0 for h in t.get("series", []))]

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    bottom = np.zeros(len(days))
    for i, task in enumerate(tasks):
        values = np.array(task.get("series", []), dtype=float)
        if values.size != len(days):
            values = np.resize(values, len(days))
        ax.bar(
            days,
            values,
            bottom=bottom,
            width=0.9,
            color=_color(series["by_task"].index(task)),
            label=task["task_name"],
        )
        bottom += values
    _style(ax, "Composition by task — last 30 days")
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    if tasks:
        ax.legend(fontsize=7, loc="upper left", frameon=False, ncol=2)
    fig.autofmt_xdate(rotation=0, ha="center")
    return _fig_to_png(fig)


def render_share(series: dict) -> bytes:
    """Donut of each task's share of the tracked time in the range."""
    tasks = sorted(
        [t for t in series["by_task"] if t["hours"] > 0],
        key=lambda t: t["hours"],
        reverse=True,
    )
    total = sum(t["hours"] for t in tasks)

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    if tasks:
        colors = [_color(series["by_task"].index(t)) for t in tasks]
        ax.pie(
            [t["hours"] for t in tasks],
            labels=[t["task_name"] for t in tasks],
            colors=colors,
            autopct=lambda p: f"{p:.0f}%" if p >= 6 else "",
            pctdistance=0.8,
            wedgeprops=dict(width=0.42, edgecolor="white"),
            textprops=dict(fontsize=8, color=_TEXT),
        )
        ax.text(0, 0, _fmt_hours(total), ha="center", va="center",
                fontsize=13, fontweight="bold", color=_TEXT)
    else:
        ax.text(0.5, 0.5, "No tracked time", ha="center", va="center",
                fontsize=10, color=_TEXT, transform=ax.transAxes)
        ax.axis("off")
    ax.set_title("Share by task — last 30 days", fontsize=12,
                 fontweight="bold", color=_TEXT, pad=10)
    return _fig_to_png(fig)


def render_heatmap(series: dict, *, weeks: int = 53, end: date | None = None) -> bytes:
    """GitHub-style daily activity heatmap over a trailing year."""
    end = end or timezone.now().date()
    by_date = {d.isoformat(): h for d, h in zip(_dates(series["buckets"]),
                                                [b["hours"] for b in series["buckets"]])}
    # Monday of the last column, then walk back to the first column's Monday.
    first_monday = end - timedelta(days=end.weekday() + (weeks - 1) * 7)

    grid = np.full((7, weeks), np.nan)
    for w in range(weeks):
        for d in range(7):
            day = first_monday + timedelta(days=w * 7 + d)
            if day > end:
                continue
            grid[d, w] = by_date.get(day.isoformat(), 0.0)

    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "activity", [_EMPTY, PALETTE[0]]
    ).with_extremes(bad="white")
    vmax = np.nanmax(grid) if np.isfinite(grid).any() else 1
    ax.imshow(np.ma.masked_invalid(grid), aspect="equal", cmap=cmap,
              vmin=0, vmax=vmax or 1)

    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "", "Wed", "", "Fri", "", ""], fontsize=7, color=_TEXT)
    # Month labels where a new month first appears at the top of a column.
    ticks, labels, last_month = [], [], -1
    for w in range(weeks):
        first = first_monday + timedelta(days=w * 7)
        if first.month != last_month:
            last_month = first.month
            ticks.append(w)
            labels.append(first.strftime("%b"))
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=7, color=_TEXT)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Daily activity — last year", fontsize=12,
                 fontweight="bold", color=_TEXT, pad=10)
    return _fig_to_png(fig)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def _caption(user, zone, series: dict, summary: dict) -> str:
    """Builds the text summary shown as the album caption, in the user's zone."""
    now = timezone.now()
    now_local = now.astimezone(zone)
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    today = services.tracked_total(user, day_start, now)
    week = services.tracked_total(user, now - timedelta(days=7), now)
    month_hours = sum(b["hours"] for b in series["buckets"])

    top = sorted(
        [t for t in series["by_task"] if t["hours"] > 0],
        key=lambda t: t["hours"],
        reverse=True,
    )[:3]

    lines = [
        f"📊 TickTask report — {now_local.strftime('%Y-%m-%d')}",
        "",
        f"⏱ Today: {_fmt_td(today)}",
        f"📅 Last 7 days: {_fmt_td(week)}",
        f"🗓 Last 30 days: {_fmt_hours(month_hours)}",
        f"🏆 All time: {_fmt_hours(summary['total_hours'])}",
    ]
    if top:
        lines.append("")
        lines.append("Top tasks (30d):")
        for i, task in enumerate(top, 1):
            lines.append(f"{i}. {task['task_name']} — {_fmt_hours(task['hours'])}")
    return "\n".join(lines)


def has_data(user) -> bool:
    """Whether the user has any tracked time to report on."""
    return services.dashboard_summary(user)["total_hours"] > 0


def build_report(user, zone) -> tuple[str, list[tuple[str, bytes]]]:
    """
    Computes the aggregates and renders the report: returns the caption text and
    the list of ``(filename, png_bytes)`` charts, ready to send as an album.
    """
    now = timezone.now()
    series = services.time_series(user, now - timedelta(days=REPORT_DAYS), now, "day")
    year = services.time_series(user, now - timedelta(days=HEATMAP_DAYS), now, "day")
    summary = services.dashboard_summary(user)

    images = [
        ("trend.png", render_trend(series)),
        ("composition.png", render_composition(series)),
        ("share.png", render_share(series)),
        ("heatmap.png", render_heatmap(year)),
    ]
    return _caption(user, zone, series, summary), images
