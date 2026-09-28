import re
import time
from functools import lru_cache

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (educational project; https://github.com/jxnau/match-predictor-ml-webapp)"
}

# vlr team id -> the name used in matches.db (match pages can show a different display name)
TEAM_NAMES_BY_ID = {
    120: "100 Thieves", 1119: "All Gamers", 397: "BBL Esports", 12010: "Bilibili Gaming",
    188: "Cloud9", 278: "DetonatioN FocusMe", 11981: "Dragon Ranger Gaming", 1120: "EDward Gaming",
    427: "ENVY", 6392: "Eternal Fire", 5248: "Evil Geniuses", 2593: "FNATIC", 4050: "FULL SENSE",
    11328: "FunPlus Phoenix", 2406: "FURIA", 1184: "FUT Esports", 11058: "G2 Esports", 17: "Gen.G",
    12694: "Gentle Mates", 14419: "GIANTX", 918: "Global Esports", 13576: "JDG Esports",
    8877: "Karmine Corp", 8185: "KIWOOM DRX", 2355: "KRÜ Esports", 2359: "LEVIATÁN", 6961: "LOUD",
    7386: "MIBR", 4915: "Natus Vincere", 11060: "Nongshim RedForce", 12064: "Nova Esports",
    1034: "NRG", 624: "Paper Rex", 3478: "PCIFIC Esports", 878: "Rex Regum Qeon", 2: "Sentinels",
    14: "T1", 1001: "Team Heretics", 474: "Team Liquid", 6199: "Team Secret", 2059: "Team Vitality",
    14137: "Titan Esports Club", 12685: "Trace Esports", 731: "TYLOO", 11229: "VARREL",
    13790: "Wolves Esports", 13581: "Xi Lai Gaming", 5448: "ZETA DIVISION",
}

# The /matches list only shows display names, so map the ones that differ from matches.db
NAME_ALIASES = {
    "JD Gaming": "JDG Esports",
}

KNOWN_TEAMS = set(TEAM_NAMES_BY_ID.values())


def map_win_prob(r, a=0, b=0):
    """P(team1 wins the map) given team1 has a rounds and team2 has b rounds. First to 13, win by 2."""
    tied = r * r / (r * r + (1 - r) ** 2)  # chance of winning overtime from a tied score

    @lru_cache(maxsize=None)
    def from_score(x, y):
        if x >= 13 and x - y >= 2:
            return 1.0
        if y >= 13 and y - x >= 2:
            return 0.0
        if x >= 12 and y >= 12:
            diff = x - y
            if diff == 0:
                return tied
            return r + (1 - r) * tied if diff == 1 else r * tied
        return r * from_score(x + 1, y) + (1 - r) * from_score(x, y + 1)

    return from_score(a, b)


def series_win_prob(p_map, best_of, won=0, lost=0, current_map=None):
    """P(team1 wins the series) given maps won/lost. current_map overrides the win chance of the next map."""
    need = best_of // 2 + 1

    @lru_cache(maxsize=None)
    def from_state(w, l):
        if w >= need:
            return 1.0
        if l >= need:
            return 0.0
        return p_map * from_state(w + 1, l) + (1 - p_map) * from_state(w, l + 1)

    if won >= need or lost >= need:
        return from_state(won, lost)
    q = p_map if current_map is None else current_map
    return q * from_state(won + 1, lost) + (1 - q) * from_state(won, lost + 1)


def _invert(fn, target):
    lo, hi = 1e-4, 1 - 1e-4
    target = min(max(target, lo), hi)
    for _ in range(60):
        mid = (lo + hi) / 2
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def implied_probs(p_series, best_of):
    """Back out the per-map and per-round win chances that produce the pre-match series probability."""
    p_map = _invert(lambda p: series_win_prob(p, best_of), p_series)
    p_round = _invert(map_win_prob, p_map)
    return p_map, p_round


