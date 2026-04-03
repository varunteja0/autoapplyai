from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from app.automation.base import BaseBot
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GreenhouseBot(BaseBot):
    """Automated application bot for Greenhouse career portals.

    Greenhouse applications are typically single-page forms:
    1. Personal Information
    2. Resume Upload
    3. Cover Letter (optional)
    4. Custom Questions
    5. Demographic Information (optional)
    6. Submit
    """

    PLATFORM_NAME = "greenhouse"

    SELECTORS = {
        # Personal info
        "first_name": "#first_name",
        "last_name": "#last_name",
        "email": "#email",
        "phone": "#phone",
        "location": "#job_application_location",
        "linkedin": "input[name*='linkedin'], input[id*='linkedin']",
        "website": "input[name*='website'], input[id*='website']",
        "github": "input[name*='github'], input[id*='github']",
        # Resume
        "resume_upload": "input[type='file'][id*='resume'], input[type='file'][name*='resume']",
        "resume_text": "#resume_text",
        # Cover letter
        "cover_letter_upload": "input[type='file'][id*='cover_letter']",
        "cover_letter_text": "#cover_letter_text",
        # Submit
        "submit_button": "#submit_app, input[type='submit'], button[type='submit']",
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
        """Execute the full Greenhouse application flow."""
        page = self._start_browser()
        try:
            logger.info("Starting Greenhouse application", url=url, application_id=application_id)

            # Navigate to application page
            apply_url = self._get_apply_url(url)
            page.goto(apply_url, wait_until="networkidle")
            self._human_delay(2000, 3000)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            # Fill personal information
            self._fill_personal_info(page, user, profile)
            self._human_delay(500, 1000)

            # Upload resume
            self._upload_resume(page, resume)
            self._human_delay(1000, 2000)

            # Fill cover letter
            self._fill_cover_letter(page, custom_answers)
            self._human_delay(500, 1000)

            # Fill custom questions
            self._fill_custom_questions(page, custom_answers or {}, profile)
            self._human_delay(500, 1000)

            # Handle demographic questions
            self._fill_demographics(page)
            self._human_delay(500, 1000)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            # Submit
            self._submit(page)

            self._take_screenshot(page, f"{application_id}_submitted")
            logger.info("Greenhouse application submitted", application_id=application_id)

            return {"status": "submitted", "captcha_detected": False}

        except Exception as exc:
            self._take_screenshot(page, f"{application_id}_error")
            logger.error("Greenhouse application failed", error=str(exc))
            raise
        finally:
            self._close_browser()

    def _get_apply_url(self, url: str) -> str:
        """Convert a Greenhouse job URL to its application URL."""
        if "/jobs/" in url and "#app" not in url:
            return url + "#app"
        return url

    def _fill_personal_info(self, page: Page, user: Any, profile: Any | None) -> None:
        """Fill the personal information section."""
        name_parts = user.full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        self._safe_fill(page, self.SELECTORS["first_name"], first_name)
        self._human_delay(200, 400)
        self._safe_fill(page, self.SELECTORS["last_name"], last_name)
        self._human_delay(200, 400)
        self._safe_fill(page, self.SELECTORS["email"], user.email)
        self._human_delay(200, 400)

        if profile:
            if profile.phone:
                self._safe_fill(page, self.SELECTORS["phone"], profile.phone)
            if profile.linkedin_url:
                self._safe_fill(page, self.SELECTORS["linkedin"], profile.linkedin_url)
            if profile.github_url:
                self._safe_fill(page, self.SELECTORS["github"], profile.github_url)
            if profile.portfolio_url:
                self._safe_fill(page, self.SELECTORS["website"], profile.portfolio_url)

            # Location autocomplete
            if profile.city and profile.state:
                location_str = f"{profile.city}, {profile.state}"
                location_input = page.locator(self.SELECTORS["location"])
                if location_input.count() > 0 and location_input.is_visible():
                    location_input.fill(location_str)
                    self._human_delay(1000, 2000)
                    # Select first suggestion
                    suggestion = page.locator(".autocomplete-results li").first
                    if suggestion.is_visible(timeout=3000):
                        suggestion.click()

        logger.info("Personal info filled for Greenhouse")

    def _upload_resume(self, page: Page, resume: Any | None) -> None:
        """Upload resume file."""
        if resume and resume.file_path:
            # Try the file input
            uploaded = self._upload_file(
                page, self.SELECTORS["resume_upload"], resume.file_path
            )
            if uploaded:
                self._human_delay(2000, 3000)
                logger.info("Resume uploaded to Greenhouse")
            else:
                # Try pasting resume text if parsed data is available
                if resume.parsed_data and resume.parsed_data.get("text"):
                    self._safe_fill(
                        page,
                        self.SELECTORS["resume_text"],
                        resume.parsed_data["text"][:5000],
                    )

    def _fill_cover_letter(self, page: Page, custom_answers: dict | None) -> None:
        """Fill cover letter section if present."""
        if custom_answers and custom_answers.get("cover_letter_summary"):
            self._safe_fill(
                page,
                self.SELECTORS["cover_letter_text"],
                custom_answers["cover_letter_summary"],
            )

    def _fill_custom_questions(
        self, page: Page, custom_answers: dict, profile: Any | None
    ) -> None:
        """Fill custom application questions."""
        # Greenhouse custom questions are typically in div.field containers
        question_fields = page.locator(".field:visible")
        count = question_fields.count()

        for i in range(count):
            try:
                field = question_fields.nth(i)
                label_el = field.locator("label").first
                if label_el.count() == 0:
                    continue

                label_text = label_el.inner_text().strip().lower()

                # Text inputs
                text_input = field.locator("input[type='text'], textarea").first
                if text_input.count() > 0 and text_input.is_visible():
                    answer = self._match_answer(label_text, custom_answers, profile)
                    if answer:
                        text_input.clear()
                        text_input.fill(answer)
                        self._human_delay(200, 400)
                        continue

                # Select dropdowns
                select_el = field.locator("select").first
                if select_el.count() > 0 and select_el.is_visible():
                    self._handle_dropdown(select_el, label_text, profile)
                    continue

                # Radio buttons
                radio_inputs = field.locator("input[type='radio']")
                if radio_inputs.count() > 0:
                    self._handle_radio_group(page, field, label_text, profile)

            except Exception as e:
                logger.debug("Could not fill custom question", index=i, error=str(e))

    def _match_answer(
        self, label: str, custom_answers: dict, profile: Any | None
    ) -> str | None:
        """Match a form label to an appropriate answer."""
        label_lower = label.lower()

        if "salary" in label_lower or "compensation" in label_lower:
            return custom_answers.get("salary_expectations") or (
                profile.salary_expectation if profile else None
            )
        if "linkedin" in label_lower:
            return profile.linkedin_url if profile else None
        if "github" in label_lower:
            return profile.github_url if profile else None
        if "portfolio" in label_lower or "website" in label_lower:
            return profile.portfolio_url if profile else None
        if "start date" in label_lower or "when can you start" in label_lower:
            return custom_answers.get("start_date")
        if "why" in label_lower and ("interest" in label_lower or "role" in label_lower):
            return custom_answers.get("why_interested")
        if "experience" in label_lower and "relevant" in label_lower:
            return custom_answers.get("relevant_experience")
        if "hear" in label_lower and "about" in label_lower:
            return "LinkedIn"

        # Check stored answers
        if profile and profile.stored_answers:
            for key, value in profile.stored_answers.items():
                if key.lower() in label_lower or label_lower in key.lower():
                    return value

        return None

    def _handle_dropdown(self, select_el: Any, label: str, profile: Any | None) -> None:
        """Handle dropdown selection for common questions."""
        options = select_el.locator("option")
        count = options.count()

        if "authorization" in label or "legally" in label:
            # Select "Yes" for work authorization
            for i in range(count):
                text = options.nth(i).inner_text().strip().lower()
                if "yes" in text:
                    select_el.select_option(index=i)
                    return

        if "sponsor" in label:
            # Select "No" for sponsorship needed (or "Yes" if needed)
            needs_sponsorship = profile.requires_sponsorship if profile else False
            target = "yes" if needs_sponsorship else "no"
            for i in range(count):
                text = options.nth(i).inner_text().strip().lower()
                if target in text:
                    select_el.select_option(index=i)
                    return

    def _handle_radio_group(
        self, page: Page, field: Any, label: str, profile: Any | None
    ) -> None:
        """Handle radio button groups."""
        if "authorization" in label or "authorized" in label:
            yes_radio = field.locator("input[type='radio'][value='Yes']")
            if yes_radio.count() > 0:
                yes_radio.click()
        elif "sponsor" in label:
            needs = profile.requires_sponsorship if profile else False
            value = "Yes" if needs else "No"
            radio = field.locator(f"input[type='radio'][value='{value}']")
            if radio.count() > 0:
                radio.click()

    def _fill_demographics(self, page: Page) -> None:
        """Handle optional demographic questions."""
        # Select decline to answer where possible
        decline_options = page.locator(
            "select option:has-text('Decline'), select option:has-text('don\\'t wish')"
        )
        if decline_options.count() > 0:
            # For each demographic dropdown, select decline
            demo_selects = page.locator(
                "#job_application_gender, #job_application_race, #job_application_veteran_status"
            )
            for i in range(demo_selects.count()):
                try:
                    sel = demo_selects.nth(i)
                    options = sel.locator("option")
                    for j in range(options.count()):
                        text = options.nth(j).inner_text().lower()
                        if "decline" in text or "don't wish" in text:
                            sel.select_option(index=j)
                            break
                except Exception:
                    pass

    def _submit(self, page: Page) -> None:
        """Submit the Greenhouse application."""
        submitted = self._safe_click(page, self.SELECTORS["submit_button"])
        if not submitted:
            # Try alternative submit buttons
            alt_selectors = [
                "button:has-text('Submit Application')",
                "input[value='Submit Application']",
                "button:has-text('Submit')",
            ]
            for selector in alt_selectors:
                if self._safe_click(page, selector):
                    submitted = True
                    break

        if not submitted:
            raise Exception("Could not find Submit button on Greenhouse form")

        self._human_delay(3000, 5000)
        logger.info("Greenhouse submit button clicked")

    def scrape_job_details(self, url: str) -> dict:
        """Scrape job details from a Greenhouse posting."""
        page = self._start_browser()
        try:
            page.goto(url, wait_until="networkidle")
            self._human_delay(1500, 2500)

            details = {}

            # Job title
            title_el = page.locator(".app-title, h1.heading")
            if title_el.count() > 0:
                details["title"] = title_el.first.inner_text().strip()

            # Company
            company_el = page.locator(".company-name, .brand-name")
            if company_el.count() > 0:
                details["company"] = company_el.first.inner_text().strip()

            # Location
            location_el = page.locator(".location, .body--metadata")
            if location_el.count() > 0:
                details["location"] = location_el.first.inner_text().strip()

            # Description
            desc_el = page.locator("#content, .content-intro, .job-description")
            if desc_el.count() > 0:
                details["description"] = desc_el.first.inner_text().strip()[:5000]

            return details
        finally:
            self._close_browser()
