from __future__ import annotations

from src.pages.base_page import BasePage

class LoginPage(BasePage):
    EMAIL_INPUTS = [
        'input[type="email"]',
        'input[name="email"]',
        'input[name="pseudonym_session[unique_id]"]',
    ]

    PASSWORD_INPUTS = [
        'input[type="password"]',
        'input[name="password"]',
        'input[name="pseudonym_session[password]"]',
    ]

    LOGIN_BUTTONS = [
        'button[type="submit"]',
        'input[type="submit"]',
    ]

    def login(self, login_url: str, email: str, password: str) -> None:
        self.goto(login_url)

        email_filled = False
        for selector in self.EMAIL_INPUTS:
            if self.page.locator(selector).count() > 0:
                self.fill(selector, email)
                email_filled = True
                break

        if not email_filled:
            raise RuntimeError("No email input found on login page.")

        password_filled = False
        for selector in self.PASSWORD_INPUTS:
            if self.page.locator(selector).count() > 0:
                self.fill(selector, password)
                password_filled = True
                break

        if not password_filled:
            raise RuntimeError("No password input found on login page.")

        clicked = False
        for selector in self.LOGIN_BUTTONS:
            if self.page.locator(selector).count() > 0:
                self.click(selector)
                clicked = True
                break

        if not clicked:
            raise RuntimeError("No login button found on login page.")

        self.page.wait_for_load_state("networkidle")