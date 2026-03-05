from generate import build_query, parse_contributions, bucket_data, generate_svg


def test_build_query_returns_valid_graphql():
    query = build_query("testuser")
    assert "contributionsCollection" in query
    assert "contributionCalendar" in query
    assert "testuser" in query


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
                        ],
                    }
                }
            }
        }
    }
    result = parse_contributions(raw)
    assert result == [("2026-01-01", 3), ("2026-01-02", 2)]


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


def test_generate_svg_returns_valid_svg():
    buckets = [("2026-01-01", 3), ("2026-01-02", 5), ("2026-01-03", 1)]
    labels = ["2026-01-01", "2026-01-03"]
    svg = generate_svg(buckets, labels)
    assert svg.startswith("<svg")
    assert "viewBox" in svg
    assert "</svg>" in svg
    assert "prefers-color-scheme: dark" in svg
    assert "<polyline" in svg or "<path" in svg


def test_generate_svg_handles_zero_contributions():
    buckets = [("2026-01-01", 0), ("2026-01-02", 0)]
    labels = ["2026-01-01", "2026-01-02"]
    svg = generate_svg(buckets, labels)
    assert "</svg>" in svg  # should not crash
