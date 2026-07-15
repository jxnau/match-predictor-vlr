import sqlite3

def setup_database():
    conn = sqlite3.connect('matches.db')
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS matches (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       event TEXT,
                       team1 TEXT,
                       team1_score INTEGER,
                       team2 TEXT,
                       team2_score INTEGER,
                       date TEXT,
                       winner TEXT,
                       UNIQUE(team1, team2, date)
                    )
                   ''')
    
    conn.commit()
    return conn