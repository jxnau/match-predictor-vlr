# Match predictor

I've created a full-stack ML app that predicts the win probability of all VCT teams if they were to go up against each other with an accuracy of 70%.
This app takes into consideration of each teams current core roster when training and testing data to derive to this accuracy. For context, other published research on pre-match esports predictions typically land between 55-71% as well.


Live site: https://matchpredictorvlr.netlify.app/
API: https://match-predictor-ml-webapp.onrender.com/docs
(The API runs on Render which goes offline when there isn't traffic so it takes awhile before the frontend is able to access the API again)

# Notes 

The logistic regression model worked better than random forest due to it's smaller dataset size.
Every feature for a match is calculated with matches that has only happened prior to the match date
Smoothing for small sample win rate teams towards neutral 0.5 baseline

## Tech-stack
Scraping: Python, 'requests' and 'BeautifulSoup4'
DTB: Sqlite
Backend: fastapi on Render
Frontend: html, css, js on Netlify
Automation: Github Actions for scheduled scraping

## Possible future improvements
Map specific win rates
Potential map draft
Elo system
