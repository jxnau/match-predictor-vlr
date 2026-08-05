import requests
from bs4 import BeautifulSoup
import time

def get_teams_from_event(event_id, event_slug):
    url = f"https://www.vlr.gg/event/{event_id}/{event_slug}"
    headers = {"User-Agent": "Mozilla/5.0 (educational project; contact: jxtanxj@gmail.com)"}
    response = requests.get(url, headers=headers)
    time.sleep(1)
    soup = BeautifulSoup(response.text, "html.parser")

    teams = set()
    team_links = soup.find_all("a", href=True)
    for link in team_links:
        href = link["href"]
        if href.startswith("/team/") and href.count("/") >= 3:
            parts = href.strip("/").split("/")
            team_id = int(parts[1])
            team_slug = parts[2]
            teams.add((team_id, team_slug))

    return teams

events = [
    (2860, "vct-2026-americas-stage-1/group-stage"),
    (2775, "vct-2026-pacific-stage-1/group-stage"),
    (2863, "vct-2026-emea-stage-1/group-stage"),
    (2864, "vct-2026-china-stage-1/group-stage"),
]

all_teams = set()
for event_id, event_slug in events:
    all_teams.update(get_teams_from_event(event_id, event_slug))

print(f"Found {len(all_teams)} unique teams")
for team in sorted(all_teams, key=lambda t: t[1]):
    print(team)