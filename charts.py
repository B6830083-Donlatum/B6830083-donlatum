"""Small dependency-free SVG chart renderer for parsed ngspice data."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence

WIDTH = 860
HEIGHT = 300
MARGIN = {"left": 64, "right": 22, "top": 24, "bottom": 52}


def _fmt(value: float) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude < 1e-3 or magnitude >= 1e5:
        return f"{value:.2e}"
    return f"{value:.4g}"


def _downsample(x: Sequence[float], y: Sequence[float], limit: int = 500):
    if len(x) <= limit:
        return list(x), list(y)
    step = len(x) / limit
    indices = [int(i * step) for i in range(limit)]
    if indices[-1] != len(x) - 1:
        indices[-1] = len(x) - 1
    return [x[i] for i in indices], [y[i] for i in indices]


def line_chart(
    title: str,
    x_label: str,
    y_label: str,
    traces: List[Dict[str, Any]],
    *,
    log_x: bool = False,
) -> str:
    """Return an SVG string drawn only from numbers supplied by the parser."""

    series = []
    for trace in traces:
        xs, ys = _downsample(trace["x"], trace["y"])
        if log_x:
            xs = [math.log10(v) if v > 0 else math.log10(1e-12) for v in xs]
        series.append((trace.get("name", "trace"), trace.get("color", "#0f7d8c"), xs, ys))

    all_x = [x for _, _, xs, _ in series for x in xs]
    all_y = [y for _, _, _, ys in series for y in ys]
    if not all_x or not all_y:
        return '<p class="error">ไม่มีข้อมูลกราฟจากการจำลอง</p>'

    xmin, xmax = min(all_x), max(all_x)
    ymin, ymax = min(all_y), max(all_y)
    if xmin == xmax:
        xmin -= 1
        xmax += 1
    if ymin == ymax:
        ymin -= 1
        ymax += 1
    ypad = (ymax - ymin) * 0.08
    ymin -= ypad
    ymax += ypad

    plot_w = WIDTH - MARGIN["left"] - MARGIN["right"]
    plot_h = HEIGHT - MARGIN["top"] - MARGIN["bottom"]

    def sx(x: float) -> float:
        return MARGIN["left"] + (x - xmin) / (xmax - xmin) * plot_w

    def sy(y: float) -> float:
        return MARGIN["top"] + plot_h - (y - ymin) / (ymax - ymin) * plot_h

    parts = [
        f'<svg class="plot" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{title}">',
        f'<text class="plot-title" x="{MARGIN["left"]}" y="17">{title}</text>',
    ]

    for tick in range(5):
        yv = ymin + (ymax - ymin) * tick / 4
        y = sy(yv)
        parts.append(
            f'<line x1="{MARGIN["left"]}" y1="{y:.1f}" x2="{WIDTH - MARGIN["right"]}" '
            f'y2="{y:.1f}" class="grid"/>'
        )
        parts.append(
            f'<text x="{MARGIN["left"] - 8}" y="{y + 4:.1f}" class="tick" '
            f'text-anchor="end">{_fmt(yv)}</text>'
        )
        xv = xmin + (xmax - xmin) * tick / 4
        x = sx(xv)
        parts.append(
            f'<line x1="{x:.1f}" y1="{MARGIN["top"]}" x2="{x:.1f}" '
            f'y2="{HEIGHT - MARGIN["bottom"]}" class="grid"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{HEIGHT - MARGIN["bottom"] + 18}" class="tick" '
            f'text-anchor="middle">{_fmt(xv)}</text>'
        )

    parts.append(
        f'<line x1="{MARGIN["left"]}" y1="{MARGIN["top"] + plot_h}" '
        f'x2="{WIDTH - MARGIN["right"]}" y2="{MARGIN["top"] + plot_h}" class="axis"/>'
    )
    parts.append(
        f'<line x1="{MARGIN["left"]}" y1="{MARGIN["top"]}" x2="{MARGIN["left"]}" '
        f'y2="{MARGIN["top"] + plot_h}" class="axis"/>'
    )

    legend_x = MARGIN["left"] + 8
    for name, color, xs, ys in series:
        path = " ".join(
            f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}"
            for i, (x, y) in enumerate(zip(xs, ys))
        )
        parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>'
        )
        parts.append(
            f'<rect x="{legend_x}" y="{MARGIN["top"] + 4}" width="10" height="4" '
            f'fill="{color}"/>'
        )
        parts.append(
            f'<text x="{legend_x + 14}" y="{MARGIN["top"] + 9}" class="legend">'
            f"{name}</text>"
        )
        legend_x += 14 + len(name) * 7.2

    parts.append(
        f'<text x="{WIDTH / 2}" y="{HEIGHT - 8}" class="axis-label" '
        f'text-anchor="middle">{x_label}</text>'
    )
    parts.append(
        f'<text transform="translate(14 {MARGIN["top"] + plot_h / 2}) rotate(-90)" '
        f'class="axis-label" text-anchor="middle">{y_label}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def ac_charts(traces: List[Dict[str, Any]]) -> Dict[str, str]:
    gain = [t for t in traces if "Gain" in t["name"]]
    phase = [t for t in traces if "Phase" in t["name"]]
    return {
        "gain": line_chart(
            "Bode magnitude - real ngspice .ac run",
            "Frequency (Hz, log scale)",
            "|Gain| (dB)",
            gain,
            log_x=True,
        ),
        "phase": line_chart(
            "Bode phase - real ngspice .ac run",
            "Frequency (Hz, log scale)",
            "Phase (degrees)",
            phase,
            log_x=True,
        ),
    }


def tran_charts(traces: List[Dict[str, Any]]) -> Dict[str, str]:
    converted = []
    for trace in traces:
        item = dict(trace)
        item["x"] = [t * 1000.0 for t in trace["x"]]
        converted.append(item)
    return {
        "wave": line_chart(
            "Transient waveforms - real ngspice .tran run",
            "Time (ms)",
            "Voltage (V)",
            converted,
        )
    }
