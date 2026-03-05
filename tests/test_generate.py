import json
from generate import build_query, parse_contributions


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
