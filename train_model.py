import sqlite3
import pickle
from features import build_training_data
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


def with_swapped(X, y):
    # add every match again with the teams swapped, so the model can't favour either slot
    return X + [[-x[0]] for x in X], y + [1 - label for label in y]


def fit(X, y):
    X, y = with_swapped(X, y)
    # no intercept: with equal ratings the prediction must be exactly 50%
    return LogisticRegression(fit_intercept=False).fit(X, y)


conn = sqlite3.connect("matches.db")
data = build_training_data(conn)
conn.close()

X = [row["features"] for row in data]
y = [row["team1_won"] for row in data]

# Walk-forward test: for each of 5 windows covering the newest half of the matches, train on
# everything before the window and predict the window. This mirrors real use (predicting the
# future from the past) and gives a larger, less noisy test than a single split.
n = len(X)
bounds = [int(n * f) for f in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
probabilities, actual = [], []
for start, end in zip(bounds, bounds[1:]):
    model = fit(X[:start], y[:start])
    probabilities += list(model.predict_proba(X[start:end])[:, 1])
    actual += y[start:end]

correct = sum((p > 0.5) == label for p, label in zip(probabilities, actual))
print(f"Walk-forward accuracy: {correct / len(actual):.2%} on {len(actual)} matches")
print(f"Brier score: {brier_score_loss(actual, probabilities):.4f} (always guessing 50% scores 0.2500)")

# Final model: train on every match
model = fit(X, y)
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)
print(f"Model saved to model.pkl (trained on {n} matches)")
