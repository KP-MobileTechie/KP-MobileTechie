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

# ---- theme (matches the old widget colors) ----
BG = "#06060b"
ACCENT = "#22d3ee"      # ring / line
FIRE = "#f472b6"        # fire + area accent
LABEL = "#a78bfa"       # current-streak label
TEXT = "#e7e9ee"
MUTED = "#8b8ba7"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"
MONO = "ui-monospace, 'Cascadia Code', 'Segoe UI Mono', Consolas, monospace"


def defs_block(p):
    return f'''<defs>
    <radialGradient id="{p}-glowA" cx="12%" cy="0%" r="80%">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.10"/>
      <stop offset="55%" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{p}-glowB" cx="95%" cy="100%" r="80%">
      <stop offset="0%" stop-color="{FIRE}" stop-opacity="0.10"/>
      <stop offset="55%" stop-color="{FIRE}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="{p}-ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{ACCENT}"/>
      <stop offset="100%" stop-color="{LABEL}"/>
    </linearGradient>
    <linearGradient id="{p}-area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <filter id="{p}-glow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3.2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="{p}-dots" width="14" height="14" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="{TEXT}" fill-opacity="0.03"/>
    </pattern>
  </defs>'''


def base_style():
    # STATIC-FIRST: every element is fully visible by default (opacity 1, no
    # hidden dash offsets). Animations are enhancement-only and can never leave
    # content hidden, so the card renders correctly even if animation never runs.
    return f'''<style>
    text {{ font-family: {FONT}; }}
    @keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes pulse {{ 0%,100% {{ opacity: .5; }} 50% {{ opacity: 1; }} }}
    .fade {{ animation: fadein .9s ease-out; }}
    .glowpulse {{ animation: pulse 3.5s ease-in-out infinite; }}
    @media (prefers-reduced-motion: reduce) {{
      .fade {{ animation: none; }}
      .glowpulse {{ animation: none; opacity: 1; }}
    }}
  </style>'''


def panel_bg(w, h, p):
    return f'''<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>
  <rect width="{w}" height="{h}" rx="12" fill="url(#{p}-glowA)"/>
  <rect width="{w}" height="{h}" rx="12" fill="url(#{p}-glowB)"/>
  <rect width="{w}" height="{h}" rx="12" fill="url(#{p}-dots)"/>'''


def load_days(path):
    days = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d, c = line.split()
        days[d] = int(c)
    return dict(sorted(days.items()))


def fmt(d):
    return datetime.date.fromisoformat(d).strftime("%b %-d, %Y") if hasattr(datetime.date, "strftime") else d


