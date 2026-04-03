from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from app.automation.base import BaseBot
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TaleoBot(BaseBot):
    """Automated application bot for Oracle Taleo career portals.

    Taleo is an older ATS with more complex, multi-page forms.
    Typical flow:
    1. Job search/details page
    2. Create profile / Sign in
    3. Personal information
    4. Experience & Education
    5. Resume Upload
    6. Questionnaire
    7. Review & Submit
    """

    PLATFORM_NAME = "taleo"

    SELECTORS = {
        "apply_button": "#applyButton, a.applyButton, a[class*='apply']",
        "first_name": "#firstName, input[name='firstName']",
        "last_name": "#lastName, input[name='lastName']",
        "email": "#email, input[name='email']",
        "phone": "#phoneNumber, input[name='phoneNumber']",
        "address": "#address, input[name='address']",
        "city": "#city, input[name='city']",
        "state": "#state, select[name='state']",
        "zip": "#zipCode, input[name='zipCode']",
        "resume_upload": "input[type='file']",
        "next_button": "#next, button:has-text('Next'), input[value='Next']",
        "submit_button": "#submit, button:has-text('Submit'), input[value='Submit']",
    }

    def apply(
        self,
        url: str,
        user: Any,
        profile: Any | None,
        resume: Any | None,
        custom_answers: dict | None,
        application_id: str,
    ) -> dict:
        page = self._start_browser()
        try:
            logger.info("Starting Taleo application", url=url, application_id=application_id)

            page.goto(url, wait_until="networkidle")
            self._human_delay(3000, 5000)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            # Click Apply
            self._safe_click(page, self.SELECTORS["apply_button"])
            self._human_delay(2000, 3000)

            # Fill personal info
            self._fill_personal_info(page, user, profile)
            self._safe_click(page, self.SELECTORS["next_button"])
            self._human_delay(2000, 3000)

            # Upload resume
            if resume and resume.file_path:
                self._upload_file(page, self.SELECTORS["resume_upload"], resume.file_path)
                self._human_delay(3000, 5000)

            self._safe_click(page, self.SELECTORS["next_button"])
            self._human_delay(2000, 3000)

            # Fill questions
            self._fill_questions(page, custom_answers or {}, profile)
            self._safe_click(page, self.SELECTORS["next_button"])
            self._human_delay(2000, 3000)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            # Submit
            self._safe_click(page, self.SELECTORS["submit_button"])
            self._human_delay(3000, 5000)

            self._take_screenshot(page, f"{application_id}_submitted")
            logger.info("Taleo application submitted", application_id=application_id)
            return {"status": "submitted", "captcha_detected": False}

        except Exception as exc:
            self._take_screenshot(page, f"{application_id}_error")
            logger.error("Taleo application failed", error=str(exc))
            raise
        finally:
            self._close_browser()

    def _fill_personal_info(self, page: Page, user: Any, profile: Any | None) -> None:
        name_parts = user.full_name.split(" ", 1)
        self._safe_fill(page, self.SELECTORS["first_name"], name_parts[0])
        self._safe_fill(page, self.SELECTORS["last_name"], name_parts[1] if len(name_parts) > 1 else "")
        self._safe_fill(page, self.SELECTORS["email"], user.email)

        if profile:
            if profile.phone:
                self._safe_fill(page, self.SELECTORS["phone"], profile.phone)
            if profile.address_line1:
                self._safe_fill(page, self.SELECTORS["address"], profile.address_line1)
            if profile.city:
                self._safe_fill(page, self.SELECTORS["city"], profile.city)
            if profile.zip_code:
                self._safe_fill(page, self.SELECTORS["zip"], profile.zip_code)

    def _fill_questions(
        self, page: Page, custom_answers: dict, profile: Any | None
    ) -> None:
        """Fill Taleo questionnaire fields."""
        text_fields = page.locator("input[type='text']:visible, textarea:visible")
        for i in range(text_fields.count()):
            try:
                field = text_fields.nth(i)
                label_text = ""
                field_id = field.get_attribute("id") or ""
                if field_id:
                    label = page.locator(f"label[for='{field_id}']")
                    if label.count() > 0:
                        label_text = label.first.inner_text().lower()

                if not label_text:
                    continue

                if "salary" in label_text:
                    answer = custom_answers.get("salary_expectations", "")
                    if answer:
                        field.fill(answer)
                elif "experience" in label_text and "year" in label_text:
                    if profile and profile.years_of_experience:
                        field.fill(str(profile.years_of_experience))
            except Exception:
                continue

    def scrape_job_details(self, url: str) -> dict:
        page = self._start_browser()
        try:
            page.goto(url, wait_until="networkidle")
            self._human_delay(2000, 3000)
            return {
                "title": page.title(),
                "description": page.locator("body").inner_text()[:5000],
            }
        finally:
            self._close_browser()
