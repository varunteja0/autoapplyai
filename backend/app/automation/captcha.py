from __future__ import annotations

from playwright.sync_api import Page

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Common CAPTCHA indicators
CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "[class*='captcha']",
    "[id*='captcha']",
    "[class*='g-recaptcha']",
    "[data-sitekey]",
    "iframe[src*='captcha']",
    "[class*='cf-turnstile']",
]

CAPTCHA_TEXT_INDICATORS = [
    "verify you are human",
    "i'm not a robot",
    "complete the captcha",
    "security check",
    "prove you're not a robot",
]


class CaptchaDetector:
    """Detect CAPTCHA presence on a page."""

    def detect(self, page: Page) -> bool:
        """Check if any CAPTCHA elements are present."""
        # Check for CAPTCHA iframes and elements
        for selector in CAPTCHA_SELECTORS:
            try:
                if page.locator(selector).count() > 0:
                    logger.warning("CAPTCHA detected via selector", selector=selector)
                    return True
            except Exception:
                continue

        # Check page text for CAPTCHA indicators
        try:
            body_text = page.locator("body").inner_text().lower()
            for indicator in CAPTCHA_TEXT_INDICATORS:
                if indicator in body_text:
                    logger.warning("CAPTCHA detected via text", indicator=indicator)
                    return True
        except Exception:
            pass

        return False
