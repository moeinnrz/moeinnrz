import json
import os
import html
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

USER = "moeinnrz"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def graphql(query, variables=None):
    payload = json.dumps({
        "query": query,
        "variables": variables or {}
    }).encode()

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

    with urlopen(req, timeout=30) as response:
        data = json.load(response)

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
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }

    repositories(
      first:100,
      ownerAffiliations:OWNER,
      isFork:false
    ) {
      nodes {
        name
        stargazerCount
        languages(
          first:10,
          orderBy:{field:SIZE, direction:DESC}
        ) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""

data = graphql(query, {"login": USER})["user"]
contributions = data["contributionsCollection"]
calendar = contributions["contributionCalendar"]

# ---------------------------------------------------------
# Contribution days
# ---------------------------------------------------------

days = []

for week in calendar["weeks"]:
    days.extend(week["contributionDays"])

days.sort(key=lambda item: item["date"])

total = calendar["totalContributions"]
today = date.today()


# ---------------------------------------------------------
# Streak calculations
# ---------------------------------------------------------

def streaks(values):
    best = 0
    current = 0
    previous = None

    for item in values:
        current_date = date.fromisoformat(item["date"])
        count = item["contributionCount"]

        if count > 0:
            if previous == current_date - timedelta(days=1):
                current += 1
            else:
                current = 1

            best = max(best, current)
            previous = current_date
        else:
            current = 0
            previous = current_date

    by_date = {
        date.fromisoformat(item["date"]): item["contributionCount"]
        for item in values
    }

    # A streak may end yesterday, so use today when active,
    # otherwise start from yesterday.
    anchor = (
        today
        if by_date.get(today, 0) > 0
        else today - timedelta(days=1)
    )

    current_streak = 0

    while by_date.get(anchor, 0) > 0:
        current_streak += 1
        anchor -= timedelta(days=1)

    return current_streak, best


current_streak, longest_streak = streaks(days)


# ---------------------------------------------------------
# Monthly contribution totals
# ---------------------------------------------------------

month_totals = {}

for item in days:
    current_date = date.fromisoformat(item["date"])
    key = (current_date.year, current_date.month)

    month_totals[key] = (
        month_totals.get(key, 0)
        + item["contributionCount"]
    )


monthly = []

cursor = date(today.year, today.month, 1)

for _ in range(12):
    monthly.append({
        "label": cursor.strftime("%b %y"),
        "value": month_totals.get(
            (cursor.year, cursor.month),
            0
        ),
    })

    if cursor.month == 1:
        cursor = date(cursor.year - 1, 12, 1)
    else:
        cursor = date(
            cursor.year,
            cursor.month - 1,
            1
        )

monthly.reverse()


# ---------------------------------------------------------
# Language statistics
# ---------------------------------------------------------

languages = {}

for repo in data["repositories"]["nodes"]:
    for edge in (repo.get("languages") or {}).get("edges", []):
        name = edge["node"]["name"]
        languages[name] = languages.get(name, 0) + edge["size"]

top_languages = sorted(
    languages.items(),
    key=lambda item: item[1],
    reverse=True
)[:5]

language_total = sum(
    value for _, value in top_languages
) or 1

language_rows = [
    (name, round(value / language_total * 100))
    for name, value in top_languages
]


# ---------------------------------------------------------
# Repository statistics
# ---------------------------------------------------------

repo_count = len(data["repositories"]["nodes"])

stars = sum(
    repo.get("stargazerCount", 0)
    for repo in data["repositories"]["nodes"]
)


# ---------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------

W, H = 1200, 700

bg = "#0B0F14"
panel = "#111820"
border = "#26303B"
text = "#F0F6FC"
muted = "#8B949E"
accent = "#58A6FF"
grid = "#202832"


def esc(value):
    return html.escape(str(value), quote=True)


def text_el(
    x,
    y,
    value,
    size=14,
    fill=text,
    weight="400",
    anchor="start",
):
    return (
        f'<text x="{x}" y="{y}" '
        f'fill="{fill}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}px" '
        f'font-weight="{weight}" '
        f'text-anchor="{anchor}">'
        f'{esc(value)}</text>'
    )


def rect(
    x,
    y,
    width,
    height,
    fill=panel,
    stroke=border,
    radius=14,
):
    return (
        f'<rect x="{x}" y="{y}" '
        f'width="{width}" height="{height}" '
        f'rx="{radius}" fill="{fill}" stroke="{stroke}"/>'
    )


# ---------------------------------------------------------
# SVG document
# ---------------------------------------------------------

parts = [
    (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">'
    ),
    f'<rect width="{W}" height="{H}" rx="20" fill="{bg}"/>',

    text_el(
        42, 52,
        "GITHUB ANALYTICS",
        13, muted, "700"
    ),

    text_el(
        42, 79,
        f"@{USER}",
        22, text, "700"
    ),

    text_el(
        1158, 58,
        "LIVE DATA • GITHUB ACTIONS",
        11, muted, "400", "end"
    ),
]

# Main panels
for x, y, width, height in [
    (42, 105, 250, 105),
    (310, 105, 250, 105),
    (578, 105, 250, 105),
    (846, 105, 312, 105),
    (42, 232, 780, 420),
    (846, 232, 312, 420),
]:
    parts.append(rect(x, y, width, height))


# ---------------------------------------------------------
# Summary cards
# ---------------------------------------------------------

cards = [
    (
        42,
        "CONTRIBUTIONS",
        total,
        "last 12 months"
    ),
    (
        310,
        "CURRENT STREAK",
        current_streak,
        "days"
    ),
    (
        578,
        "LONGEST STREAK",
        longest_streak,
        "days"
    ),
    (
        846,
        "PUBLIC REPOSITORIES",
        repo_count,
        f"{stars} total stars"
    ),
]

for x, label, value, subtitle in cards:
    parts.extend([
        text_el(
            x + 18, 135,
            label,
            10, muted, "700"
        ),
        text_el(
            x + 18, 175,
            value,
            31, text, "700"
        ),
        text_el(
            x + 18, 198,
            subtitle,
            11, muted
        ),
    ])


# ---------------------------------------------------------
# Contribution trend
# ---------------------------------------------------------

parts.extend([
    text_el(
        66, 267,
        "CONTRIBUTION TREND",
        13, muted, "700"
    ),
    text_el(
        66, 292,
        "Monthly activity across the latest 12 months",
        15, text, "600"
    ),
])

cx, cy, cw, ch = 70, 325, 700, 270

max_value = max(
    [month["value"] for month in monthly] + [1]
)

for index in range(5):
    gy = cy + index * ch / 4

    parts.append(
        f'<line x1="{cx}" y1="{gy}" '
        f'x2="{cx + cw}" y2="{gy}" '
        f'stroke="{grid}" stroke-width="1"/>'
    )

    parts.append(
        text_el(
            cx - 12,
            gy + 4,
            round(max_value * (4 - index) / 4),
            10,
            muted,
            "400",
            "end",
        )
    )


points = []

for index, month in enumerate(monthly):
    x = cx + index * cw / (len(monthly) - 1)
    y = (
        cy
        + ch
        - (month["value"] / max_value) * ch
    )

    points.append((x, y, month))

    parts.append(
        text_el(
            x,
            cy + ch + 24,
            month["label"],
            10,
            muted,
            "400",
            "middle",
        )
    )


if points:
    line_path = (
        "M "
        + " L ".join(
            f"{x:.1f} {y:.1f}"
            for x, y, _ in points
        )
    )

    area_path = (
        f"M {points[0][0]:.1f} {cy + ch} L "
        + " L ".join(
            f"{x:.1f} {y:.1f}"
            for x, y, _ in points
        )
        + f" L {points[-1][0]:.1f} {cy + ch} Z"
    )

    parts.append(
        f'<path d="{area_path}" '
        f'fill="{accent}" opacity="0.10"/>'
    )

    parts.append(
        f'<path d="{line_path}" '
        f'fill="none" stroke="{accent}" '
        f'stroke-width="3" '
        f'stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
    )

    for x, y, _ in points:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" '
            f'r="4" fill="{accent}"/>'
        )


# ---------------------------------------------------------
# Language profile
# ---------------------------------------------------------

parts.extend([
    text_el(
        870, 267,
        "LANGUAGE PROFILE",
        13, muted, "700"
    ),
    text_el(
        870, 292,
        "Repository language footprint",
        15, text, "600"
    ),
])

bar_y = 335

for index, (name, percentage) in enumerate(language_rows):
    y = bar_y + index * 55

    parts.extend([
        text_el(
            870, y,
            name,
            12, text, "600"
        ),

        text_el(
            1130, y,
            f"{percentage}%",
            12, muted, "600", "end"
        ),

        (
            f'<rect x="870" y="{y + 12}" '
            f'width="260" height="8" rx="4" '
            f'fill="{grid}"/>'
        ),

        (
            f'<rect x="870" y="{y + 12}" '
            f'width="{260 * percentage / 100:.1f}" '
            f'height="8" rx="4" '
            f'fill="{accent}"/>'
        ),
    ])


if not language_rows:
    parts.append(
        text_el(
            870, 345,
            "No language data available yet.",
            12, muted
        )
    )


# ---------------------------------------------------------
# Activity mix
# ---------------------------------------------------------

activity_items = [
    (
        "COMMITS",
        contributions["totalCommitContributions"]
    ),
    (
        "ISSUES",
        contributions["totalIssueContributions"]
    ),
    (
        "PULL REQUESTS",
        contributions["totalPullRequestContributions"]
    ),
    (
        "REPOSITORY CREATIONS",
        contributions["totalRepositoryContributions"]
    ),
]

parts.append(
    text_el(
        66, 624,
        "ACTIVITY MIX",
        10, muted, "700"
    )
)

x = 150

for label, value in activity_items:
    parts.extend([
        text_el(
            x, 624,
            label,
            9, muted, "700"
        ),
        text_el(
            x, 646,
            value,
            14, text, "700"
        ),
    ])

    x += 145


# ---------------------------------------------------------
# Finish and write SVG
# ---------------------------------------------------------

parts.append("</svg>")

output_dir = Path("dist")
output_dir.mkdir(exist_ok=True)

output_file = output_dir / "github-dashboard.svg"

output_file.write_text(
    "\n".join(parts),
    encoding="utf-8"
)

print(f"Generated {output_file}")
