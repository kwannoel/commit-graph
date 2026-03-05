# Contribution Graph Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-updating SVG line chart of GitHub contributions on a profile README.

**Architecture:** Python script fetches contribution data via `gh api graphql`, applies adaptive time bucketing, and generates a pure SVG line chart. A GitHub Actions cron job runs this daily and commits the result.

**Tech Stack:** Python 3 (stdlib only), `gh` CLI, GitHub Actions, raw SVG

---

### Task 1: Data Fetching Module

**Files:**
- Create: `generate.py`
- Create: `tests/test_generate.py`

**Step 1: Write the failing test for GraphQL query construction**

```python
# tests/test_generate.py
import json
from generate import build_query

def test_build_query_returns_valid_graphql():
    query = build_query("testuser")
    assert "contributionsCollection" in query
    assert "contributionCalendar" in query
    assert "testuser" in query
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generate.py::test_build_query_returns_valid_graphql -v`
Expected: FAIL with "cannot import name 'build_query'"

**Step 3: Write minimal implementation**

```python
# generate.py
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_generate.py::test_build_query_returns_valid_graphql -v`
Expected: PASS

**Step 5: Write the failing test for parsing API response**

```python
# tests/test_generate.py
from generate import parse_contributions

def test_parse_contributions_extracts_daily_data():
    raw = {
        "data": {
            "user": {
                "contributionsCollection": {
                    "contributionCalendar": {
                        "totalContributions": 5,
                        "weeks": [
                            {
                                "contributionDays": [
                                    {"date": "2026-01-01", "contributionCount": 3},
                                    {"date": "2026-01-02", "contributionCount": 2},
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }
    result = parse_contributions(raw)
    assert result == [("2026-01-01", 3), ("2026-01-02", 2)]
```

**Step 6: Run test to verify it fails**

Run: `python -m pytest tests/test_generate.py::test_parse_contributions_extracts_daily_data -v`
Expected: FAIL

**Step 7: Write minimal implementation**

```python
# generate.py
def parse_contributions(response: dict) -> list[tuple[str, int]]:
    calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append((day["date"], day["contributionCount"]))
    return days
```

**Step 8: Run test to verify it passes**

Run: `python -m pytest tests/test_generate.py -v`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add generate.py tests/test_generate.py
git commit -m "feat: add data fetching and parsing for contribution graph"
```

---

### Task 2: Adaptive Granularity Bucketing

**Files:**
- Modify: `generate.py`
- Modify: `tests/test_generate.py`

**Step 1: Write the failing test for daily bucketing (<=60 days)**

```python
# tests/test_generate.py
from generate import bucket_data

def test_bucket_daily_short_range():
    """30 days of data should stay as daily buckets."""
    days = [(f"2026-01-{d:02d}", d % 5) for d in range(1, 31)]
    buckets, labels = bucket_data(days)
    assert len(buckets) == 30  # one per day
    assert len(labels) <= 8  # sparse labels

def test_bucket_weekly_medium_range():
    """90 days of data should become weekly buckets."""
    from datetime import date, timedelta
    start = date(2026, 1, 1)
    days = [((start + timedelta(days=i)).isoformat(), i % 7) for i in range(90)]
    buckets, labels = bucket_data(days)
    assert 12 <= len(buckets) <= 14  # ~13 weeks
    assert len(labels) <= 8

def test_bucket_monthly_long_range():
    """365 days of data should become monthly buckets."""
    from datetime import date, timedelta
    start = date(2025, 3, 6)
    days = [((start + timedelta(days=i)).isoformat(), i % 10) for i in range(365)]
    buckets, labels = bucket_data(days)
    assert 12 <= len(buckets) <= 13  # ~12 months
    assert len(labels) <= 12
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_generate.py -k bucket -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# generate.py
from datetime import date, timedelta
from collections import defaultdict

def bucket_data(days: list[tuple[str, int]]) -> tuple[list[tuple[str, int]], list[str]]:
    """Bucket daily contribution data adaptively. Returns (buckets, label_strings)."""
    num_days = len(days)

    if num_days <= 60:
        # Daily: keep as-is
        buckets = days
        max_labels = 7
    elif num_days <= 180:
        # Weekly
        grouped = defaultdict(int)
        for date_str, count in days:
            d = date.fromisoformat(date_str)
            # Week start (Monday)
            week_start = d - timedelta(days=d.weekday())
            grouped[week_start.isoformat()] += count
        buckets = sorted(grouped.items())
        max_labels = 7
    else:
        # Monthly
        grouped = defaultdict(int)
        for date_str, count in days:
            month_key = date_str[:7]  # "YYYY-MM"
            grouped[month_key] += count
        buckets = sorted(grouped.items())
        max_labels = 12

    # Select evenly spaced label indices
    if len(buckets) <= max_labels:
        labels = [b[0] for b in buckets]
    else:
        step = (len(buckets) - 1) / (max_labels - 1)
        indices = [round(i * step) for i in range(max_labels)]
        labels = [buckets[i][0] for i in indices]

    return buckets, labels
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_generate.py -k bucket -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add generate.py tests/test_generate.py
git commit -m "feat: add adaptive granularity bucketing"
```

---

### Task 3: SVG Generation

**Files:**
- Modify: `generate.py`
- Modify: `tests/test_generate.py`

**Step 1: Write the failing test for SVG output**

```python
# tests/test_generate.py
from generate import generate_svg

