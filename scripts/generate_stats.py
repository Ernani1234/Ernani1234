"""Generate animated GitHub stats cards (SVG) for the profile README.

Runs inside GitHub Actions with the default GITHUB_TOKEN and only the
standard library, so the profile does not depend on third-party card
services that go offline or hit rate limits.

Usage:
    GITHUB_TOKEN=... python scripts/generate_stats.py --user Ernani1234 --out dist
    python scripts/generate_stats.py --demo --out dist   # offline preview
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

# Markup/docs formats inflate byte counts without reflecting code written.
IGNORED_LANGUAGES = {"HTML", "CSS", "SCSS", "TeX", "Batchfile", "Jupyter Notebook", "Makefile", "Dockerfile"}
IGNORED_REPOS = {"Ernani1234"}
TOP_LANGUAGES = 6

BG = "#0D1117"
CARD_STROKE = "#30363D"
TEXT = "#E6EDF3"
MUTED = "#8B949E"
ACCENT = "#00D9FF"
ACCENT_2 = "#8B5CF6"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'Cascadia Code', 'Fira Code', Consolas, monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch(user: str, token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def demo_data() -> dict:
    rng = random.Random(7)
    start = dt.date.today() - dt.timedelta(days=364)
    weeks, week = [], []
    for i in range(365):
        day = start + dt.timedelta(days=i)
        week.append({"date": day.isoformat(), "contributionCount": rng.choice([0, 0, 1, 2, 3, 5, 8])})
        if len(week) == 7:
            weeks.append({"contributionDays": week})
            week = []
    if week:
        weeks.append({"contributionDays": week})
    langs = [("Python", "#3572A5", 590000), ("TypeScript", "#3178c6", 474000), ("Rust", "#dea584", 255000),
             ("JavaScript", "#f1e05a", 355000), ("SQL", "#e38c00", 1000)]
    return {
        "followers": {"totalCount": 4},
        "pullRequests": {"totalCount": 12},
        "contributionsCollection": {
            "totalCommitContributions": 420,
            "restrictedContributionsCount": 0,
            "contributionCalendar": {"totalContributions": 612, "weeks": weeks},
        },
        "repositories": {
            "totalCount": 12,
            "nodes": [{"name": "demo", "stargazerCount": 1, "languages": {"edges": [
                {"size": s, "node": {"name": n, "color": c}} for n, c, s in langs]}}],
        },
    }


def streaks(days: list[dict]) -> tuple[int, int]:
    counts = [d["contributionCount"] for d in sorted(days, key=lambda d: d["date"])]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    # Today may not have contributions yet; the streak is still alive.
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    current = 0
    while i >= 0 and counts[i]:
        current += 1
        i -= 1
    return current, longest


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


STYLE = f"""
  <style>
    .t {{ font-family: {FONT}; }}
    .m {{ font-family: {MONO}; }}
    .in {{ opacity: 0; animation: in .6s ease-out forwards; }}
    @keyframes in {{ from {{ opacity: 0; transform: translateX(-8px) }} to {{ opacity: 1; transform: none }} }}
    .grow {{ transform-box: fill-box; transform-origin: bottom; transform: scaleY(0); animation: gy .6s cubic-bezier(.2,.8,.2,1) forwards; }}
    @keyframes gy {{ to {{ transform: scaleY(1) }} }}
    .growx {{ transform-box: fill-box; transform-origin: left; transform: scaleX(0); animation: gx 1s cubic-bezier(.2,.8,.2,1) forwards; }}
    @keyframes gx {{ to {{ transform: scaleX(1) }} }}
    .ring {{ animation: ring 1.6s ease-out .3s forwards; }}
    @keyframes ring {{ to {{ stroke-dashoffset: var(--to) }} }}
    .flame {{ transform-box: fill-box; transform-origin: bottom; animation: flame 1.4s ease-in-out infinite; }}
    @keyframes flame {{ 0%,100% {{ transform: scale(1) }} 50% {{ transform: scale(1.12, .92) }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important }} .in {{ opacity: 1 }} .grow, .growx {{ transform: none }} .ring {{ stroke-dashoffset: var(--to) }} }}
  </style>"""


def card(width: int, height: int, title: str, body: str, label: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">
  <title>{escape(label)}</title>
  <defs>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity=".55"/>
      <stop offset=".5" stop-color="{CARD_STROKE}"/>
      <stop offset="1" stop-color="{ACCENT_2}" stop-opacity=".55"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="{ACCENT_2}"/>
      <stop offset="1" stop-color="{ACCENT}"/>
    </linearGradient>
  </defs>{STYLE}
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" fill="{BG}" stroke="url(#edge)" stroke-width="1.5"/>
  <text x="26" y="40" class="t" font-size="17" font-weight="700" fill="{TEXT}">{escape(title)}</text>
{body}
</svg>
"""


