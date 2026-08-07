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


def build_training_data(conn, recent_n=10):
    cursor = conn.cursor()
    cursor.execute("SELECT team1, team2, winner, date, team1_core, team2_core FROM matches ORDER BY date")
    all_matches = cursor.fetchall()

    training_rows = []

    for team1, team2, winner, date, team1_core, team2_core in all_matches:
        team1_overall = calculate_win_rate(team1, date, conn, core=team1_core)
        team2_overall = calculate_win_rate(team2, date, conn, core=team2_core)
        team1_recent = calculate_win_rate(team1, date, conn, last_n=recent_n, core=team1_core)
        team2_recent = calculate_win_rate(team2, date, conn, last_n=recent_n, core=team2_core)
        h2h_rate, h2h_count = calculate_head_to_head(team1, team2, date, conn)

        if team1_overall is None or team2_overall is None:
            continue

        training_rows.append({
            "team1_overall_winrate": team1_overall,
            "team2_overall_winrate": team2_overall,
            "team1_recent_winrate": team1_recent,
            "team2_recent_winrate": team2_recent,
            "h2h_winrate": h2h_rate if h2h_rate is not None else 0.5,
            "h2h_matches": h2h_count,
            "team1_won": 1 if winner == team1 else 0
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