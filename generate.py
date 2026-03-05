from typing import List, Tuple
from datetime import date, timedelta
from collections import defaultdict
import subprocess
import json
import sys


def build_query(username: str) -> str:
    return """
    query {
      user(login: "%s") {
        contributionsCollection {
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
      }
    }
    """ % username


def parse_contributions(response: dict) -> List[Tuple[str, int]]:
    calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append((day["date"], day["contributionCount"]))
    return days


def bucket_data(days: List[Tuple[str, int]]) -> Tuple[List[Tuple[str, int]], List[str]]:
    """Bucket daily contribution data adaptively. Returns (buckets, label_strings)."""
    num_days = len(days)

    if num_days <= 60:
        buckets = days
        max_labels = 7
    elif num_days <= 180:
        grouped = defaultdict(int)
        for date_str, count in days:
            d = date.fromisoformat(date_str)
            week_start = d - timedelta(days=d.weekday())
            grouped[week_start.isoformat()] += count
        buckets = sorted(grouped.items())
        max_labels = 7
    else:
        grouped = defaultdict(int)
        for date_str, count in days:
            month_key = date_str[:7]
            grouped[month_key] += count
        buckets = sorted(grouped.items())
        max_labels = 12

    if len(buckets) <= max_labels:
        labels = [b[0] for b in buckets]
    else:
        step = (len(buckets) - 1) / (max_labels - 1)
        indices = [round(i * step) for i in range(max_labels)]
        labels = [buckets[i][0] for i in indices]

    return buckets, labels


def _format_label(date_str: str) -> str:
    """Format a date or month string for axis display."""
    if len(date_str) == 7:  # "YYYY-MM"
        d = date.fromisoformat(date_str + "-01")
        return d.strftime("%b %y")
    d = date.fromisoformat(date_str)
    return d.strftime("%b %d")


def generate_svg(buckets: List[Tuple[str, int]], labels: List[str]) -> str:
    width, height = 800, 250
    margin = {"top": 20, "right": 20, "bottom": 40, "left": 50}
    chart_w = width - margin["left"] - margin["right"]
    chart_h = height - margin["top"] - margin["bottom"]

    counts = [c for _, c in buckets]
    max_count = max(counts) if counts and max(counts) > 0 else 1

    # Map data to coordinates
    points = []
    for i, (_, count) in enumerate(buckets):
        x = margin["left"] + (i / max(len(buckets) - 1, 1)) * chart_w
        y = margin["top"] + chart_h - (count / max_count) * chart_h
        points.append((x, y))

    # Build polyline points string
    points_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    # Build filled area (close path along bottom)
    area_points = points_str
    if points:
        area_points += f" {points[-1][0]:.1f},{margin['top'] + chart_h:.1f}"
        area_points += f" {points[0][0]:.1f},{margin['top'] + chart_h:.1f}"

    # Y-axis labels (0 and max)
    y_labels_svg = ""
    y_labels_svg += (
        f'<text x="{margin["left"] - 8}" y="{margin["top"] + chart_h}" '
        f'text-anchor="end" class="axis-label">0</text>'
    )
    y_labels_svg += (
        f'<text x="{margin["left"] - 8}" y="{margin["top"] + 4}" '
        f'text-anchor="end" class="axis-label">{max_count}</text>'
    )

    # X-axis labels
    x_labels_svg = ""
    label_set = set(labels)
    for i, (date_str, _) in enumerate(buckets):
        if date_str in label_set:
            x = margin["left"] + (i / max(len(buckets) - 1, 1)) * chart_w
            formatted = _format_label(date_str)
            x_labels_svg += (
                f'<text x="{x:.1f}" y="{height - 8}" '
                f'text-anchor="middle" class="axis-label">{formatted}</text>'
            )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%">
  <style>
    .line {{ fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
    .area {{ opacity: 0.15; }}
    .axis-label {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 11px; }}
    .axis-line {{ stroke-width: 1; }}

    @media (prefers-color-scheme: dark) {{
      .line {{ stroke: #58a6ff; }}
      .area {{ fill: #58a6ff; }}
      .axis-label {{ fill: #8b949e; }}
      .axis-line {{ stroke: #30363d; }}
    }}
    @media (prefers-color-scheme: light) {{
      .line {{ stroke: #0969da; }}
      .area {{ fill: #0969da; }}
      .axis-label {{ fill: #57606a; }}
      .axis-line {{ stroke: #d0d7de; }}
    }}
  </style>

  <!-- Axes -->
  <line class="axis-line" x1="{margin['left']}" y1="{margin['top']}" x2="{margin['left']}" y2="{margin['top'] + chart_h}" />
  <line class="axis-line" x1="{margin['left']}" y1="{margin['top'] + chart_h}" x2="{margin['left'] + chart_w}" y2="{margin['top'] + chart_h}" />

  <!-- Area fill -->
  <polygon class="area" points="{area_points}" />

  <!-- Line -->
  <polyline class="line" points="{points_str}" />

  <!-- Labels -->
  {y_labels_svg}
  {x_labels_svg}
</svg>"""

    return svg


def fetch_contributions(username: str) -> List[Tuple[str, int]]:
    """Fetch contribution data using gh CLI."""
    query = build_query(username)
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, check=True,
    )
    response = json.loads(result.stdout)
    return parse_contributions(response)


def main():
    if len(sys.argv) < 2:
        print("Usage: generate.py <username> [output_path]", file=sys.stderr)
        sys.exit(1)
    username = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "contributions.svg"
    days = fetch_contributions(username)
    buckets, labels = bucket_data(days)
    svg = generate_svg(buckets, labels)
    with open(output_path, "w") as f:
        f.write(svg)
    print(f"Generated {output_path} ({len(days)} days, {len(buckets)} buckets)")


if __name__ == "__main__":
    main()
