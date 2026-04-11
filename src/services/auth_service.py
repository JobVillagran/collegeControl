from __future__ import annotations

from playwright.sync_api import Page
from config.settings import CANVAS_LOGIN_URL, CANVAS_EMAIL, CANVAS_PASSWORD
from src.pages.login_page import LoginPage

class AuthService:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.login_page = LoginPage(page)

    def login(self) -> None:
        self.login_page.login(
            login_url=CANVAS_LOGIN_URL,
            email=CANVAS_EMAIL,
            password=CANVAS_PASSWORD,
        )