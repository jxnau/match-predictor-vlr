import requests
from bs4 import BeautifulSoup
import time
from database import setup_database
import sqlite3


def get_matches_page(team_id, team_slug):
    url = f"https://www.vlr.gg/team/matches/{team_id}/{team_slug}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (educational project; contact: jxtanxj@gmail.com)"
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

for team_id, team_slug in teams:
    soup = get_matches_page(team_id, team_slug)
    if soup is None:
        continue
    match_cards = soup.find_all("a", class_="wf-card fc-flex m-item")

    for card in match_cards:

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

        scores = result_div.find_all("span")
        score1 = int(scores[0].get_text(strip=True))
        score2 = int(scores[1].get_text(strip=True))

        date = card.find("div", class_="m-item-date").find("div").get_text(strip=True)

        match_key = tuple(sorted([team1, team2]) + [date])
        if match_key in seen:
            continue
        seen.add(match_key)

        match_data = {
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
            INSERT INTO matches (event, team1, team1_score, team1_core, team2, team2_score, team2_core, date, winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
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
