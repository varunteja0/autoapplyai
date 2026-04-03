from __future__ import annotations

import re
from typing import Type
from urllib.parse import urlparse

from app.models.job import JobPlatform
from app.utils.logging import get_logger

logger = get_logger(__name__)

# URL patterns for platform detection
PLATFORM_PATTERNS: dict[JobPlatform, list[str]] = {
    JobPlatform.WORKDAY: [
        r"myworkdayjobs\.com",
        r"workday\.com",
        r"wd\d+\.myworkdayjobs\.com",
    ],
    JobPlatform.GREENHOUSE: [
        r"greenhouse\.io",
        r"boards\.greenhouse\.io",
        r"job-boards\.greenhouse\.io",
    ],
    JobPlatform.LEVER: [
        r"lever\.co",
        r"jobs\.lever\.co",
    ],
    JobPlatform.TALEO: [
        r"taleo\.net",
        r"oracle\.com/.*taleo",
    ],
}


def detect_platform(url: str) -> JobPlatform:
    """Detect the ATS platform from a job URL."""
    parsed = urlparse(url)
    full_url = f"{parsed.netloc}{parsed.path}".lower()

    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, full_url, re.IGNORECASE):
                logger.info("Platform detected", platform=platform.value, url=url)
                return platform

    logger.warning("Unknown platform", url=url)
    return JobPlatform.UNKNOWN


def get_platform_bot(platform: JobPlatform) -> Type:
    """Get the appropriate automation bot class for a platform."""
    from app.automation.platforms.workday import WorkdayBot
    from app.automation.platforms.greenhouse import GreenhouseBot
    from app.automation.platforms.lever import LeverBot
    from app.automation.platforms.taleo import TaleoBot

    platform_bots = {
        JobPlatform.WORKDAY: WorkdayBot,
        JobPlatform.GREENHOUSE: GreenhouseBot,
        JobPlatform.LEVER: LeverBot,
        JobPlatform.TALEO: TaleoBot,
    }

    bot_class = platform_bots.get(platform)
    if bot_class is None:
        from app.automation.base import BaseBot
        return BaseBot

    return bot_class
