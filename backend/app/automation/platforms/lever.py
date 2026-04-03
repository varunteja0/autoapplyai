from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from app.automation.base import BaseBot
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LeverBot(BaseBot):
    """Automated application bot for Lever career portals.

    Lever applications are typically single-page forms similar to Greenhouse:
    1. Personal Information (name, email, phone, URLs)
    2. Resume Upload
    3. Cover Letter
    4. Additional Information / Custom Questions
    5. Submit
    """

    PLATFORM_NAME = "lever"

    SELECTORS = {
        "apply_button": "a.postings-btn, a[href*='apply']",
        "name": "input[name='name']",
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "org": "input[name='org']",
        "linkedin": "input[name='urls[LinkedIn]']",
        "github": "input[name='urls[GitHub]']",
        "portfolio": "input[name='urls[Portfolio]']",
        "other_url": "input[name='urls[Other]']",
        "resume_upload": "input[type='file'][name='resume']",
        "cover_letter": "textarea[name='comments']",
        "submit_button": "button[type='submit'], .application-submit",
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
        """Execute the full Lever application flow."""
        page = self._start_browser()
        try:
            logger.info("Starting Lever application", url=url, application_id=application_id)

            # Navigate to apply page
            apply_url = url if "/apply" in url else url.rstrip("/") + "/apply"
            page.goto(apply_url, wait_until="networkidle")
            self._human_delay(2000, 3000)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            # Fill form
            self._fill_personal_info(page, user, profile)
            self._human_delay(500, 1000)

            self._upload_resume(page, resume)
            self._human_delay(1000, 2000)

            self._fill_cover_letter(page, custom_answers)
            self._human_delay(500, 1000)

            self._fill_custom_questions(page, custom_answers or {}, profile)
            self._human_delay(500, 1000)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            self._submit(page)

            self._take_screenshot(page, f"{application_id}_submitted")
            logger.info("Lever application submitted", application_id=application_id)
            return {"status": "submitted", "captcha_detected": False}

        except Exception as exc:
            self._take_screenshot(page, f"{application_id}_error")
            logger.error("Lever application failed", error=str(exc))
            raise
        finally:
            self._close_browser()

    def _fill_personal_info(self, page: Page, user: Any, profile: Any | None) -> None:
        self._safe_fill(page, self.SELECTORS["name"], user.full_name)
        self._safe_fill(page, self.SELECTORS["email"], user.email)

        if profile:
            if profile.phone:
                self._safe_fill(page, self.SELECTORS["phone"], profile.phone)
            if profile.current_company:
                self._safe_fill(page, self.SELECTORS["org"], profile.current_company)
            if profile.linkedin_url:
                self._safe_fill(page, self.SELECTORS["linkedin"], profile.linkedin_url)
            if profile.github_url:
                self._safe_fill(page, self.SELECTORS["github"], profile.github_url)
            if profile.portfolio_url:
                self._safe_fill(page, self.SELECTORS["portfolio"], profile.portfolio_url)

    def _upload_resume(self, page: Page, resume: Any | None) -> None:
        if resume and resume.file_path:
            self._upload_file(page, self.SELECTORS["resume_upload"], resume.file_path)
            self._human_delay(2000, 3000)

    def _fill_cover_letter(self, page: Page, custom_answers: dict | None) -> None:
        if custom_answers and custom_answers.get("cover_letter_summary"):
            self._safe_fill(
                page,
                self.SELECTORS["cover_letter"],
                custom_answers["cover_letter_summary"],
            )

    def _fill_custom_questions(
        self, page: Page, custom_answers: dict, profile: Any | None
    ) -> None:
        """Fill custom fields on the Lever application form."""
        custom_fields = page.locator(".application-question")
        count = custom_fields.count()

        for i in range(count):
            try:
                field = custom_fields.nth(i)
                label = field.locator("label, .application-label").first
                if label.count() == 0:
                    continue

                label_text = label.inner_text().strip().lower()

                # Text inputs
                text_input = field.locator("input[type='text'], textarea").first
                if text_input.count() > 0 and text_input.is_visible():
                    answer = self._match_answer(label_text, custom_answers, profile)
                    if answer:
                        text_input.fill(answer)
                        continue

                # Dropdowns
                select_el = field.locator("select").first
                if select_el.count() > 0:
                    self._handle_dropdown(select_el, label_text, profile)

            except Exception as e:
                logger.debug("Could not fill Lever question", index=i, error=str(e))

    def _match_answer(
        self, label: str, custom_answers: dict, profile: Any | None
    ) -> str | None:
        label_lower = label.lower()
        if "salary" in label_lower:
            return custom_answers.get("salary_expectations") or (
                profile.salary_expectation if profile else None
            )
        if "why" in label_lower and "interest" in label_lower:
            return custom_answers.get("why_interested")
        if "hear" in label_lower:
            return "LinkedIn"
        if profile and profile.stored_answers:
            for key, value in profile.stored_answers.items():
                if key.lower() in label_lower:
                    return value
        return None

    def _handle_dropdown(self, select_el: Any, label: str, profile: Any | None) -> None:
        options = select_el.locator("option")
        count = options.count()
        if "authorization" in label:
            for i in range(count):
                if "yes" in options.nth(i).inner_text().lower():
                    select_el.select_option(index=i)
                    return

    def _submit(self, page: Page) -> None:
        submitted = self._safe_click(page, self.SELECTORS["submit_button"])
        if not submitted:
            self._safe_click(page, "button:has-text('Submit application')")
        self._human_delay(3000, 5000)

    def scrape_job_details(self, url: str) -> dict:
        page = self._start_browser()
        try:
            page.goto(url, wait_until="networkidle")
            self._human_delay(1500, 2500)
            details = {}
            title_el = page.locator(".posting-headline h2")
            if title_el.count() > 0:
                details["title"] = title_el.first.inner_text().strip()
            location_el = page.locator(".posting-categories .location")
            if location_el.count() > 0:
                details["location"] = location_el.first.inner_text().strip()
            desc_el = page.locator(".posting-page [data-qa='job-description']")
            if desc_el.count() > 0:
                details["description"] = desc_el.first.inner_text().strip()[:5000]
            return details
        finally:
            self._close_browser()