def test_generate_svg_returns_valid_svg():
    buckets = [("2026-01-01", 3), ("2026-01-02", 5), ("2026-01-03", 1)]
    labels = ["Jan 1", "Jan 3"]
    svg = generate_svg(buckets, labels)
    assert svg.startswith("<svg")
    assert "viewBox" in svg
    assert "</svg>" in svg
    assert "prefers-color-scheme: dark" in svg
    assert "<polyline" in svg or "<path" in svg

def test_generate_svg_handles_zero_contributions():
    buckets = [("2026-01-01", 0), ("2026-01-02", 0)]
    labels = ["Jan 1", "Jan 2"]
    svg = generate_svg(buckets, labels)
    assert "</svg>" in svg  # should not crash
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_generate.py -k svg -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# generate.py

def _format_label(date_str: str) -> str:
    """Format a date or month string for axis display."""
    if len(date_str) == 7:  # "YYYY-MM"
        d = date.fromisoformat(date_str + "-01")
        return d.strftime("%b %y")
    d = date.fromisoformat(date_str)
    return d.strftime("%b %d")


def generate_svg(buckets: list[tuple[str, int]], labels: list[str]) -> str:
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
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_generate.py -k svg -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add generate.py tests/test_generate.py
git commit -m "feat: add SVG chart generation with dark/light theme"
```

---

### Task 4: CLI Entrypoint

**Files:**
- Modify: `generate.py`

**Step 1: Write the `main()` function and `__main__` block**

This wires everything together: calls `gh api graphql`, parses response, buckets data, generates SVG, writes to file.

```python
# generate.py — add at bottom
import subprocess
import json
import sys

def fetch_contributions() -> list[tuple[str, int]]:
    """Fetch contribution data using gh CLI."""
    # Get username
    result = subprocess.run(
        ["gh", "api", "/user", "--jq", ".login"],
        capture_output=True, text=True, check=True,
    )
    username = result.stdout.strip()

    # Fetch contributions
    query = build_query(username)
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, check=True,
    )
    response = json.loads(result.stdout)
    return parse_contributions(response)


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else "contributions.svg"
    days = fetch_contributions()
    buckets, labels = bucket_data(days)
    svg = generate_svg(buckets, labels)
    with open(output_path, "w") as f:
        f.write(svg)
    print(f"Generated {output_path} ({len(days)} days, {len(buckets)} buckets)")


if __name__ == "__main__":
    main()
```

**Step 2: Test manually**

Run: `python generate.py contributions.svg`
Expected: creates `contributions.svg` file, prints summary. Open in browser to visually verify.

**Step 3: Commit**

```bash
git add generate.py
git commit -m "feat: add CLI entrypoint for contribution graph generation"
```

---

### Task 5: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/update-graph.yml`

**Step 1: Write the workflow file**

```yaml
# .github/workflows/update-graph.yml
name: Update contribution graph

on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Generate graph
        run: python generate.py contributions.svg
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Commit and push if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add contributions.svg
          git diff --staged --quiet || git commit -m "chore: update contribution graph" && git push
```

**Step 2: Commit**

```bash
git add .github/workflows/update-graph.yml
git commit -m "feat: add GitHub Actions workflow for daily graph updates"
```

---

### Task 6: README

**Files:**
- Create: `README.md`

**Step 1: Write README**

```markdown
![Contributions](contributions.svg)
```

That's it — just the graph. The profile README should be minimal.

**Step 2: Commit**

```bash
git add README.md
git commit -m "feat: add profile README with contribution graph"
```

---

### Task 7: End-to-End Verification

**Step 1: Run the full script locally**

Run: `python generate.py contributions.svg`

**Step 2: Open the SVG in a browser to visually verify**

Run: `open contributions.svg` (macOS)

Check:
- Line chart renders correctly
- Axis labels are sparse and readable
- Toggle browser dark/light mode to verify theming

**Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 4: Final commit if any adjustments were needed**

```bash
git add -A
git commit -m "fix: adjustments from end-to-end verification"
```
