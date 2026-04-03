from __future__ import annotations

import re
from urllib.parse import urlparse


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filenames."""
    return re.sub(r'[^\w\s\-.]', '', filename).strip()


def extract_domain(url: str) -> str:
    """Extract domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to a maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
