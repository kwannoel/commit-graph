from typing import List, Tuple
from datetime import date, timedelta
from collections import defaultdict


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
