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

    first = dates[0] if dates else None
    last = dates[-1] if dates else None
    return {
        "total": total,
        "total_range": (first, last),
        "current": cur,
        "current_range": (c_start, c_end),
        "longest": longest,
        "longest_range": (l_start, l_end),
    }


def streak_svg(m):
    W, H = 495, 195
    col = W / 3
    cx = col * 1.5

    def rng(r):
        a, b = r
        if not a:
            return ""
        if a == b:
            return fmt_date(a)
        return f"{fmt_date(a)} - {fmt_date(b)}"

    total_rng = rng(m["total_range"])
    cur_rng = rng(m["current_range"]) or "-"
    long_rng = rng(m["longest_range"]) or "-"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="GitHub streak stats">
  <style>
    .num {{ font: 700 28px {FONT}; fill: {TEXT}; }}
    .cur-num {{ font: 700 34px {FONT}; fill: {ACCENT}; }}
    .lab {{ font: 400 14px {FONT}; fill: {MUTED}; }}
    .cur-lab {{ font: 700 14px {FONT}; fill: {LABEL}; letter-spacing: .5px; }}
    .date {{ font: 400 11px {FONT}; fill: {MUTED}; }}
    text {{ text-anchor: middle; dominant-baseline: middle; }}
  </style>
  <rect width="{W}" height="{H}" rx="6" fill="{BG}"/>
  <!-- dividers -->
  <line x1="{col:.0f}" y1="35" x2="{col:.0f}" y2="{H-35}" stroke="{MUTED}" stroke-opacity="0.25"/>
  <line x1="{col*2:.0f}" y1="35" x2="{col*2:.0f}" y2="{H-35}" stroke="{MUTED}" stroke-opacity="0.25"/>

  <!-- total (left) -->
  <text class="num" x="{col*0.5:.0f}" y="62">{m['total']}</text>
  <text class="lab" x="{col*0.5:.0f}" y="92">Total Contributions</text>
  <text class="date" x="{col*0.5:.0f}" y="140">{total_rng}</text>

  <!-- current streak (center) -->
  <circle cx="{cx:.0f}" cy="62" r="34" fill="none" stroke="{ACCENT}" stroke-width="3"/>
  <text class="cur-num" x="{cx:.0f}" y="64">{m['current']}</text>
  <text class="cur-lab" x="{cx:.0f}" y="118">Current Streak</text>
  <text class="date" x="{cx:.0f}" y="140">{cur_rng}</text>
  <!-- fire -->
  <path transform="translate({cx-9:.0f},20) scale(0.9)" fill="{FIRE}" d="M9 0c.5 3-1.7 4.3-2.8 5.8C4.9 7.6 4 9.3 4 11.2 4 14.4 6.2 17 9 17s5-2.6 5-5.8c0-2.4-1.4-3.9-2.3-5.4C10.9 4.5 11 2 9 0zm.1 16c-1.5 0-2.6-1.2-2.6-2.7 0-1.4 1-2.3 1.6-3.1.3.9 1 1.3 1.8 1.9.6.5 1.2 1.1 1.2 2 0 1.1-.8 1.9-2 1.9z"/>

  <!-- longest streak (right) -->
  <text class="num" x="{col*2.5:.0f}" y="62">{m['longest']}</text>
  <text class="lab" x="{col*2.5:.0f}" y="92">Longest Streak</text>
  <text class="date" x="{col*2.5:.0f}" y="140">{long_rng}</text>
</svg>
'''


def activity_svg(days):
    # last 365 days
    items = list(days.items())[-365:]
    counts = [c for _, c in items]
    dates = [datetime.date.fromisoformat(d) for d, _ in items]
    n = len(items)
    W, H = 820, 240
    pad_l, pad_r, pad_t, pad_b = 40, 20, 50, 40
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    mx = max(counts) if counts else 1
    mx = max(mx, 1)

    def px(i):
        return pad_l + (plot_w * i / (n - 1 if n > 1 else 1))

    def py(v):
        return pad_t + plot_h - (plot_h * v / mx)

    pts = [(px(i), py(c)) for i, c in enumerate(counts)]
    line_path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area_path = (f"M {pts[0][0]:.1f},{pad_t+plot_h:.1f} L "
                 + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                 + f" L {pts[-1][0]:.1f},{pad_t+plot_h:.1f} Z")

    # month gridlines / labels
    ticks = []
    seen = set()
    for i, dt in enumerate(dates):
        key = (dt.year, dt.month)
        if dt.day <= 7 and key not in seen:
            seen.add(key)
            ticks.append((px(i), dt.strftime("%b")))

    tick_svg = ""
    for x, lab in ticks:
        tick_svg += (f'<line x1="{x:.1f}" y1="{pad_t:.0f}" x2="{x:.1f}" y2="{pad_t+plot_h:.0f}" '
                     f'stroke="{MUTED}" stroke-opacity="0.12"/>'
                     f'<text x="{x:.1f}" y="{H-pad_b+20:.0f}" class="mlab">{lab}</text>')

    # y max label
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="Contribution graph">
  <style>
    .title {{ font: 700 16px {FONT}; fill: {TEXT}; }}
    .mlab {{ font: 400 11px {FONT}; fill: {MUTED}; text-anchor: middle; }}
    .ymax {{ font: 400 11px {FONT}; fill: {MUTED}; }}
  </style>
  <defs>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" rx="6" fill="{BG}"/>
  <text class="title" x="{pad_l}" y="28">Contribution Graph</text>
  <text class="ymax" x="{pad_l}" y="{pad_t-4}">peak {mx}/day</text>
  {tick_svg}
  <path d="{area_path}" fill="url(#area)"/>
  <path d="{line_path}" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linejoin="round"/>
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
