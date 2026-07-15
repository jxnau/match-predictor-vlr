import requests
from bs4 import BeautifulSoup
import time
from database import setup_database
import sqlite3

def get_matches_page(team_id, team_slug):
    url = f"https://www.vlr.gg/team/matches/{team_id}/{team_slug}/"
    headers = {"User-Agent": "Mozilla/5.0 (educational project; contact: jxtanxj@gmail.com)"}
    response = requests.get(url, headers=headers)
    time.sleep(1)
    return BeautifulSoup(response.text, "html.parser")

teams = [
    (624, "paper-rex"),
    (1034, "nrg"),
    (2, "sentinels"),
    (11058, "g2-esports"),
    (2059, "team-vitality"),
    (1001, "team-heretics"),
    (2593, "fnatic"),
    (6961, "loud"),
    (17, "gen-g"),
    (14, "t1"),
    (8185, "kiwoom-drx"),
    (1120, "edward-gaming"),
    (12010, "bilibili-gaming"),
]

matches = []  # empty list to collect our results based on the teams in teams lsit
seen = set()

for team_id, team_slug in teams:
    soup = get_matches_page(team_id, team_slug)
    match_cards = soup.find_all("a", class_="wf-card fc-flex m-item")

    for card in match_cards:

        result_div = card.find("div", class_="m-item-result")
        if ("mod-win" not in result_div.get("class", []) and "mod-loss" not in result_div.get("class", [])):
            continue

        event = card.find("div", class_="m-item-event").find("div").get_text(strip=True)
        
        team_names = card.find_all("span", class_="m-item-team-name")
        team1 = team_names[0].get_text(strip=True)
        team2 = team_names[1].get_text(strip=True)
         
        scores = card.find("div", class_="m-item-result").find_all("span")
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
            "team2": team2,
            "team2_score": score2,
            "date": date,
            "winner": team1 if score1 > score2 else team2
        }
        matches.append(match_data)


conn = setup_database()
cursor = conn.cursor()

inserted_count = 0

print(f"Total matches found: {len(matches)} across {len(teams)} teams.")
for m in matches:
    try:
        cursor.execute('''
            INSERT INTO matches (event, team1, team1_score, team2, team2_score, date, winner)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (m["event"], m["team1"], m["team1_score"], m["team2"], m["team2_score"], m["date"], m["winner"]))
        inserted_count += 1
    except sqlite3.IntegrityError:
        pass

conn.commit()
conn.close()
print(f"Matches inserted: {inserted_count} into the database.")

conn = sqlite3.connect('matches.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM matches LIMIT 5')
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()