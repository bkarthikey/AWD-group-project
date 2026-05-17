"""
End-to-end browser tests against a live in-process Flask server.

Requires a local browser + matching WebDriver. Selenium 4.6+ bundles Selenium
Manager, which resolves Chrome / Edge / Firefox drivers automatically when the
browser is installed.

Optional: set SELENIUM_BROWSER to one of chrome, edge, firefox, safari to use
only that driver (otherwise the first working driver in the default order is
used: chrome, edge, firefox, safari).
"""

import os
import secrets
import socket
import threading
import time

import pytest
from werkzeug.serving import make_server

from app import create_app
from app.extensions import db
from config import TestConfig

selenium = pytest.importorskip("selenium")
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ServerThread(threading.Thread):
    def __init__(self, app, port):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", port, app)
        self.app = app

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


@pytest.fixture(scope="module")
def live_server():
    app = create_app(TestConfig)
    port = find_free_port()

    with app.app_context():
        db.create_all()

    server = ServerThread(app, port)
    server.start()
    time.sleep(0.3)

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


def _webdriver_factories():
    """Return ordered (label, callable) pairs for WebDriver startup."""
    pref = (os.environ.get("SELENIUM_BROWSER") or "").strip().lower()
    all_factories = [
        ("chrome", webdriver.Chrome),
        ("edge", webdriver.Edge),
        ("firefox", webdriver.Firefox),
        ("safari", webdriver.Safari),
    ]
    if pref:
        by_label = dict(all_factories)
        if pref not in by_label:
            pytest.skip(
                f"Unknown SELENIUM_BROWSER={pref!r}. Use one of: "
                f"{', '.join(by_label)}."
            )
        return [(pref, by_label[pref])]
    return all_factories


@pytest.fixture(scope="module")
def browser():
    errors = []
    driver = None

    for label, factory in _webdriver_factories():
        try:
            driver = factory()
            break
        except (WebDriverException, PermissionError, OSError) as exc:
            msg = str(exc).strip() or repr(exc)
            if len(msg) > 240:
                msg = msg[:237] + "..."
            errors.append(f"{label}: {msg}")

    if driver is None:
        tried = ", ".join(label for label, _ in _webdriver_factories())
        pytest.skip(
            "No WebDriver could be started (tried: "
            f"{tried}). Install Chrome, Edge, or Firefox, or on macOS run "
            "`safaridriver --enable` for Safari. Optional: set SELENIUM_BROWSER "
            f"to force one browser. Errors: {' | '.join(errors)}"
        )

    driver.set_window_size(1280, 900)
    driver.implicitly_wait(0)
    yield driver
    driver.quit()


def test_landing_page_loads(browser, live_server):
    browser.get(f"{live_server}/")

    assert "Space Colony" in browser.title
    assert "Explore. Mine. Build your colony." in browser.page_source


def test_signup_page_loads(browser, live_server):
    browser.get(f"{live_server}/signup")

    assert "Create colony" in browser.page_source
    assert browser.find_element(By.NAME, "username")
    assert browser.find_element(By.NAME, "email")


def test_login_page_loads(browser, live_server):
    browser.get(f"{live_server}/login")

    assert "Welcome back" in browser.page_source
    assert browser.find_element(By.NAME, "email")
    assert browser.find_element(By.NAME, "password")


def _random_signup_credentials():
    """Unique commander + email + password per run (RegisterForm: username ≥3, password ≥8)."""
    token = secrets.token_hex(5)
    username = f"cmd{token}"
    email = f"selenium.{token}@example.com"
    password = secrets.token_urlsafe(16)
    return username, email, password


def test_user_can_signup_and_reach_dashboard(browser, live_server):
    browser.get(f"{live_server}/signup")

    username, email, password = _random_signup_credentials()
    browser.find_element(By.NAME, "username").send_keys(username)
    browser.find_element(By.NAME, "email").send_keys(email)
    browser.find_element(By.NAME, "password").send_keys(password)
    browser.find_element(By.NAME, "confirm_password").send_keys(password)
    browser.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()

    WebDriverWait(browser, 5).until(EC.url_contains("/dashboard"))
    assert "Colony Status" in browser.page_source


def test_discussion_board_page_loads(browser, live_server):
    browser.get(f"{live_server}/discussion")

    assert "Discussion Board" in browser.page_source
    assert "Create post" in browser.page_source
    assert "Reward exchange" in browser.page_source


def test_leaderboard_page_loads(browser, live_server):
    browser.get(f"{live_server}/leaderboard")

    assert "Top 15 Colonies" in browser.page_source
    assert "Leaderboard" in browser.title
