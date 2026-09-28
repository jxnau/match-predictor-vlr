import requests
from bs4 import BeautifulSoup
import re
import sys
import time
from database import setup_database
import sqlite3

# Routine runs only read each team's first page of matches (the newest ~50).
# `python scraper.py --full` pages back to FULL_SCRAPE_SINCE to rebuild the history.
FULL_SCRAPE = "--full" in sys.argv
FULL_SCRAPE_SINCE = "2023/01/01"


def get_matches_page(team_id, team_slug, page=1):
    url = f"https://www.vlr.gg/team/matches/{team_id}/{team_slug}/?page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (educational project; https://github.com/jxnau/match-predictor-ml-webapp)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        time.sleep(1)
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {team_slug}: {e}")
        return None


teams = [
    (120, "100-thieves"),
    (1119, "all-gamers"),
    (397, "bbl-esports"),
    (12010, "bilibili-gaming"),
    (188, "cloud9"),
    (278, "detonation-focusme"),
    (11981, "dragon-ranger-gaming"),
    (1120, "edward-gaming"),
    (427, "envy"),
    (6392, "eternal-fire"),
    (5248, "evil-geniuses"),
    (2593, "fnatic"),
    (4050, "full-sense"),
    (11328, "funplus-phoenix"),
    (2406, "furia"),
    (1184, "fut-esports"),
    (11058, "g2-esports"),
    (17, "gen-g"),
    (12694, "gentle-mates"),
    (14419, "giantx"),
    (918, "global-esports"),
    (13576, "jdg-esports"),
    (8877, "karmine-corp"),
    (8185, "kiwoom-drx"),
    (2355, "kr-esports"),
    (2359, "leviat-n"),
    (6961, "loud"),
    (7386, "mibr"),
    (4915, "natus-vincere"),
    (11060, "nongshim-redforce"),
    (12064, "nova-esports"),
    (1034, "nrg"),
    (624, "paper-rex"),
    (3478, "pcific-esports"),
    (878, "rex-regum-qeon"),
    (2, "sentinels"),
    (14, "t1"),
    (1001, "team-heretics"),
    (474, "team-liquid"),
    (6199, "team-secret"),
    (2059, "team-vitality"),
    (14137, "titan-esports-club"),
    (12685, "trace-esports"),
    (731, "tyloo"),
    (11229, "varrel"),
    (13790, "wolves-esports"),
    (13581, "xi-lai-gaming"),
    (5448, "zeta-division"),
]

matches = []  # empty list to collect our results based on the teams in teams lsit
seen = set()

def get_match_cards(team_id, team_slug):
    page = 1
    while True:
        soup = get_matches_page(team_id, team_slug, page)
        if soup is None:
            return
        match_cards = soup.find_all("a", class_="wf-card fc-flex m-item")
        if not match_cards:
            return
        yield from match_cards
        if not FULL_SCRAPE:
            return
        oldest = match_cards[-1].find("div", class_="m-item-date").find("div").get_text(strip=True)
        if oldest < FULL_SCRAPE_SINCE:
            return
        page += 1


for team_id, team_slug in teams:
    for card in get_match_cards(team_id, team_slug):

        match_id = re.match(r"^/(\d+)/", card.get("href", ""))
        if match_id is None:
            continue
        vlr_match_id = int(match_id.group(1))

        result_div = card.find("div", class_="m-item-result")
        if "mod-win" not in result_div.get(
            "class", []
        ) and "mod-loss" not in result_div.get("class", []):
            continue

        event = card.find("div", class_="m-item-event").find("div").get_text(strip=True)

        team_blocks = card.find_all("div", class_="m-item-team")
        team1 = (
            team_blocks[0].find("span", class_="m-item-team-name").get_text(strip=True)
        )
        team2 = (
            team_blocks[1].find("span", class_="m-item-team-name").get_text(strip=True)
        )

        team1_core_tag = team_blocks[0].find("div", class_="m-item-team-core")
        team1_core = team1_core_tag.get_text(strip=True) if team1_core_tag else None
        team2_core_tag = team_blocks[1].find("div", class_="m-item-team-core")
        team2_core = team2_core_tag.get_text(strip=True) if team2_core_tag else None

        scores = [s.get_text(strip=True) for s in result_div.find_all("span")]
        if len(scores) < 2 or not scores[0].isdigit() or not scores[1].isdigit():
            continue  # forfeits have a result but no score
        score1, score2 = int(scores[0]), int(scores[1])

        date = card.find("div", class_="m-item-date").find("div").get_text(strip=True)
        if FULL_SCRAPE and date < FULL_SCRAPE_SINCE:
            continue

        if vlr_match_id in seen:
            continue
        seen.add(vlr_match_id)

        match_data = {
            "vlr_match_id": vlr_match_id,
            "event": event,
            "team1": team1,
            "team1_score": score1,
            "team1_core": team1_core,
            "team2": team2,
            "team2_score": score2,
            "team2_core": team2_core,
            "date": date,
            "winner": team1 if score1 > score2 else team2,
        }
        matches.append(match_data)


conn = setup_database()
cursor = conn.cursor()

inserted_count = 0

print(f"Total matches found: {len(matches)} across {len(teams)} teams.")
for m in matches:
    try:
        cursor.execute(
            """
            INSERT INTO matches (vlr_match_id, event, team1, team1_score, team1_core, team2, team2_score, team2_core, date, winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                m["vlr_match_id"],
                m["event"],
                m["team1"],
                m["team1_score"],
                m["team1_core"],
                m["team2"],
                m["team2_score"],
                m["team2_core"],
                m["date"],
                m["winner"],
            ),
        )
        inserted_count += 1
    except sqlite3.IntegrityError:
        pass

conn.commit()
conn.close()
print(f"Matches inserted: {inserted_count} into the database.")

conn = sqlite3.connect("matches.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM matches LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()
