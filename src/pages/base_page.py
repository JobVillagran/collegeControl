from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def goto(self, url: str) -> None:
        self.page.goto(url, wait_until="networkidle")

    def click(self, selector: str) -> None:
        self.page.locator(selector).click()

    def fill(self, selector: str, value: str) -> None:
        self.page.locator(selector).fill(value)

    def text(self, selector: str) -> str:
        return self.page.locator(selector).inner_text().strip()

    def exists(self, selector: str, timeout: int = 3000) -> bool:
        try:
            self.page.locator(selector).wait_for(timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False