def live_win_prob(p_series, best_of, maps):
    """maps: list of {"score1", "score2", "finished"} in play order."""
    p_map, p_round = implied_probs(p_series, best_of)
    won = sum(1 for m in maps if m["finished"] and m["score1"] > m["score2"])
    lost = sum(1 for m in maps if m["finished"] and m["score2"] > m["score1"])
    current = next((m for m in maps if not m["finished"]), None)
    current_map = map_win_prob(p_round, current["score1"], current["score2"]) if current else None
    return {
        "series": series_win_prob(p_map, best_of, won, lost, current_map),
        "current_map": current_map,
        "map_prior": p_map,
        "round_prior": p_round,
        "maps_won": [won, lost],
    }



_cache = {}


def _cached(key, ttl, fetch):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = fetch()
    _cache[key] = (now, value)
    return value


def _get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _canonical(name):
    name = NAME_ALIASES.get(name, name)
    return name if name in KNOWN_TEAMS else None


def fetch_match_list():
    """Live and upcoming matches between partnered teams, from vlr.gg/matches."""
    def fetch():
        soup = _get_soup("https://www.vlr.gg/matches")
        results = []
        for card in soup.select("a.match-item"):
            names = [n.get_text(" ", strip=True) for n in card.select(".match-item-vs-team-name .text-of")]
            if len(names) != 2:
                continue
            team1, team2 = _canonical(names[0]), _canonical(names[1])
            if team1 is None or team2 is None:
                continue
            match_id = re.match(r"^/(\d+)/", card.get("href", ""))
            if not match_id:
                continue
            status = card.select_one(".ml-status")
            event = card.select_one(".match-item-event")
            series = card.select_one(".match-item-event-series")
            series_text = series.get_text(" ", strip=True) if series else ""
            event_text = event.get_text(" ", strip=True) if event else ""
            if series_text and event_text.startswith(series_text):
                event_text = event_text[len(series_text):].strip()
            results.append({
                "match_id": int(match_id.group(1)),
                "team1": team1,
                "team2": team2,
                "status": status.get_text(strip=True).lower() if status else "",
                "event": event_text,
                "series": series_text,
            })
        # live matches first, keeping vlr's chronological order otherwise
        results.sort(key=lambda m: m["status"] != "live")
        return results

    return _cached("match_list", 60, fetch)


def _parse_score(tag):
    if tag is None:
        return None
    text = tag.get_text(strip=True)
    return int(text) if text.isdigit() else None


def _is_map_finished(a, b):
    return (a >= 13 or b >= 13) and abs(a - b) >= 2


def fetch_match(match_id):
    """Teams, format and per-map round scores for one vlr match page."""
    def fetch():
        soup = _get_soup(f"https://www.vlr.gg/{match_id}/")

        team_links = soup.select(".match-header-vs a.match-header-link")
        teams = []
        for link in team_links[:2]:
            team_id = re.match(r"^/team/(\d+)/", link.get("href", ""))
            teams.append(TEAM_NAMES_BY_ID.get(int(team_id.group(1))) if team_id else None)
        if len(teams) != 2:
            raise ValueError("Could not find both teams on the match page")

        notes = [n.get_text(" ", strip=True).lower() for n in soup.select(".match-header-vs-note")]
        best_of = 3
        for note in notes:
            found = re.search(r"bo(\d)", note)
            if found:
                best_of = int(found.group(1))
        status = "live" if any("live" in n for n in notes) else ("final" if any("final" in n for n in notes) else "upcoming")

        maps = []
        for header in soup.select(".vm-stats-game-header"):
            sides = header.select(".team")
            if len(sides) != 2:
                continue
            score1, score2 = _parse_score(sides[0].select_one(".score")), _parse_score(sides[1].select_one(".score"))
            if score1 is None or score2 is None:
                continue
            map_span = header.select_one(".map span")
            map_name = map_span.find(string=True, recursive=False) if map_span else None
            maps.append({
                "map": map_name.strip() if map_name else "",
                "score1": score1,
                "score2": score2,
                "finished": _is_map_finished(score1, score2),
            })

        
        trimmed = []
        for m in maps:
            trimmed.append(m)
            if not m["finished"]:
                break

        return {
            "match_id": match_id,
            "team1": teams[0],
            "team2": teams[1],
            "best_of": best_of,
            "status": status,
            "maps": trimmed,
        }

    return _cached(f"match_{match_id}", 30, fetch)
