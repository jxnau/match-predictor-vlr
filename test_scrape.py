import requests
from bs4 import BeautifulSoup
import time

def get_matches_page(team_id, team_slug):
    url = f"https://www.vlr.gg/team/matches/{team_id}/{team_slug}/"
    headers = {"User-Agent": "Mozilla/5.0 (educational project; contact: jxtanxj@gmail.com)"}
    response = requests.get(url, headers=headers)
    time.sleep(1)
    return BeautifulSoup(response.text, "html.parser")

soup = get_matches_page(624, "paper-rex")
match_cards = soup.find_all("a", class_="wf-card fc-flex m-item")

matches = []  # empty list to collect our clean results

for card in match_cards:
    event = card.find("div", class_="m-item-event").find("div").get_text(strip=True)
    
    team_names = card.find_all("span", class_="m-item-team-name")
    team1 = team_names[0].get_text(strip=True)
    team2 = team_names[1].get_text(strip=True)
    
    scores = card.find("div", class_="m-item-result").find_all("span")
    score1 = scores[0].get_text(strip=True)
    score2 = scores[1].get_text(strip=True)
    
    date = card.find("div", class_="m-item-date").find("div").get_text(strip=True)
    
    match_data = {
        "event": event,
        "team1": team1,
        "team1_score": score1,
        "team2": team2,
        "team2_score": score2,
        "date": date
    }
    matches.append(match_data)



for m in matches[:5]:
    print(m)