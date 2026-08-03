import sqlite3
import pickle
from features import build_training_data
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

conn = sqlite3.connect("matches.db")
data = build_training_data(conn)
conn.close()

X = [[
    row["team1_overall_winrate"],
    row["team2_overall_winrate"],
    row["team1_recent_winrate"],
    row["team2_recent_winrate"],
    row["h2h_winrate"],
    row["h2h_matches"]
] for row in data]
y = [row["team1_won"] for row in data]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LogisticRegression()
model.fit(X_train, y_train)
accuracy = model.score(X_test, y_test)
print(f"Model accuracy on test data: {accuracy:.2%}")

# Save the trained model to a file
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)
print("Model saved to model.pkl")