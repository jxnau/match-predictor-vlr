import sqlite3
conn = sqlite3.connect("matches.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM matches WHERE team1_core IS NULL OR team2_core IS NULL")
print("Rows missing core data:", cursor.fetchone())
cursor.execute("SELECT COUNT(*) FROM matches")
print("Total rows:", cursor.fetchone())
conn.close()