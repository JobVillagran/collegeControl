from __future__ import annotations

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from backend.config.settings import HEADLESS

class BrowserManager:
    def __init__(self) -> None:
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> Page:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        return self.page

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()