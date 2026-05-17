# Space Colony Builder

## Purpose, design, and use

**Space Colony Builder** is a web application for the UWA Agile Web Development project. It is an **alien-planet survival clicker**: players sign in, manage a **colony** on a dashboard, and **click or drag** on the planet to harvest **oxygen, water, and minerals**. Resources feed **extractor upgrades** that generate passive income over time, **missions**, **achievements**, and a **colony score** used for ranking.

**Design:** The app uses **Flask** with **Jinja2** templates, a **dark sci-fi** visual theme (custom CSS plus Bootstrap 5 from the CDN), and a **clear navigation flow**—landing page → sign up or log in → dashboard as the main game hub, with links to **discussion** (community posts, comments, screenshot uploads, and **resource exchanges**), **leaderboard** (top public colonies), and **profile** (account, visibility, security, and colony stats). Game state is **persisted in SQLite** via **SQLAlchemy**; the browser talks to **JSON APIs** for collecting resources, upgrades, and live colony data.

**Use:** New users **register** and receive a colony. They **play on the dashboard**, optionally **upgrade extractors** on a dedicated page, **join the discussion board** to share strategies or trade resources, and may set their profile **public** to appear on the **leaderboard**. Passwords are stored securely; forms use **CSRF** protection.

---

## Group members

| UWA ID   | Name                         | GitHub username   |
|----------|------------------------------|-------------------|
| 24444964 | Suraj Kumar Vijay Kumar      | surajkumar1818    |
| 24701183 | Karthikeya Bezwada           | bkarthikeya       |
| 24104733 | Muhammad Hamza Khalid        | Hamza-portfolio   |

---

## How to launch the application

1. **Clone** this repository and open a terminal in the project root.

2. **Create a virtual environment** (recommended) and install dependencies:

   ```bash
   python -m venv .venv
   ```

   Activate it:

   - **Windows (cmd):** `.venv\Scripts\activate.bat`
   - **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
   - **macOS / Linux:** `source .venv/bin/activate`

   Then:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Configure environment variables** (optional for local dev; required for production):

   - `SECRET_KEY` — Flask secret (defaults to a dev value in `config.py` if unset).
   - `DATABASE_URL` — SQLAlchemy URI (defaults to `sqlite:///space_colony.db` in the project folder if unset).

4. **Apply database migrations** so the schema matches the models:

   ```bash
   flask --app run.py db upgrade
   ```

5. **Run the development server:**

   ```bash
   python run.py
   ```

6. Open a browser at **http://127.0.0.1:5000/**

**Note:** If you only need an empty database without migration history, you can use `flask --app run.py init-db` instead of `db upgrade` for a quick local setup (migrations are the supported path for the unit).

---

## How to run the tests

**Full test suite** (unit/API tests and Selenium if a browser is available):

```bash
python -m pytest -q
```

**Unit and API tests only** (no browser; faster CI-style run):

```bash
python -m pytest -q tests/test_models.py tests/test_game_api.py tests/test_auth_pages.py tests/test_discussion.py
```

**Selenium end-to-end tests** (in-process **live** Flask server + real browser; six tests):

```bash
python -m pytest -q tests/test_selenium.py
```

Selenium tries **Chrome**, then **Edge**, then **Firefox**, then **Safari**. Install at least one of those browsers on your machine. Selenium 4’s **Selenium Manager** resolves drivers automatically when possible.

To force one browser:

- **cmd:** `set SELENIUM_BROWSER=chrome` then run pytest as above.
- **PowerShell:** `$env:SELENIUM_BROWSER="chrome"` then run pytest.

On **macOS** with Safari only, run `safaridriver --enable` once.

---

## Main routes and pages

| Area            | Route / page              | Description                                      |
|-----------------|---------------------------|--------------------------------------------------|
| Landing         | `/`                       | Project introduction and entry points            |
| Auth            | `/signup`, `/login`       | Registration and login                           |
| Game            | `/dashboard`              | Main clicker gameplay and colony HUD             |
| Upgrades        | `/upgrades`               | Spend resources on extractors                    |
| Community       | `/discussion`            | Posts, comments, images, resource exchanges      |
| Rankings        | `/leaderboard`            | Top public colonies by score                     |
| Profile         | `/profile/<username>`    | Commander and colony profile; owner can edit     |

---

## Database migrations

This project uses **Flask-Migrate** (Alembic). After model changes:

```bash
flask --app run.py db migrate -m "Describe schema change"
flask --app run.py db upgrade
```

---

## Tech stack (summary)

- **Backend:** Flask, Flask-Login, Flask-WTF (CSRF), Flask-Migrate, SQLAlchemy  
- **Frontend:** Jinja2, Bootstrap 5 (CDN), custom CSS and JavaScript  
- **Database:** SQLite by default (`space_colony.db` in the project root unless `DATABASE_URL` is set)
