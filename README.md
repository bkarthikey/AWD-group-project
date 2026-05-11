# Space Colony Builder

A Flask web application prototype for the CITS3403/CITS5505 group project.

## Concept

Space Colony Builder is an alien planet survival clicker game.  
Players click and hold on the planet surface to make a small astronaut explore, dig, and collect resources such as oxygen, water, and minerals. These resources can later be used to build colony extractors that automatically generate resources over time.

## Current pages

- `index.html` — landing page
- `/login` — login page
- `/signup` — signup page
- `/dashboard` — main game-style dashboard
- `/upgrades` — extractor upgrade page
- `/leaderboard` — top players page
- `/profile/<username>` — public/private colony profile view

## How to run

```bash
python -m pip install -r requirements.txt
flask --app run.py init-db
python run.py
```

Then open:

```text
http://127.0.0.1:5000/
```

## How to run tests

```bash
python -m pytest -q
```

## Implemented backend foundation

- Flask app factory and routes
- Jinja templates for main pages
- user registration/login/logout
- SQLite + SQLAlchemy models for users, colonies, upgrades, and events
- saved resource totals and upgrade levels through backend API routes
- leaderboard using database values
- CSRF protection and password hashing

## CSS Framework

This prototype uses Bootstrap 5 through the CDN for the required CSS framework, with custom CSS layered on top for the sci-fi game interface.
