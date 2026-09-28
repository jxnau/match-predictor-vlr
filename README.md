# Match predictor

I've created a full-stack ML app that predicts the win probability of all VCT teams if they were to go up against each other, with an accuracy of ~62% on future matches.
It also has a live predictor that updates the win probability round by round while a match is being played. For context, other published research on pre-match esports predictions typically land between 55-71%.


Live site: https://matchpredictorvlr.netlify.app/
API: https://match-predictor-ml-webapp.onrender.com/docs
(The API runs on Render which goes offline when there isn't traffic so it takes awhile before the frontend is able to access the API again)

# Notes 

Predictions are based on an Elo rating for each team, built by replaying every match in date order. Beating strong teams earns more than beating weak ones, and a 2-0 counts for more than a 2-1.
A logistic regression turns the Elo difference into a win probability. It is trained on every match in both team orders, so it can't favour whichever team is listed first.
Accuracy is measured walk-forward: the model is trained only on matches before each test window and predicts the matches in it, which mirrors how it is used.
Each match is stored with vlr's match ID so it can never be counted twice. An earlier version stored some matches twice (vlr shows dates in the viewer's timezone), which leaked results into the test and inflated the reported accuracy to 70%.
The live predictor converts the pre-match probability into an implied per-map and per-round win chance, then applies it to the current score. It treats rounds as independent, so side, economy and map picks aren't factored in.

## Tech-stack
Scraping: Python, 'requests' and 'BeautifulSoup4'
DTB: Sqlite
Backend: fastapi on Render
Frontend: html, css, js on Netlify
Automation: Github Actions for scheduled scraping

## Possible future improvements
Map specific win rates
Potential map draft
Elo based on round differentials per map, rather than series results
