import pickle
import sqlite3
from fastapi import FastAPI
from features import calculate_win_rate, calculate_head_to_head
from datetime import date
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("model.pkl", "rb") as f:
    model = pickle.load(f)

@app.get("/predict")
def predict(team1: str, team2: str):
    conn = sqlite3.connect("matches.db")
    today = date.today().strftime("%Y/%m/%d")

    team1_overall = calculate_win_rate(team1, today, conn) or 0.5
    team2_overall = calculate_win_rate(team2, today, conn) or 0.5
    team1_recent = calculate_win_rate(team1, today, conn, last_n=10) or 0.5
    team2_recent = calculate_win_rate(team2, today, conn, last_n=10) or 0.5
    h2h_rate, h2h_count = calculate_head_to_head(team1, team2, today, conn)
    h2h_rate = h2h_rate if h2h_rate is not None else 0.5

    conn.close()

    features = [[team1_overall, team2_overall, team1_recent, team2_recent, h2h_rate, h2h_count]]
    probability = model.predict_proba(features)[0][1]

    return {
        "team1": team1,
        "team2": team2,
        "team1_win_probability": round(probability, 3)
    }