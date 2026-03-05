from typing import List, Tuple


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
