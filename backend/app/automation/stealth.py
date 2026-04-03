from __future__ import annotations

from playwright.sync_api import BrowserContext

from app.utils.logging import get_logger

logger = get_logger(__name__)


def apply_stealth_settings(context: BrowserContext) -> None:
    """Apply anti-bot-detection measures to the browser context.

    Modifies navigator properties and other JavaScript APIs to make
    the automated browser appear more like a regular user browser.
    """
    stealth_js = """
    () => {
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });

        // Override navigator.plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });

        // Override navigator.languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });

        // Override chrome runtime
        window.chrome = {
            runtime: {},
        };

        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);

        // Prevent canvas fingerprinting detection
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function() {
            return getImageData.apply(this, arguments);
        };

        // Override connection rtt
        if (navigator.connection) {
            Object.defineProperty(navigator.connection, 'rtt', {
                get: () => 100,
            });
        }
    }
    """
    context.add_init_script(stealth_js)
    logger.debug("Stealth settings applied")
