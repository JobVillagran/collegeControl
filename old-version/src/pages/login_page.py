from __future__ import annotations

from pages.base_page import BasePage


class LoginPage(BasePage):
    EMAIL_INPUTS = [
        'input[type="email"]',
        'input[name="identifier"]',
        'input[name="email"]',
        'input[name="pseudonym_session[unique_id]"]',
        'input[autocomplete="username"]',
    ]

    PASSWORD_INPUTS = [
        'input[autocomplete="current-password"]',
        'input[name="Passwd"]',
        'input[name="password"]',
        'input[name="pseudonym_session[password]"]',
        'input[type="password"]:not([aria-hidden="true"])',
    ]

    NEXT_BUTTONS = [
        'button:has-text("Next")',
        'button:has-text("Siguiente")',
        '#identifierNext',
        'div[role="button"]:has-text("Next")',
        'div[role="button"]:has-text("Siguiente")',
        'input[type="button"][value="Next"]',
        'input[type="button"][value="Siguiente"]',
    ]

    LOGIN_BUTTONS = [
        'button[type="submit"]',
        'input[type="submit"]',
        '#passwordNext',
        'button:has-text("Log in")',
        'button:has-text("Login")',
        'button:has-text("Iniciar sesión")',
        'button:has-text("Sign in")',
        'div[role="button"]:has-text("Next")',
        'div[role="button"]:has-text("Siguiente")',
    ]

    POST_LOGIN_INDICATORS = [
        'a[href*="/courses/"]',
        'a[href*="/dashboard"]',
        'nav',
        '#DashboardCard_Container',
        '[data-testid="k5-dashboard-card-hero"]',
    ]

    def login(self, login_url: str, email: str, password: str) -> None:
        try:
            self.goto(login_url)

            # Paso 1: correo
            self.fill_first_visible(self.EMAIL_INPUTS, email)

            # Si hay botón intermedio de "Next", lo usa
            if self._has_any_visible(self.NEXT_BUTTONS, timeout=4000):
                self.click_first_visible(self.NEXT_BUTTONS)

            # Paso 2: esperar password visible real
            self.wait_for_any_visible(self.PASSWORD_INPUTS, timeout=20000)
            self.fill_first_visible(self.PASSWORD_INPUTS, password)

            # Paso 3: submit / next
            self.click_first_visible(self.LOGIN_BUTTONS)

            # Paso 4: esperar navegación post-login
            self.page.wait_for_load_state("networkidle")
            self._wait_for_post_login()

        except Exception:
            self.save_screenshot("login_failure.png")
            raise

    def _has_any_visible(self, selectors: list[str], timeout: int = 3000) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector)
            count = locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    candidate.wait_for(state="visible", timeout=timeout)
                    return True
                except Exception:
                    continue
        return False

    def _wait_for_post_login(self) -> None:
        for selector in self.POST_LOGIN_INDICATORS:
            locator = self.page.locator(selector)
            count = locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    candidate.wait_for(state="visible", timeout=5000)
                    return
                except Exception:
                    continue