def stats_card(user: dict) -> str:
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)
    repos = user["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"] if r["name"] not in IGNORED_REPOS)
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    metrics = [
        ("Contribuições (12 meses)", cal["totalContributions"], ACCENT),
        ("Commits (12 meses)", commits, "#7EE787"),
        ("Pull requests", user["pullRequests"]["totalCount"], "#D2A8FF"),
        ("Repositórios públicos", repos["totalCount"], "#FFD866"),
        ("Estrelas recebidas", stars, "#F5A97F"),
    ]
    rows = []
    for i, (label, value, color) in enumerate(metrics):
        y = 76 + i * 26
        rows.append(
            f'  <g class="in t" style="animation-delay:{0.15 + i * 0.12:.2f}s">'
            f'<circle cx="32" cy="{y - 5}" r="4" fill="{color}"/>'
            f'<text x="46" y="{y}" font-size="14" fill="{MUTED}">{escape(label)}</text>'
            f'<text x="290" y="{y}" text-anchor="end" class="m" font-size="15" font-weight="700" fill="{TEXT}">{fmt(value)}</text></g>'
        )

    # Streak ring: fill proportional to current/longest.
    circ = 2 * 3.14159 * 46
    ratio = current / longest if longest else 0
    offset = circ * (1 - ratio)
    ring = f"""  <g transform="translate(400 118)">
    <circle r="46" fill="none" stroke="#21262D" stroke-width="8"/>
    <circle class="ring" r="46" fill="none" stroke="url(#accent)" stroke-width="8" stroke-linecap="round"
      stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}" style="--to:{offset:.1f}" transform="rotate(-90)"/>
    <path class="flame" d="M0 -30c6 7 9 12 9 17a9 9 0 0 1-18 0c0-4 2-7 4-9c0 4 2 6 4 6c0-5-1-9 1-14z" fill="#F5A97F"/>
    <text y="16" text-anchor="middle" class="t" font-size="26" font-weight="800" fill="{TEXT}">{current}</text>
    <text y="32" text-anchor="middle" class="t" font-size="10" fill="{MUTED}">dias seguidos</text>
  </g>
  <text x="400" y="190" text-anchor="middle" class="t in" style="animation-delay:.9s" font-size="12" fill="{MUTED}">recorde: <tspan class="m" fill="{TEXT}" font-weight="700">{longest}</tspan> dias</text>"""

    # Weekly activity bars for the last 52 weeks.
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]][-52:]
    peak = max(weekly) or 1
    bar_w, gap, x0, base, max_h = 6.5, 2, 26, 262, 42
    bars = []
    for i, v in enumerate(weekly):
        h = max(2, v / peak * max_h)
        bars.append(
            f'<rect class="grow" style="animation-delay:{0.4 + i * 0.018:.3f}s" x="{x0 + i * (bar_w + gap):.1f}" y="{base - h:.1f}" '
            f'width="{bar_w}" height="{h:.1f}" rx="2" fill="url(#accent)" fill-opacity="{0.35 + 0.65 * v / peak:.2f}"/>'
        )
    chart = (
        f'  <text x="26" y="{base - max_h - 6}" class="t" font-size="11" fill="{MUTED}">atividade semanal · últimas 52 semanas</text>\n'
        f'  <g>{"".join(bars)}</g>'
    )
    body = "\n".join(rows) + "\n" + ring + "\n" + chart
    label = (f"Estatísticas do GitHub: {cal['totalContributions']} contribuições no último ano, "
             f"sequência atual de {current} dias, recorde de {longest} dias")
    return card(495, 280, "Atividade no GitHub", body, label)


def languages_card(user: dict) -> str:
    totals: dict[str, int] = {}
    colors: dict[str, str] = {}
    for repo in user["repositories"]["nodes"]:
        if repo["name"] in IGNORED_REPOS:
            continue
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in IGNORED_LANGUAGES:
                continue
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or MUTED
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:TOP_LANGUAGES]
    rest = sum(v for _, v in ranked[TOP_LANGUAGES:])
    if rest:
        top.append(("Outras", rest))
        colors["Outras"] = "#484F58"
    grand = sum(v for _, v in top) or 1

    # Stacked bar
    segs, x = [], 26.0
    full = 443.0
    for i, (name, size) in enumerate(top):
        w = size / grand * full
        segs.append(f'<rect class="growx" style="animation-delay:{0.1 + i * 0.12:.2f}s" x="{x:.1f}" y="60" width="{max(w, 0.1):.1f}" height="10" fill="{colors[name]}"/>')
        x += w
    stacked = (f'  <clipPath id="bar"><rect x="26" y="60" width="{full}" height="10" rx="5"/></clipPath>\n'
               f'  <rect x="26" y="60" width="{full}" height="10" rx="5" fill="#21262D"/>\n'
               f'  <g clip-path="url(#bar)">{"".join(segs)}</g>')

    rows = []
    for i, (name, size) in enumerate(top):
        pct = size / grand * 100
        y = 104 + i * 25
        w = max(2.0, pct / 100 * 210)
        rows.append(
            f'  <g class="in t" style="animation-delay:{0.3 + i * 0.1:.2f}s">'
            f'<circle cx="32" cy="{y - 5}" r="5" fill="{colors[name]}"/>'
            f'<text x="46" y="{y}" font-size="14" fill="{TEXT}">{escape(name)}</text>'
            f'<rect x="190" y="{y - 10}" width="210" height="6" rx="3" fill="#21262D"/>'
            f'<rect class="growx" style="animation-delay:{0.5 + i * 0.1:.2f}s" x="190" y="{y - 10}" width="{w:.1f}" height="6" rx="3" fill="{colors[name]}"/>'
            f'<text x="469" y="{y}" text-anchor="end" class="m" font-size="13" fill="{MUTED}">{pct:.1f}%</text></g>'
        )
    body = stacked + "\n" + "\n".join(rows)
    label = "Linguagens mais usadas: " + ", ".join(f"{n} {s / grand * 100:.0f}%" for n, s in top)
    return card(495, 280, "Linguagens mais usadas", body, label)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "Ernani1234"))
    ap.add_argument("--out", default="dist")
    ap.add_argument("--demo", action="store_true", help="render with fake data, no network")
    args = ap.parse_args()

    if args.demo:
        user = demo_data()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is required (or pass --demo)")
        user = fetch(args.user, token)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.svg").write_text(stats_card(user), encoding="utf-8")
    (out / "languages.svg").write_text(languages_card(user), encoding="utf-8")
    print(f"wrote {out / 'stats.svg'} and {out / 'languages.svg'}")


if __name__ == "__main__":
    main()
