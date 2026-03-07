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


def test_bucket_data_trims_to_window():
    """365 days of data should be trimmed to the 6-month window."""
    from datetime import date, timedelta
    start = date(2025, 3, 7)
    days = [((start + timedelta(days=i)).isoformat(), i % 10) for i in range(365)]
    buckets, labels = bucket_data(days)
    assert len(buckets) == 182
    assert buckets[0][0] == days[-182][0]
    assert len(labels) <= 12


def test_bucket_data_short_input_unchanged():
    """Input shorter than window should pass through unchanged."""
    days = [(f"2026-01-{d:02d}", d) for d in range(1, 31)]
    buckets, labels = bucket_data(days)
    assert len(buckets) == 30


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
