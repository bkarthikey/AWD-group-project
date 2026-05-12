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


@pytest.fixture(scope="module")
def browser():
    try:
        driver = webdriver.Safari()
    except (PermissionError, WebDriverException) as exc:
        pytest.skip(f"Safari WebDriver is not available or not enabled: {exc}")

    driver.set_window_size(1280, 900)
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


def test_user_can_signup_and_reach_dashboard(browser, live_server):
    browser.get(f"{live_server}/signup")

    browser.find_element(By.NAME, "username").send_keys("SeleniumNova")
    browser.find_element(By.NAME, "email").send_keys("selenium@example.com")
    browser.find_element(By.NAME, "password").send_keys("password123")
    browser.find_element(By.NAME, "confirm_password").send_keys("password123")
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

    assert "Top 10 Colonies" in browser.page_source
    assert "Leaderboard" in browser.title
