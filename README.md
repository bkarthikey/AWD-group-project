# Space Colony Builder — Frontend Prototype

A static frontend prototype for the CITS3403/CITS5505 group project.

## Concept

Space Colony Builder is an alien planet survival clicker game.  
Players click and hold on the planet surface to make a small astronaut explore, dig, and collect resources such as oxygen, water, and minerals. These resources can later be used to build colony extractors that automatically generate resources over time.

## Current frontend pages

- `index.html` — landing page
- `login.html` — login mockup
- `signup.html` — signup mockup
- `dashboard.html` — main game-style dashboard
- `upgrades.html` — extractor upgrade page
- `leaderboard.html` — top players page
- `profile.html` — public colony profile
- `profile-private.html` — private profile view

## How to run

Open `index.html` in a browser, or use the VS Code Live Server extension.

## Planned backend features

- Flask routes
- user registration/login/logout
- SQLite + SQLAlchemy database
- saved resource totals and upgrade levels
- public/private colony setting
- leaderboard using real database values
- CSRF protection and password hashing

## CSS Framework

This prototype uses Bootstrap 5 through the CDN for the required CSS framework, with custom CSS layered on top for the sci-fi game interface.
