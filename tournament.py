import random
import re

from live import TEAM_NAMES_BY_ID, _cached, _get_soup, implied_probs, series_win_prob

# Valorant Champions 2026. Change this for the next event (the id is in the vlr.gg event URL).
DEFAULT_EVENT_ID = 2766
SIMULATIONS = 10000

# 8-team double-elimination playoff, as used by VCT Masters and Champions.
# Each match takes its two teams from earlier matches: ("W", m) = winner of m, ("L", m) = loser of m.
# Listed in the order matches are played, so sources are always decided before they're needed.
BRACKET = [
    ("UQF1", None, None),
    ("UQF2", None, None),
    ("UQF3", None, None),
    ("UQF4", None, None),
    ("USF1", ("W", "UQF1"), ("W", "UQF2")),
    ("USF2", ("W", "UQF3"), ("W", "UQF4")),
    ("LR1_1", ("L", "UQF1"), ("L", "UQF2")),
    ("LR1_2", ("L", "UQF3"), ("L", "UQF4")),
    # upper semifinal losers drop to the opposite side of the lower bracket to avoid rematches
    ("LR2_1", ("W", "LR1_1"), ("L", "USF2")),
    ("LR2_2", ("W", "LR1_2"), ("L", "USF1")),
    ("UF", ("W", "USF1"), ("W", "USF2")),
    ("LR3", ("W", "LR2_1"), ("W", "LR2_2")),
    ("LF", ("L", "UF"), ("W", "LR3")),
    ("GF", ("W", "UF"), ("W", "LF")),
]
BEST_OF = {"LF": 5, "GF": 5}  # everything else is Bo3

# vlr column label -> our match keys, top to bottom
COLUMNS = {
    "Upper Quarterfinals": ["UQF1", "UQF2", "UQF3", "UQF4"],
    "Upper Semifinals": ["USF1", "USF2"],
    "Upper Final": ["UF"],
    "Grand Final": ["GF"],
    "Lower Round 1": ["LR1_1", "LR1_2"],
    "Lower Round 2": ["LR2_1", "LR2_2"],
    "Lower Round 3": ["LR3"],
    "Lower Final": ["LF"],
}


def fetch_bracket(event_id):
    """Teams and results for every playoff match on the vlr.gg event page."""
    def fetch():
        soup = _get_soup(f"https://www.vlr.gg/event/{event_id}/")
        title = soup.select_one("h1")
        matches = {}
        for col in soup.select(".bracket-container .bracket-col"):
            label = col.select_one(".bracket-col-label")
            keys = COLUMNS.get(label.get_text(" ", strip=True) if label else "")
            if keys is None:
                continue
            items = col.select(".bracket-item")
            if len(items) != len(keys):
                raise ValueError("This event's playoff bracket isn't the supported 8-team double elimination format")
            for key, item in zip(keys, items):
                teams, winner = [], None
                for side in item.select(".bracket-item-team"):
                    name = side.select_one(".bracket-item-team-name span")
                    team_id = side.get("data-team-id", "")
                    team = TEAM_NAMES_BY_ID.get(int(team_id)) if team_id.isdigit() else None
                    team = team or (name.get_text(strip=True) if name else "")
                    teams.append(team or None)
                    if "mod-winner" in side.get("class", []):
                        winner = team
                matches[key] = {"teams": teams, "winner": winner}

        missing = [key for key, _, _ in BRACKET if key not in matches]
        if missing:
            raise ValueError("Couldn't find this event's playoff bracket on vlr.gg")
        if not all(all(matches[key]["teams"]) for key in COLUMNS["Upper Quarterfinals"]):
            raise ValueError("The playoff teams for this event aren't decided yet")
        return {"event": title.get_text(" ", strip=True) if title else f"Event {event_id}", "matches": matches}

    return _cached(f"bracket_{event_id}", 60, fetch)


def simulate(bracket, predict, simulations=SIMULATIONS, seed=None):
    """Play out the rest of the bracket many times using the model's odds.

    predict(team1, team2) -> team1's chance of winning a Bo3. Finished matches keep their real result.
    """
    rng = random.Random(seed)
    matches = bracket["matches"]
    teams = sorted({t for key in ("UQF1", "UQF2", "UQF3", "UQF4") for t in matches[key]["teams"] if t})

    # odds for every pairing and format, worked out once up front
    odds = {}
    for a in teams:
        for b in teams:
            if a < b:
                p_bo3 = predict(a, b)
                p_map, _ = implied_probs(p_bo3, 3)
                odds[(a, b, 3)] = p_bo3
                odds[(a, b, 5)] = series_win_prob(p_map, 5)

    def chance(a, b, best_of):
        return odds[(a, b, best_of)] if a < b else 1 - odds[(b, a, best_of)]

    champion = dict.fromkeys(teams, 0)
    finalist = dict.fromkeys(teams, 0)
    for _ in range(simulations):
        result = {}
        for key, source_a, source_b in BRACKET:
            real = matches[key]
            if all(real["teams"]):
                a, b = real["teams"]  # vlr already knows who plays here
            else:
                a = result[source_a[1]][source_a[0]]
                b = result[source_b[1]][source_b[0]]
            if real["winner"] in (a, b):
                winner = real["winner"]
            else:
                winner = a if rng.random() < chance(a, b, BEST_OF.get(key, 3)) else b
            result[key] = {"W": winner, "L": b if winner == a else a}
        champion[result["GF"]["W"]] += 1
        finalist[result["GF"]["W"]] += 1
        finalist[result["GF"]["L"]] += 1

    standings = [
        {
            "team": team,
            "champion_probability": round(champion[team] / simulations, 3),
            "grand_final_probability": round(finalist[team] / simulations, 3),
        }
        for team in teams
    ]
    standings.sort(key=lambda s: (-s["champion_probability"], -s["grand_final_probability"]))
    return standings


def tournament_odds(predict, event_id=DEFAULT_EVENT_ID):
    bracket = fetch_bracket(event_id)
    played = sum(1 for m in bracket["matches"].values() if m["winner"])
    return {
        "event_id": event_id,
        "event": re.sub(r"\s+", " ", bracket["event"]),
        "matches_played": played,
        "matches_total": len(BRACKET),
        "simulations": SIMULATIONS,
        # fixed seed: the same bracket always gives the same numbers, so they don't jitter on refresh
        "standings": simulate(bracket, predict, seed=0),
    }
