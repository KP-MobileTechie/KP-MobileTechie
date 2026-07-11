#!/usr/bin/env python3
"""
Generate self-hosted GitHub metric SVGs (streak card + contribution area graph)
directly from GitHub's contribution calendar data. No third-party image services,
so the README never breaks when those go down.

Input: a text file with one "YYYY-MM-DD <count>" per line (all-time daily history).
Output: assets/streak-stats.svg and assets/activity-graph.svg

Usage: python scripts/generate_metrics.py <days_file>
"""
import sys
import datetime
from pathlib import Path

# ---- theme: "precision spec sheet" ----
# Grounded in an engineering datasheet: GitHub-canvas base so the cards blend
# into the README, a single restrained cyan accent, hairlines, tabular mono
# numerals. No glow, no glass, no secondary accents.
BG = "#0d1117"          # GitHub dark canvas
PANEL = "#0f141b"       # barely-raised surface
ACCENT = "#22d3ee"      # the one accent
TEXT = "#f0f6fc"        # primary figures
MUTED = "#7d8590"       # labels, captions, axis
HAIR = "rgba(240,246,252,0.10)"   # hairline rules / borders
GRID = "rgba(240,246,252,0.055)"  # chart gridlines
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"
MONO = "ui-monospace, 'Cascadia Code', 'Segoe UI Mono', Consolas, monospace"


def defs_block(p):
    return f'''<defs>
    <linearGradient id="{p}-area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
  </defs>'''


def base_style():
    # STATIC-FIRST: everything is fully visible by default. Motion is a single
    # gentle fade-in enhancement that can never leave content hidden, plus a
    # slow "live" pulse on the status dot. Reduced motion disables both.
    return f'''<style>
    text {{ font-family: {FONT}; }}
    @keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes blip {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .35; }} }}
    .fade {{ animation: fadein .8s ease-out; }}
    .live {{ animation: blip 2.4s ease-in-out infinite; }}
    @media (prefers-reduced-motion: reduce) {{
      .fade {{ animation: none; }}
      .live {{ animation: none; opacity: 1; }}
    }}
  </style>'''


