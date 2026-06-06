from __future__ import annotations

from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def goto(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def click(self, selector: str, timeout: int = 10000) -> None:
        self.page.locator(selector).first.click(timeout=timeout)

    def fill(self, selector: str, value: str, timeout: int = 10000) -> None:
        self.page.locator(selector).first.fill(value, timeout=timeout)

    def exists(self, selector: str, timeout: int = 3000) -> bool:
        try:
            self.page.locator(selector).first.wait_for(state="attached", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def is_visible(self, selector: str, timeout: int = 3000) -> bool:
        try:
            self.page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def click_first_visible(self, selectors: list[str], timeout: int = 10000) -> str:
        for selector in selectors:
            locator = self.page.locator(selector)
            count = locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    candidate.wait_for(state="visible", timeout=1500)
                    candidate.click(timeout=timeout)
                    return selector
                except Exception:
                    continue
        raise RuntimeError(f"No visible clickable selector found from: {selectors}")

    def fill_first_visible(self, selectors: list[str], value: str, timeout: int = 10000) -> str:
        for selector in selectors:
            locator = self.page.locator(selector)
            count = locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    candidate.wait_for(state="visible", timeout=1500)
                    candidate.fill(value, timeout=timeout)
                    return selector
                except Exception:
                    continue
        raise RuntimeError(f"No visible fillable selector found from: {selectors}")

    def wait_for_any_visible(self, selectors: list[str], timeout: int = 10000) -> str:
        for selector in selectors:
            locator = self.page.locator(selector)
            count = locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    candidate.wait_for(state="visible", timeout=1500)
                    return selector
                except Exception:
                    continue
        raise RuntimeError(f"No visible selector found from: {selectors}")

    def save_screenshot(self, filename: str) -> Path:
        path = Path("data") / "logs" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=True)
        return path