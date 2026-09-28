import pickle
import sqlite3
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, HTTPException
from features import calculate_win_rate, calculate_head_to_head
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
from features import calculate_win_rate, calculate_head_to_head, get_current_core
from live import fetch_match_list, fetch_match, live_win_prob
import requests

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://matchpredictorvlr.netlify.app", "http://127.0.0.1:5500"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

with open("model.pkl", "rb") as f:
    model = pickle.load(f)

@app.get("/predict")
@limiter.limit("20/minute")
def predict(request: Request,team1: str, team2: str):

    if team1 not in PARTNERED_TEAMS or team2 not in PARTNERED_TEAMS:
        raise HTTPException(status_code=400, detail="One or both teams are not partnered teams.")
    if team1 == team2:
        raise HTTPException(status_code=400, detail="Team names must be different.")

    return pre_match_prediction(team1, team2)


def pre_match_prediction(team1, team2):
    conn = sqlite3.connect("matches.db")
    today = date.today().strftime("%Y/%m/%d")
    
    team1_core = get_current_core(team1, today, conn)
    team2_core = get_current_core(team2, today, conn)

    team1_overall = calculate_win_rate(team1, today, conn, core=team1_core) or 0.5
    team2_overall = calculate_win_rate(team2, today, conn, core=team2_core) or 0.5
    team1_recent = calculate_win_rate(team1, today, conn, last_n=10, core=team1_core) or 0.5
    team2_recent = calculate_win_rate(team2, today, conn, last_n=10, core=team2_core) or 0.5
    h2h_rate, h2h_count = calculate_head_to_head(team1, team2, today, conn)
    h2h_rate = h2h_rate if h2h_rate is not None else 0.5

    conn.close()

    features = [[team1_overall, team2_overall, team1_recent, team2_recent, h2h_rate, h2h_count]]
    probability = model.predict_proba(features)[0][1]

    return {
        "team1": team1,
        "team2": team2,
        "team1_win_probability": round(probability, 3),
        "stats": {
            "team1_overall_winrate": round(team1_overall, 3),
            "team2_overall_winrate": round(team2_overall, 3),
            "team1_recent_winrate": round(team1_recent, 3),
            "team2_recent_winrate": round(team2_recent, 3),
            "h2h_team1_winrate": round(h2h_rate, 3),
            "h2h_matches_played": h2h_count
        }
    }
    
PARTNERED_TEAMS = [
    "100 Thieves", "All Gamers", "BBL Esports", "Bilibili Gaming", "Cloud9",
    "DetonatioN FocusMe", "Dragon Ranger Gaming", "EDward Gaming", "ENVY",
    "Eternal Fire", "Evil Geniuses", "FNATIC", "FULL SENSE", "FunPlus Phoenix",
    "FURIA", "FUT Esports", "G2 Esports", "Gen.G", "Gentle Mates", "GIANTX",
    "Global Esports", "JDG Esports", "Karmine Corp", "KIWOOM DRX", "KRÜ Esports",
    "LEVIATÁN", "LOUD", "MIBR", "Natus Vincere", "Nongshim RedForce", "Nova Esports",
    "NRG", "Paper Rex", "PCIFIC Esports", "Rex Regum Qeon", "Sentinels", "T1",
    "Team Heretics", "Team Liquid", "Team Secret", "Team Vitality",
    "Titan Esports Club", "Trace Esports", "TYLOO", "VARREL", "Wolves Esports",
    "Xi Lai Gaming", "ZETA DIVISION",
]

@app.get("/teams")
@limiter.limit("10/minute")
def get_teams(request: Request):
    return sorted(PARTNERED_TEAMS)


@app.get("/live/matches")
@limiter.limit("20/minute")
def live_matches(request: Request):
    try:
        return fetch_match_list()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Couldn't reach vlr.gg.")


@app.get("/live/{match_id}")
@limiter.limit("30/minute")
def live_match(request: Request, match_id: int):
    try:
        match = fetch_match(match_id)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Couldn't reach vlr.gg.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if match["team1"] is None or match["team2"] is None:
        raise HTTPException(status_code=400, detail="This match isn't between two partnered teams.")

    pre_match = pre_match_prediction(match["team1"], match["team2"])
    p_series = pre_match["team1_win_probability"]
    live = live_win_prob(p_series, match["best_of"], match["maps"])

    return {
        **match,
        "pre_match_win_probability": p_series,
        "live_win_probability": round(live["series"], 3),
        "current_map_win_probability": round(live["current_map"], 3) if live["current_map"] is not None else None,
        "maps_won": live["maps_won"],
        "implied_map_win_probability": round(live["map_prior"], 3),
        "implied_round_win_probability": round(live["round_prior"], 3),
        "stats": pre_match["stats"],
    }