def panel_bg(w, h, p):
    # A single hairline-bordered card on the GitHub canvas.
    return (f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="13" fill="{BG}" stroke="{HAIR}"/>')


def load_days(path):
    days = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d, c = line.split()
        days[d] = int(c)
    return dict(sorted(days.items()))


def fmt_date(d):
    # cross-platform (no %-d on Windows)
    dt = datetime.date.fromisoformat(d)
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


def fmt_short(d):
    dt = datetime.date.fromisoformat(d)
    return f"{dt.strftime('%b')} {dt.day}"


def fmt_my(d):
    dt = datetime.date.fromisoformat(d)
    return f"{dt.strftime('%b')} '{dt.strftime('%y')}"


def span(rr):
    a, b = rr
    if not a:
        return "—"
    if a == b:
        return fmt_short(a)
    # omit year when both ends share it
    ay = a[:4]
    by = b[:4]
    if ay == by:
        return f"{fmt_short(a)} – {fmt_short(b)}"
    return f"{fmt_my(a)} – {fmt_my(b)}"


def compute(days):
    items = list(days.items())  # sorted (date, count)
    total = sum(c for _, c in items)

    # longest streak
    longest = 0
    l_start = l_end = None
    run = 0
    run_start = None
    for d, c in items:
        if c > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest:
                longest = run
                l_start, l_end = run_start, d
        else:
            run = 0

    # current streak: count back from the last day; if last day is 0, allow
    # the streak to end on the previous day (today still "pending").
    dates = [d for d, _ in items]
    counts = [c for _, c in items]
    i = len(items) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    cur = 0
    c_start = c_end = None
    while i >= 0 and counts[i] > 0:
        if cur == 0:
            c_end = dates[i]
        c_start = dates[i]
        cur += 1
        i -= 1

    # total range spans the FIRST real contribution to the last, not the
    # zero-padded calendar edges (which start at a January 1 year boundary).
    nonzero = [d for d, c in items if c > 0]
    first = nonzero[0] if nonzero else (dates[0] if dates else None)
    last = nonzero[-1] if nonzero else (dates[-1] if dates else None)
    return {
        "total": total,
        "total_range": (first, last),
        "current": cur,
        "current_range": (c_start, c_end),
        "longest": longest,
        "longest_range": (l_start, l_end),
    }


def streak_svg(m):
    W, H, P = 495, 172, "s"
    PADX = 30
    inner = W - 2 * PADX
    # three columns, centered
    cxs = [PADX + inner * (1 / 6), PADX + inner * (1 / 2), PADX + inner * (5 / 6)]
    # baseline grid rows
    NUM_Y = 104
    LAB_Y = 126
    RULE_Y = 134
    CAP_Y = 152

    stats = [
        (f"{m['total']:,}", "TOTAL", f"since {fmt_my(m['total_range'][0])}" if m['total_range'][0] else "—", False),
        (f"{m['current']}", "CURRENT", span(m['current_range']), True),
        (f"{m['longest']}", "LONGEST", span(m['longest_range']), False),
    ]

    cells = ""
    for cx, (val, lab, cap, hero) in zip(cxs, stats):
        num_cls = "num hero" if hero else "num"
        rule_col = ACCENT if hero else HAIR
        rule_w = 30 if hero else 22
        cells += (
            f'<text class="{num_cls}" x="{cx:.1f}" y="{NUM_Y}">{val}</text>'
            f'<text class="lab" x="{cx:.1f}" y="{LAB_Y}">{lab}</text>'
            f'<line x1="{cx-rule_w/2:.1f}" y1="{RULE_Y}" x2="{cx+rule_w/2:.1f}" y2="{RULE_Y}" stroke="{rule_col}" stroke-width="1.5"/>'
            f'<text class="cap" x="{cx:.1f}" y="{CAP_Y}">{cap}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="Contribution streak: {m['current']} day current streak, {m['longest']} longest, {m['total']} total contributions">
  {defs_block(P)}
  {base_style()}
  <style>
    .eyebrow {{ font: 700 10px {FONT}; fill: {MUTED}; letter-spacing: 2.4px; }}
    .meta {{ font: 600 10px {MONO}; fill: {MUTED}; }}
    .num {{ font: 500 34px {MONO}; fill: {TEXT}; letter-spacing: -1px; text-anchor: middle; }}
    .hero {{ font-weight: 700; fill: {ACCENT}; }}
    .lab {{ font: 700 9.5px {FONT}; fill: {MUTED}; letter-spacing: 1.8px; text-anchor: middle; }}
    .cap {{ font: 400 9.5px {MONO}; fill: {MUTED}; text-anchor: middle; }}
  </style>
  {panel_bg(W, H, P)}
  <g class="fade">
    <text class="eyebrow" x="{PADX}" y="40">CONTRIBUTION STREAK</text>
    <circle class="live" cx="{W-PADX-52}" cy="36" r="3" fill="{ACCENT}"/>
    <text class="meta" x="{W-PADX-42}" y="40">active</text>
    <line x1="{PADX}" y1="56" x2="{W-PADX}" y2="56" stroke="{HAIR}"/>
    {cells}
  </g>
</svg>
'''


def activity_svg(days):
    items = list(days.items())[-365:]
    counts = [c for _, c in items]
    dates = [datetime.date.fromisoformat(d) for d, _ in items]
    n = len(items)
    W, H, P = 820, 232, "a"
    pad_l, pad_r, pad_t, pad_b = 52, 26, 88, 34
    plot_w, plot_h = W - pad_l - pad_r, H - pad_t - pad_b
    mx = max(max(counts), 1)
    total = sum(counts)
    base = pad_t + plot_h

    def px(i):
        return pad_l + plot_w * i / (n - 1 if n > 1 else 1)

    def py(v):
        return base - plot_h * v / mx

    pts = [(px(i), py(c)) for i, c in enumerate(counts)]
    line = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = (f"M {pts[0][0]:.1f},{base:.1f} L "
            + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            + f" L {pts[-1][0]:.1f},{base:.1f} Z")

    peak_i = counts.index(mx)
    pkx, pky = pts[peak_i]
    endx, endy = pts[-1]

    # horizontal gridlines + left y-axis labels (0, mid, peak)
    grid = ""
    for v in (0, mx // 2, mx):
        y = py(v)
        grid += (f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W-pad_r}" y2="{y:.1f}" stroke="{GRID}"/>'
                 f'<text class="yl" x="{pad_l-10}" y="{y+3:.1f}">{v}</text>')

    # month labels
    ticks = ""
    seen = set()
    for i, dt in enumerate(dates):
        key = (dt.year, dt.month)
        if dt.day <= 7 and key not in seen:
            seen.add(key)
            ticks += f'<text class="ml" x="{px(i):.1f}" y="{base+22:.0f}">{dt.strftime("%b")}</text>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="Contribution activity, peak {mx} per day, {total} contributions in the last 12 months">
  {defs_block(P)}
  {base_style()}
  <style>
    .title {{ font: 600 16px {FONT}; fill: {TEXT}; letter-spacing: .2px; }}
    .sub {{ font: 400 11px {FONT}; fill: {MUTED}; }}
    .kv {{ font: 400 11px {FONT}; fill: {MUTED}; text-anchor: end; }}
    .kn {{ font: 600 11px {MONO}; fill: {TEXT}; text-anchor: end; }}
    .yl {{ font: 400 9.5px {MONO}; fill: {MUTED}; text-anchor: end; }}
    .ml {{ font: 400 10px {MONO}; fill: {MUTED}; text-anchor: middle; }}
    .pk {{ font: 600 10px {MONO}; fill: {ACCENT}; text-anchor: middle; }}
  </style>
  {panel_bg(W, H, P)}
  <text class="title" x="{pad_l}" y="38">Contribution activity</text>
  <text class="sub" x="{pad_l}" y="56">last 12 months</text>
  <text class="kn" x="{W-pad_r}" y="34">{total:,}</text>
  <text class="kv" x="{W-pad_r}" y="50">contributions · peak {mx}/day</text>
  <line x1="{pad_l}" y1="68" x2="{W-pad_r}" y2="68" stroke="{HAIR}"/>
  <g class="fade">
    {grid}
    {ticks}
    <path d="{area}" fill="url(#{P}-area)"/>
    <path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="{pkx:.1f}" cy="{pky:.1f}" r="3" fill="{BG}" stroke="{ACCENT}" stroke-width="1.75"/>
    <text class="pk" x="{pkx:.1f}" y="{pky-9:.1f}">{mx}</text>
    <circle cx="{endx:.1f}" cy="{endy:.1f}" r="2.5" fill="{ACCENT}"/>
  </g>
</svg>
'''


def main():
    days_file = sys.argv[1] if len(sys.argv) > 1 else "assets/.contrib-daily.txt"
    days = load_days(days_file)
    if not days:
        print("no data; refusing to overwrite", file=sys.stderr)
        sys.exit(1)
    m = compute(days)
    out = Path("assets")
    out.mkdir(exist_ok=True)
    (out / "streak-stats.svg").write_text(streak_svg(m), encoding="utf-8")
    (out / "activity-graph.svg").write_text(activity_svg(days), encoding="utf-8")
    print(f"total={m['total']} current={m['current']} longest={m['longest']}")


if __name__ == "__main__":
    main()
