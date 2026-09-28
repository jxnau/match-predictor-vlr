import sqlite3

def get_team_matches(team_name, before_date, conn, core=None):
    cursor = conn.cursor()
    if core is not None:
        cursor.execute("""
            SELECT team1, team2, winner, date FROM matches
            WHERE ((team1 = ? AND team1_core = ?) OR (team2 = ? AND team2_core = ?)) AND date < ?
            ORDER BY date
        """, (team_name, core, team_name, core, before_date))
    else:
        cursor.execute("""
            SELECT team1, team2, winner, date FROM matches
            WHERE (team1 = ? OR team2 = ?) AND date < ?
            ORDER BY date
        """, (team_name, team_name, before_date))
    return cursor.fetchall()


def get_current_core(team_name, before_date, conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team1_core, team2_core, team1, team2 FROM matches
        WHERE (team1 = ? OR team2 = ?) AND date < ?
        ORDER BY date DESC LIMIT 1
    """, (team_name, team_name, before_date))
    row = cursor.fetchone()
    if row is None:
        return None
    team1_core, team2_core, team1, team2 = row
    return team1_core if team1 == team_name else team2_core


def calculate_win_rate(team_name, before_date, conn, last_n=None, prior_weight=5, core=None):
    matches = get_team_matches(team_name, before_date, conn, core=core)

    if last_n is not None:
        matches = matches[-last_n:]

    if len(matches) == 0:
        return None

    wins = sum(1 for match in matches if match[2] == team_name)
    total = len(matches)

    smoothed_rate = (wins + prior_weight * 0.5) / (total + prior_weight)
    return smoothed_rate


def calculate_head_to_head(team1, team2, before_date, conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT winner FROM matches
        WHERE ((team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?)) AND date < ?
    """, (team1, team2, team2, team1, before_date))
    results = cursor.fetchall()

    if len(results) == 0:
        return None, 0  # no prior meetings

    team1_wins = sum(1 for r in results if r[0] == team1)
    h2h_rate = team1_wins / len(results)
    return h2h_rate, len(results)


ELO_K = 48
ELO_START = 1500


def elo_history(conn, k=ELO_K):
    """Replay every match in date order and track each team's Elo rating.

    Returns (matches, pre_match, ratings, games): pre_match[i] is (team1_elo, team2_elo) going into
    matches[i], ratings is every team's rating after the last match, and games[team] is how many
    matches that team has played.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team1, team2, winner, date, team1_score, team2_score FROM matches
        ORDER BY date, id
    """)
    matches = cursor.fetchall()

    ratings = {}
    games = {}
    pre_match = []
    for team1, team2, winner, date, score1, score2 in matches:
        elo1 = ratings.get(team1, ELO_START)
        elo2 = ratings.get(team2, ELO_START)
        pre_match.append((elo1, elo2, games.get(team1, 0), games.get(team2, 0)))

        expected = 1 / (1 + 10 ** ((elo2 - elo1) / 400))
        result = 1.0 if winner == team1 else 0.0
        # a 2-0 moves ratings more than a 2-1
        margin = 1 + abs(score1 - score2) / max(score1 + score2, 1)
        change = k * margin * (result - expected)
        ratings[team1] = elo1 + change
        ratings[team2] = elo2 - change
        games[team1] = games.get(team1, 0) + 1
        games[team2] = games.get(team2, 0) + 1

    return matches, pre_match, ratings, games


def elo_feature(elo1, elo2):
    return [(elo1 - elo2) / 400]


def build_training_data(conn):
    """One row per match, in date order, using only what was known before the match was played."""
    matches, pre_match, _, _ = elo_history(conn)

    training_rows = []
    for (team1, team2, winner, date, _, _), (elo1, elo2, games1, games2) in zip(matches, pre_match):
        # skip a team's first match: its rating is still the 1500 starting value
        if games1 == 0 or games2 == 0:
            continue
        training_rows.append({
            "date": date,
            "features": elo_feature(elo1, elo2),
            "team1_won": 1 if winner == team1 else 0,
        })

    return training_rows


if __name__ == "__main__":
    conn = sqlite3.connect("matches.db")
    data = build_training_data(conn)
    print(f"Built {len(data)} training rows")
    print("First 5 rows:")
    for row in data[:5]:
        print(row)
    conn.close()