from __future__ import annotations

import random
import time
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from app.automation.captcha import CaptchaDetector
from app.automation.stealth import apply_stealth_settings
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BaseBot:
    """Base class for all platform automation bots.

    Provides common browser management, navigation, form filling,
    and anti-detection utilities.
    """

    PLATFORM_NAME = "unknown"

    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.captcha_detector = CaptchaDetector()

    def _start_browser(self) -> Page:
        """Launch a Playwright browser with stealth settings."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=settings.playwright_headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
        )
        apply_stealth_settings(self.context)
        self.page = self.context.new_page()
        self.page.set_default_timeout(settings.playwright_timeout)
        return self.page

    def _close_browser(self) -> None:
        """Safely close the browser."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.warning("Error closing browser", error=str(e))

    def _human_delay(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Add a random human-like delay."""
        delay = random.randint(min_ms, max_ms) / 1000.0
        time.sleep(delay)

    def _human_type(self, page: Page, selector: str, text: str) -> None:
        """Type text with human-like delays between keystrokes."""
        element = page.locator(selector)
        element.click()
        self._human_delay(200, 500)
        for char in text:
            element.type(char, delay=random.randint(30, 120))

    def _safe_fill(self, page: Page, selector: str, value: str) -> bool:
        """Safely fill a form field, returning True if successful."""
        try:
            element = page.locator(selector)
            if element.is_visible(timeout=3000):
                element.clear()
                element.fill(value)
                return True
        except Exception as e:
            logger.debug("Could not fill field", selector=selector, error=str(e))
        return False

    def _safe_select(self, page: Page, selector: str, value: str) -> bool:
        """Safely select a dropdown option."""
        try:
            element = page.locator(selector)
            if element.is_visible(timeout=3000):
                element.select_option(value=value)
                return True
        except Exception as e:
            logger.debug("Could not select option", selector=selector, error=str(e))
        return False

    def _safe_click(self, page: Page, selector: str) -> bool:
        """Safely click an element."""
        try:
            element = page.locator(selector)
            if element.is_visible(timeout=3000):
                element.click()
                return True
        except Exception as e:
            logger.debug("Could not click", selector=selector, error=str(e))
        return False

    def _upload_file(self, page: Page, selector: str, file_path: str) -> bool:
        """Upload a file to a file input."""
        try:
            page.locator(selector).set_input_files(file_path)
            return True
        except Exception as e:
            logger.error("File upload failed", selector=selector, error=str(e))
            return False

    def _check_captcha(self, page: Page) -> bool:
        """Check if a CAPTCHA is present on the page."""
        return self.captcha_detector.detect(page)

    def _take_screenshot(self, page: Page, name: str) -> str | None:
        """Take a screenshot for debugging."""
        try:
            path = settings.upload_path / "screenshots" / f"{name}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path))
            return str(path)
        except Exception as e:
            logger.warning("Screenshot failed", error=str(e))
            return None

    def apply(
        self,
        url: str,
        user: Any,
        profile: Any | None,
        resume: Any | None,
        custom_answers: dict | None,
        application_id: str,
    ) -> dict:
        """Execute the full application flow. Override in subclasses."""
        raise NotImplementedError(
            f"apply() not implemented for {self.PLATFORM_NAME}"
        )

    def scrape_job_details(self, url: str) -> dict:
        """Scrape job title, company, description from the URL."""
        page = self._start_browser()
        try:
            page.goto(url, wait_until="networkidle")
            self._human_delay(1000, 2000)

            title = page.title()
            description = page.locator("body").inner_text()[:5000]

            return {
                "title": title,
                "description": description,
            }
        finally:
            self._close_browser()
