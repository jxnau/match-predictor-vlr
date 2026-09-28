import sqlite3

def setup_database():
    conn = sqlite3.connect('matches.db')
    cursor = conn.cursor()

    # vlr_match_id is vlr's own id for the match, so the same match can never be stored twice
    # (dates alone aren't safe: vlr shows them in the viewer's timezone)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS matches (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       vlr_match_id INTEGER UNIQUE,
                       event TEXT,
                       team1 TEXT,
                       team1_score INTEGER,
                       team1_core TEXT,
                       team2 TEXT,
                       team2_score INTEGER,
                       team2_core TEXT,
                       date TEXT,
                       winner TEXT
                    )
                   ''')

    conn.commit()
    return conn