def fmt_date(d):
    # cross-platform (no %-d on Windows)
    dt = datetime.date.fromisoformat(d)
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


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
    W, H, P = 495, 210, "s"
    col = W / 3
    cx = col * 1.5
    # shared layout grid: every column aligns on the same three rows
    BIG_Y = 104      # baseline of the big number / vertical center of the ring
    LAB_Y = 154      # label row (all three columns)
    DATE_Y = 178     # date row (all three columns)
    cy = 96          # ring center
    r = 37
    frac = min(m["current"] / m["longest"], 1.0) if m["longest"] else 0.0
    circ = 2 * 3.14159265 * r
    dash = f'{circ*frac:.1f} {circ:.1f}'

    def rng(rr):
        a, b = rr
        if not a:
            return "-"
        return fmt_date(a) if a == b else f"{fmt_date(a)} → {fmt_date(b)}"

    def panel(x, accent):
        return (f'<rect x="{x+13:.0f}" y="24" width="{col-26:.0f}" height="{H-48}" rx="14" '
                f'fill="rgba(255,255,255,.025)" stroke="rgba(255,255,255,.08)"/>'
                f'<rect x="{x+13:.0f}" y="24" width="{col-26:.0f}" height="2.5" rx="1.2" '
                f'fill="{accent}" fill-opacity="0.6"/>')

    def side(x, value, label, rr, accent):
        return (f'<text class="side c" x="{x:.0f}" y="{BIG_Y}" fill="{accent}" filter="url(#{P}-glow)" opacity="0.85">{value}</text>'
                f'<text class="side c" x="{x:.0f}" y="{BIG_Y}">{value}</text>'
                f'<text class="lab c" x="{x:.0f}" y="{LAB_Y}">{label}</text>'
                f'<text class="date c" x="{x:.0f}" y="{DATE_Y}">{rng(rr)}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="GitHub streak: {m['current']} day current streak, {m['longest']} longest, {m['total']} total contributions">
  {defs_block(P)}
  {base_style()}
  <style>
    .side {{ font: 700 28px {MONO}; fill: {TEXT}; letter-spacing: -.5px; }}
    .cur {{ font: 800 38px {MONO}; fill: {TEXT}; letter-spacing: -1px; }}
    .unit {{ font: 600 8.5px {FONT}; fill: {MUTED}; letter-spacing: 2px; }}
    .lab {{ font: 700 8.5px {FONT}; fill: {MUTED}; letter-spacing: 1.4px; }}
    .clab {{ font: 800 9px {FONT}; fill: {LABEL}; letter-spacing: 1.8px; }}
    .date {{ font: 400 8.5px {MONO}; fill: {MUTED}; }}
    .c {{ text-anchor: middle; }}
  </style>
  {panel_bg(W, H, P)}
  {panel(0, ACCENT)}{panel(col, LABEL)}{panel(col*2, FIRE)}

  <g class="fade">
    {side(col*0.5, m['total'], 'TOTAL CONTRIBUTIONS', m['total_range'], ACCENT)}

    <!-- CURRENT (hero) -->
    <circle cx="{cx:.0f}" cy="{cy}" r="{r}" stroke="rgba(255,255,255,.07)" stroke-width="5"/>
    <circle class="glowpulse" cx="{cx:.0f}" cy="{cy}" r="{r}" stroke="url(#{P}-ring)" stroke-width="5"
            stroke-linecap="round" stroke-dasharray="{dash}"
            transform="rotate(-90 {cx:.0f} {cy})" filter="url(#{P}-glow)"/>
    <circle cx="{cx:.0f}" cy="{cy}" r="{r}" stroke="url(#{P}-ring)" stroke-width="2.5"
            stroke-linecap="round" stroke-dasharray="{dash}"
            transform="rotate(-90 {cx:.0f} {cy})"/>
    <path transform="translate({cx-8:.0f},{cy-r-16:.0f}) scale(0.8)" fill="{FIRE}" filter="url(#{P}-glow)" d="M9 0c.5 3-1.7 4.3-2.8 5.8C4.9 7.6 4 9.3 4 11.2 4 14.4 6.2 17 9 17s5-2.6 5-5.8c0-2.4-1.4-3.9-2.3-5.4C10.9 4.5 11 2 9 0z"/>
    <text class="cur c" x="{cx:.0f}" y="{cy+4}">{m['current']}</text>
    <text class="unit c" x="{cx:.0f}" y="{cy+20}">DAYS</text>
    <text class="clab c" x="{cx:.0f}" y="{LAB_Y}">CURRENT STREAK</text>
    <text class="date c" x="{cx:.0f}" y="{DATE_Y}">{rng(m['current_range'])}</text>

    {side(col*2.5, m['longest'], 'LONGEST STREAK', m['longest_range'], FIRE)}
  </g>
</svg>
'''


def activity_svg(days):
    items = list(days.items())[-365:]
    counts = [c for _, c in items]
    dates = [datetime.date.fromisoformat(d) for d, _ in items]
    n = len(items)
    W, H, P = 820, 260, "a"
    pad_l, pad_r, pad_t, pad_b = 44, 24, 58, 42
    plot_w, plot_h = W - pad_l - pad_r, H - pad_t - pad_b
    mx = max(max(counts), 1)

    def px(i):
        return pad_l + plot_w * i / (n - 1 if n > 1 else 1)

    def py(v):
        return pad_t + plot_h - plot_h * v / mx

    pts = [(px(i), py(c)) for i, c in enumerate(counts)]
    line = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = (f"M {pts[0][0]:.1f},{pad_t+plot_h:.1f} L "
            + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            + f" L {pts[-1][0]:.1f},{pad_t+plot_h:.1f} Z")

    peak_i = counts.index(mx)
    pkx, pky = pts[peak_i]
    endx, endy = pts[-1]

    ticks = ""
    seen = set()
    for i, dt in enumerate(dates):
        key = (dt.year, dt.month)
        if dt.day <= 7 and key not in seen:
            seen.add(key)
            x = px(i)
            ticks += (f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{pad_t+plot_h}" stroke="{MUTED}" stroke-opacity="0.10"/>'
                      f'<text x="{x:.1f}" y="{H-pad_b+20}" class="mlab">{dt.strftime("%b")}</text>')

    total = sum(counts)
    baseline = pad_t + plot_h
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="Contribution graph, peak {mx} per day, {total} contributions this year">
  {defs_block(P)}
  {base_style()}
  <style>
    .title {{ font: 800 17px {FONT}; fill: {TEXT}; letter-spacing: .2px; }}
    .sub {{ font: 400 11px {FONT}; fill: {MUTED}; }}
    .mlab {{ font: 500 10.5px {MONO}; fill: {MUTED}; text-anchor: middle; }}
    .chip {{ font: 700 10.5px {MONO}; fill: {ACCENT}; }}
    .pk {{ font: 800 11px {MONO}; fill: {FIRE}; text-anchor: middle; }}
  </style>
  {panel_bg(W, H, P)}
  <circle cx="{pad_l+4}" cy="25" r="4" fill="{ACCENT}" filter="url(#{P}-glow)"/>
  <text class="title" x="{pad_l+16}" y="30">Contribution Graph</text>
  <text class="sub" x="{pad_l+16}" y="46">last 12 months</text>
  <rect x="{W-pad_r-104:.0f}" y="17" width="104" height="20" rx="10" fill="rgba(34,211,238,.10)" stroke="rgba(34,211,238,.22)"/>
  <text class="chip" x="{W-pad_r-92:.0f}" y="31">peak {mx}/day</text>
  <g class="fade">
    <line x1="{pad_l}" y1="{baseline:.0f}" x2="{W-pad_r}" y2="{baseline:.0f}" stroke="{MUTED}" stroke-opacity="0.18"/>
    {ticks}
    <path d="{area}" fill="url(#{P}-area)"/>
    <path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="3.5" stroke-opacity="0.45" stroke-linejoin="round" filter="url(#{P}-glow)"/>
    <path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linejoin="round"/>
    <line x1="{pkx:.1f}" y1="{pky+3:.1f}" x2="{pkx:.1f}" y2="{pky-6:.1f}" stroke="{FIRE}" stroke-opacity="0.6"/>
    <circle class="glowpulse" cx="{pkx:.1f}" cy="{pky:.1f}" r="4.5" fill="{FIRE}" filter="url(#{P}-glow)"/>
    <circle cx="{pkx:.1f}" cy="{pky:.1f}" r="2.5" fill="{FIRE}"/>
    <text class="pk" x="{pkx:.1f}" y="{pky-12:.1f}">{mx}</text>
    <circle cx="{endx:.1f}" cy="{endy:.1f}" r="3.5" fill="{ACCENT}" filter="url(#{P}-glow)"/>
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
