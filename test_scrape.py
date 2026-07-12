import requests
from bs4 import BeautifulSoup
import time

def get_matches_page(team_id, team_slug):
    url = f"https://www.vlr.gg/team/matches/{team_id}/{team_slug}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (educational project; contact: your_email@example.com)"
    }
    response = requests.get(url, headers=headers)
    print(f"Fetching {url} -> status {response.status_code}")
    time.sleep(1)
    return BeautifulSoup(response.text, "html.parser")

soup = get_matches_page(624, "paper-rex")

# Target the match card class specifically
match_cards = soup.find_all("a", class_="wf-card fc-flex m-item")
print(f"Found {len(match_cards)} match cards\n")

# Print the raw text of the first 5 so we can see the structure
for i, card in enumerate(match_cards[:5]):
    print(f"--- Match {i} ---")
    print(card.get_text(separator=" | ", strip=True))
    print()