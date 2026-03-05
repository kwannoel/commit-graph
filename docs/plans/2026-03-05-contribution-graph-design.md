# GitHub Profile Contribution Graph

## Goal

Auto-updating 2D line chart of GitHub contributions displayed on the user's profile README. Y-axis: commits, X-axis: timestamp. Minimal axis labels, adaptive granularity, dark/light theme support.

## Approach

Pure SVG generation — no charting libraries. A Python script generates the SVG directly, giving pixel-perfect control over styling.

## Components

### 1. `generate.py`

- Fetches contribution data via `gh api graphql` (subprocess call)
- Queries `contributionsCollection.contributionCalendar` for daily contribution counts (past year)
- Applies adaptive granularity:
  - <= 60 days: daily buckets, ~6-8 axis labels
  - 61-180 days: weekly buckets, ~6-8 axis labels
  - > 180 days: monthly buckets, ~6-12 axis labels
- Generates an SVG line chart:
  - Fixed viewBox (800x250), scales responsively
  - `<polyline>` or `<path>` for the line
  - Subtle filled area under the line
  - Minimal axis: thin lines, sparse labels, no gridlines
  - CSS `prefers-color-scheme` media query for dark (light line/text) and light (dark line/text) on transparent background

### 2. `.github/workflows/update-graph.yml`

- Cron: `0 0 * * *` (daily)
- Manual trigger: `workflow_dispatch`
- Steps: checkout -> setup python -> run `generate.py` -> commit & push SVG if changed
- Uses `GITHUB_TOKEN` via `gh` CLI (no extra secrets needed)

### 3. `README.md`

- References the generated SVG image

## Constraints

- Zero external Python dependencies (stdlib only + `gh` CLI)
- No hardcoded username — derived from `gh api /user` or repo context
- Max ~6-12 axis labels regardless of granularity to avoid crowding
