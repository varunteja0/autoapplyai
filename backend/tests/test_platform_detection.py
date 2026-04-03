from __future__ import annotations

import pytest

from app.automation.detector import detect_platform
from app.models.job import JobPlatform


def test_detect_workday():
    urls = [
        "https://company.wd5.myworkdayjobs.com/en-US/careers/job/Engineer_12345",
        "https://abc.myworkdayjobs.com/jobs/12345",
    ]
    for url in urls:
        assert detect_platform(url) == JobPlatform.WORKDAY


def test_detect_greenhouse():
    urls = [
        "https://boards.greenhouse.io/company/jobs/12345",
        "https://job-boards.greenhouse.io/company/jobs/12345",
    ]
    for url in urls:
        assert detect_platform(url) == JobPlatform.GREENHOUSE


def test_detect_lever():
    urls = [
        "https://jobs.lever.co/company/12345",
        "https://jobs.lever.co/company/12345/apply",
    ]
    for url in urls:
        assert detect_platform(url) == JobPlatform.LEVER


def test_detect_taleo():
    urls = [
        "https://company.taleo.net/careersection/2/jobdetail.ftl?job=12345",
    ]
    for url in urls:
        assert detect_platform(url) == JobPlatform.TALEO


def test_detect_unknown():
    assert detect_platform("https://example.com/careers") == JobPlatform.UNKNOWN
    assert detect_platform("https://linkedin.com/jobs/123") == JobPlatform.UNKNOWN
