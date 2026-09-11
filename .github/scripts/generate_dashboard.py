import json, os, html
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

USER = "moeinnrz"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def graphql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "moeinnrz-profile-dashboard",
        },
        method="POST",
    )
    with urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


query = """
query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalRepositoryContributions
      totalContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false) {
      nodes {
        name
        stargazerCount
        languages(first:10, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

data = graphql(query, {"login": USER})["user"]
calendar = data["contributionsCollection"]["contributionCalendar"]

days = []
for week in calendar["weeks"]:
    days.extend(week["contributionDays"])
days.sort(key=lambda x: x["date"])

total = calendar["totalContributions"]
today = date.today()


def streaks(values):
    best = cur = 0
    prev = None
    for item in values:
        d = date.fromisoformat(item["date"])
        n = item["contributionCount"]
        if n > 0:
            cur = cur + 1 if prev == d - timedelta(days=1) else 1
            best = max(best, cur)
            prev = d
        else:
            cur = 0
            prev = d
    by_date = {date.fromisoformat(x["date"]): x["contributionCount"] for x in values}
    anchor = today if by_date.get(today, 0) > 0 else today - timedelta(days=1)
    current = 0
    while by_date.get(anchor, 0) > 0:
        current += 1
        anchor -= timedelta(days=1)
    return current, best


current_streak, longest_streak = streaks(days)

month_totals = {}
for item in days:
    d = date.fromisoformat(item["date"])
    key = (d.year, d.month)
    month_totals[key] = month_totals.get(key, 0) + item["contributionCount"]

monthly = []
cursor = date(today.year, today.month, 1)
for _ in range(12):
    monthly.append({"label": cursor.strftime("%b %y"), "value": month_totals.get((cursor.year, cursor.month), 0)})
    cursor = date(cursor.year - 1, 12, 1) if cursor.month == 1 else date(cursor.year, cursor.month - 1, 1)
monthly.reverse()

langs = {}
for repo in data["repositories"]["nodes"]:
    for edge in (repo.get("languages") or {}).get("edges", []):
        name = edge["node"]["name"]
        langs[name] = langs.get(name, 0) + edge["size"]
top_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:5]
lang_total = sum(v for _, v in top_langs) or 1
lang_rows = [(name, round(v / lang_total * 100)) for name, v in top_langs]

repo_count = len(data["repositories"]["nodes"])
stars = sum(r.get("stargazerCount", 0) for r in data["repositories"]["nodes"])

W, H = 1200, 700
bg, panel, border = "#0B0F14", "#111820", "#26303B"
text, muted, accent, grid = "#F0F6FC", "#8B949E", "#58A6FF", "#202832"


def esc(s):
    return html.escape(str(s), quote=True)


def text_el(x, y, s, size=14, fill=text, weight="400", anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial, Helvetica, sans-serif" font-size="{size}px" font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>'


def rect(x, y, w, h, fill=panel, stroke=border, r=14):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'


parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
    f'<rect width="{W}" height="{H}" rx="20" fill="{bg}"/>',
    text_el(42, 52, "GITHUB ANALYTICS", 13, muted, "700"),
    text_el(42, 79, f"@{USER}", 22, text, "700"),
    text_el(1158, 58, "LIVE DATA • GITHUB ACTIONS", 11, muted, "400", "end"),
]

for x, y, w, h in [(42,105,250,105),(310,105,250,105),(578,105,250,105),(846,105,312,105),(42,232,780,420),(846,232,312,420)]:
    parts.append(rect(x,y,w,h))

cards = [
    (42, "CONTRIBUTIONS", total, "last 12 months"),
    (310, "CURRENT STREAK", current_streak, "days"),
    (578, "LONGEST STREAK", longest_streak, "days"),
    (846, "PUBLIC REPOSITORIES", repo_count, f"{stars} total stars"),
]
for x, label, value, sub in cards:
    parts += [text_el(x+18,135,label,10,muted,"700"), text_el(x+18,175,value,31,text,"700"), text_el(x+18,198,sub,11,muted)]

parts += [text_el(66,267,"CONTRIBUTION TREND",13,muted,"700"),
          text_el(66,292,"Monthly activity across the latest 12 months",15,text,"600")]

cx, cy, cw, ch = 70, 325, 700, 270
maxv = max([m["value"] for m in monthly] + [1])
for i in range(5):
    gy = cy + i * ch / 4
    parts.append(f'<line x1="{cx}" y1="{gy}" x2="{cx+cw}" y2="{gy}" stroke="{grid}" stroke-width="1"/>')
    parts.append(text_el(cx-12, gy+4, round(maxv*(4-i)/4), 10, muted, "400", "end"))

points = []
for i, m in enumerate(monthly):
    x = cx + i * cw/(len(monthly)-1)
    y = cy + ch - (m["value"]/maxv)*ch
    points.append((x,y,m))
    parts.append(text_el(x, cy+ch+24, m["label"], 10, muted, "400", "middle"))

if points:
    line_d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x,y,_ in points)
    area_d = f"M {points[0][0]:.1f} {cy+ch} L " + " L ".join(f"{x:.1f} {y:.1f}" for x,y,_ in points) + f" L {points[-1][0]:.1f} {cy+ch} Z"
    parts.append(f'<path d="{area_d}" fill="{accent}" opacity="0.10"/>')
    parts.append(f'<path d="{line_d}" fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    for x,y,_ in points:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{accent}"/>')

parts += [text_el(870,267,"LANGUAGE PROFILE",13,muted,"700"),
          text_el(870,292,"Repository language footprint",15,text,"600")]

bar_y = 335
for idx, (name, pct) in enumerate(lang_rows):
    y = bar_y + idx*55
    parts += [text_el(870,y,name,12,text,"600"), text_el(1130,y,str(pct)+"%",12,muted,"600","end"),
              f'<rect x="870" y="{y+12}" width="260" height="8" rx="4" fill="{grid}"/>',
              f'<rect x="870" y="{y+12}" width="{260*pct/100:.1f}" height="8" rx="4" fill="{accent}"/>']
if not lang_rows:
    parts.append(text_el(870,345,"No language data available yet.",12,muted))

mix = data["contributionsCollection"]
mix_items = [("COMMITS",mix["totalCommitContributions"]),("ISSUES",mix["totalIssueContributions"]),("PULL REQUESTS",mix["totalPullRequestContributions"]),("REPOSITORY CREATIONS",mix["totalRepositoryContributions"])]
parts.append(text_el(66,624,"ACTIVITY MIX",10,muted,"700"))
x = 150
for label, val in mix_items:
    parts += [text_el(x,624,label,9,muted,"700"), text_el(x,646,val,14,text,"700")]
    x += 145

parts.append("</svg>")
out = Path("dist")
out.mkdir(exist_ok=True)
(out / "github-dashboard.svg").write_text("\n".join(parts), encoding="utf-8")
print("Generated", out / "github-dashboard.svg")
