import sqlite3
conn = sqlite3.connect("matches.db")
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT team1 FROM matches UNION SELECT DISTINCT team2 FROM matches")
actual_names = sorted([row[0] for row in cursor.fetchall()])
conn.close()

for name in actual_names:
    print(name)