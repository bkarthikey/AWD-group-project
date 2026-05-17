# Space Colony Builder

A Flask web application prototype for the CITS3403/CITS5505 group project.

## Concept

Space Colony Builder is an alien planet survival clicker game.  
Players click and hold on the planet surface to make a small astronaut explore, dig and collect resources such as oxygen, water, and minerals. These resources can later be used to build colony extractors that automatically generate resources over time.

## Team members

- 24444964 - Suraj Kumar Vijay Kumar - `surajkumar1818`
- UWA ID - Name - `github-username`
- UWA ID - Name - `github-username`

## Current pages

- `index.html` - landing page
- `/login` - login page
- `/signup` - signup page
- `/dashboard` - main game-style dashboard
- `/discussion` - colony community and reward exchange page
- `/leaderboard` - top players page
- `/profile/<username>` - public/private colony profile view

## How to run

```bash
python -m pip install -r requirements.txt
flask --app run.py db upgrade
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

Run only the backend/unit tests:

```bash
python -m pytest -q tests/test_models.py tests/test_game_api.py tests/test_auth_pages.py tests/test_discussion.py
```

Run Selenium browser tests (live Flask server in-process + real browser):

```bash
python -m pytest -q tests/test_selenium.py
```

The tests try **Chrome**, then **Edge**, then **Firefox**, then **Safari** (Selenium Manager supplies matching drivers when the browser is installed). On Windows or Linux, install one of Chrome, Edge, or Firefox so at least one driver can start.

To force a specific browser:

```bash
set SELENIUM_BROWSER=chrome
python -m pytest -q tests/test_selenium.py
```

(On PowerShell use `$env:SELENIUM_BROWSER="chrome"` before the same pytest command.)

On macOS, if you rely on Safari only, enable its driver first:

```bash
safaridriver --enable
```

## Database migrations

This project uses Flask-Migrate/Alembic for database migrations.

Create a migration after model changes:

```bash
flask --app run.py db migrate -m "Describe schema change"
```

Apply migrations:

```bash
flask --app run.py db upgrade
```

The older development helper is still available if needed:

```bash
flask --app run.py init-db
```

## Implemented backend foundation

- Flask app factory and routes
- Jinja templates for main pages
- user registration/login/logout
- SQLite + SQLAlchemy models for users, colonies, upgrades and events
- discussion models for posts, comments, and reward exchanges
- discussion screenshot uploads for colony images
- saved resource totals and upgrade levels through backend API routes
- server-side passive extractor income applied from saved upgrade levels
- leaderboard using database values
- CSRF protection and password hashing
- Flask-Migrate/Alembic database migration setup

## CSS Framework

This prototype uses Bootstrap 5 through the CDN for the required CSS framework, with custom CSS layered on top for the sci-fi game interface.
