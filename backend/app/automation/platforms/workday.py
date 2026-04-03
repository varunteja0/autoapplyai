from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from app.automation.base import BaseBot
from app.utils.logging import get_logger

logger = get_logger(__name__)


class WorkdayBot(BaseBot):
    """Automated application bot for Workday career portals.

    Workday portals typically follow a multi-step application flow:
    1. Job details page → "Apply" button
    2. Sign In / Create Account
    3. My Information (personal details)
    4. My Experience (resume, work history)
    5. Application Questions
    6. Voluntary Disclosures
    7. Review & Submit
    """

    PLATFORM_NAME = "workday"

    # Common Workday selectors
    SELECTORS = {
        "apply_button": "[data-automation-id='jobPostingApplyButton']",
        "sign_in_link": "[data-automation-id='signInLink']",
        "create_account_link": "[data-automation-id='createAccountLink']",
        "email_input": "[data-automation-id='email']",
        "password_input": "[data-automation-id='password']",
        "verify_email_input": "[data-automation-id='verifyEmail']",
        "first_name": "[data-automation-id='legalNameSection_firstName']",
        "last_name": "[data-automation-id='legalNameSection_lastName']",
        "address_line1": "[data-automation-id='addressSection_addressLine1']",
        "city": "[data-automation-id='addressSection_city']",
        "state": "[data-automation-id='addressSection_countryRegion']",
        "zip_code": "[data-automation-id='addressSection_postalCode']",
        "phone_type": "[data-automation-id='phoneType']",
        "phone_number": "[data-automation-id='phone-number']",
        "resume_upload": "[data-automation-id='file-upload-input-ref']",
        "next_button": "[data-automation-id='bottom-navigation-next-button']",
        "submit_button": "[data-automation-id='bottom-navigation-next-button']",
        "country_dropdown": "[data-automation-id='countryDropdown']",
        "how_hear": "[data-automation-id='sourceSection']",
        "linkedin_input": "[data-automation-id='linkedinQuestion']",
        "previous_worker_no": "[data-automation-id='previousWorker'] input[value='No']",
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
        """Execute the full Workday application flow."""
        page = self._start_browser()
        try:
            logger.info("Starting Workday application", url=url, application_id=application_id)

            # Step 1: Navigate to job page
            page.goto(url, wait_until="networkidle")
            self._human_delay(2000, 4000)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            # Step 2: Click Apply
            if not self._click_apply(page):
                self._take_screenshot(page, f"{application_id}_apply_failed")
                raise Exception("Could not find Apply button on Workday page")

            self._human_delay(2000, 3000)

            # Step 3: Handle Sign In / Account Creation
            self._handle_auth_page(page, user)
            self._human_delay(1500, 2500)

            if self._check_captcha(page):
                return {"captcha_detected": True}

            # Step 4: Fill My Information
            self._fill_personal_info(page, user, profile)
            self._click_next(page)
            self._human_delay(1500, 2500)

            # Step 5: Upload Resume & Fill Experience
            self._fill_experience(page, resume)
            self._click_next(page)
            self._human_delay(1500, 2500)

            # Step 6: Fill Application Questions
            self._fill_questions(page, custom_answers or {}, profile)
            self._click_next(page)
            self._human_delay(1500, 2500)

            # Step 7: Handle Voluntary Disclosures
            self._fill_voluntary_disclosures(page)
            self._click_next(page)
            self._human_delay(1500, 2500)

            # Step 8: Review and Submit
            self._submit_application(page)

            self._take_screenshot(page, f"{application_id}_submitted")
            logger.info("Workday application submitted", application_id=application_id)

            return {"status": "submitted", "captcha_detected": False}

        except Exception as exc:
            self._take_screenshot(page, f"{application_id}_error")
            logger.error("Workday application failed", error=str(exc))
            raise
        finally:
            self._close_browser()

    def _click_apply(self, page: Page) -> bool:
        """Click the Apply button on the job posting page."""
        # Try multiple possible Apply button selectors
        selectors = [
            self.SELECTORS["apply_button"],
            "a:has-text('Apply')",
            "button:has-text('Apply')",
            "[aria-label='Apply']",
        ]
        for selector in selectors:
            if self._safe_click(page, selector):
                logger.info("Clicked Apply button", selector=selector)
                return True
        return False

    def _handle_auth_page(self, page: Page, user: Any) -> None:
        """Handle the Workday sign-in or account creation page."""
        self._human_delay(2000, 3000)

        # Check if we need to create an account or sign in
        # Try "Use my last application" first
        if self._safe_click(page, "[data-automation-id='useMyLastApplication']"):
            self._human_delay(1000, 2000)
            return

        # Try to create account with autofill
        if self._safe_click(page, self.SELECTORS["create_account_link"]):
            self._human_delay(1000, 2000)
            self._safe_fill(page, self.SELECTORS["email_input"], user.email)
            self._safe_fill(page, self.SELECTORS["verify_email_input"], user.email)
            # Password handling - we don't store plain passwords
            # The user flow would need to handle this
            self._safe_click(page, "[data-automation-id='createAccountSubmitButton']")
            self._human_delay(2000, 3000)

    def _fill_personal_info(self, page: Page, user: Any, profile: Any | None) -> None:
        """Fill the My Information section."""
        name_parts = user.full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        self._safe_fill(page, self.SELECTORS["first_name"], first_name)
        self._safe_fill(page, self.SELECTORS["last_name"], last_name)

        if profile:
            self._safe_fill(page, self.SELECTORS["address_line1"], profile.address_line1 or "")
            self._safe_fill(page, self.SELECTORS["city"], profile.city or "")
            self._safe_fill(page, self.SELECTORS["zip_code"], profile.zip_code or "")
            self._safe_fill(page, self.SELECTORS["phone_number"], profile.phone or "")

            if profile.country:
                self._safe_select(page, self.SELECTORS["country_dropdown"], profile.country)

        logger.info("Personal info filled")

    def _fill_experience(self, page: Page, resume: Any | None) -> None:
        """Upload resume and fill experience section."""
        if resume and resume.file_path:
            self._upload_file(page, self.SELECTORS["resume_upload"], resume.file_path)
            self._human_delay(3000, 5000)
            logger.info("Resume uploaded to Workday")

    def _fill_questions(
        self, page: Page, custom_answers: dict, profile: Any | None
    ) -> None:
        """Fill application-specific questions using AI-generated answers."""
        # Handle common Workday questions
        text_inputs = page.locator("input[type='text']:visible, textarea:visible")
        count = text_inputs.count()

        for i in range(count):
            try:
                element = text_inputs.nth(i)
                label_text = self._get_field_label(page, element)

                if not label_text:
                    continue

                answer = self._match_answer(label_text, custom_answers, profile)
                if answer:
                    element.clear()
                    element.fill(answer)
                    self._human_delay(300, 600)
            except Exception as e:
                logger.debug("Could not fill question field", index=i, error=str(e))

        # Handle radio buttons and checkboxes for common questions
        self._handle_yes_no_questions(page, profile)

    def _get_field_label(self, page: Page, element: Any) -> str:
        """Try to find the label text for a form field."""
        try:
            # Try aria-label
            aria = element.get_attribute("aria-label")
            if aria:
                return aria.lower()

            # Try associated label
            field_id = element.get_attribute("id")
            if field_id:
                label = page.locator(f"label[for='{field_id}']")
                if label.count() > 0:
                    return label.first.inner_text().lower()

            # Try parent label
            parent = element.locator("xpath=ancestor::label[1]")
            if parent.count() > 0:
                return parent.first.inner_text().lower()

            # Try preceding sibling or data-automation-id
            automation_id = element.get_attribute("data-automation-id")
            if automation_id:
                return automation_id.lower()
        except Exception:
            pass
        return ""

    def _match_answer(
        self, label: str, custom_answers: dict, profile: Any | None
    ) -> str | None:
        """Match a form label to an appropriate answer."""
        label_lower = label.lower()

        # Direct matches from AI-generated answers
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
        if "start date" in label_lower or "availability" in label_lower:
            return custom_answers.get("start_date")
        if "experience" in label_lower and "year" in label_lower:
            return str(profile.years_of_experience) if profile and profile.years_of_experience else None

        # Check stored answers from profile
        if profile and profile.stored_answers:
            for key, value in profile.stored_answers.items():
                if key.lower() in label_lower or label_lower in key.lower():
                    return value

        return None

    def _handle_yes_no_questions(self, page: Page, profile: Any | None) -> None:
        """Handle common yes/no radio button questions."""
        # Work authorization
        if profile and profile.work_authorization:
            self._safe_click(
                page,
                f"input[type='radio'][value='Yes']:near(:text('authorized to work'))",
            )
        # Previous worker - typically "No"
        self._safe_click(page, self.SELECTORS["previous_worker_no"])

    def _fill_voluntary_disclosures(self, page: Page) -> None:
        """Handle voluntary disclosure page (gender, race, veteran, disability)."""
        # Select "I don't wish to answer" where available
        decline_selectors = [
            "[data-automation-id='declineToSelfIdentify']",
            "input[value='I don\\'t wish to answer']",
            "input[value='Decline to Self Identify']",
        ]
        for selector in decline_selectors:
            self._safe_click(page, selector)

    def _click_next(self, page: Page) -> None:
        """Click the Next button."""
        self._safe_click(page, self.SELECTORS["next_button"])
        self._human_delay(2000, 3000)

    def _submit_application(self, page: Page) -> None:
        """Click the final Submit button."""
        submit_selectors = [
            self.SELECTORS["submit_button"],
            "button:has-text('Submit')",
            "[data-automation-id='submitButton']",
        ]
        for selector in submit_selectors:
            if self._safe_click(page, selector):
                self._human_delay(3000, 5000)
                logger.info("Application submit button clicked")
                return

        raise Exception("Could not find Submit button")

    def scrape_job_details(self, url: str) -> dict:
        """Scrape job details from a Workday posting."""
        page = self._start_browser()
        try:
            page.goto(url, wait_until="networkidle")
            self._human_delay(2000, 3000)

            details = {}

            # Job title
            title_el = page.locator("[data-automation-id='jobPostingHeader']")
            if title_el.count() > 0:
                details["title"] = title_el.first.inner_text().strip()

            # Company
            company_el = page.locator("[data-automation-id='company']")
            if company_el.count() > 0:
                details["company"] = company_el.first.inner_text().strip()

            # Location
            location_el = page.locator("[data-automation-id='locations']")
            if location_el.count() > 0:
                details["location"] = location_el.first.inner_text().strip()

            # Description
            desc_el = page.locator("[data-automation-id='jobPostingDescription']")
            if desc_el.count() > 0:
                details["description"] = desc_el.first.inner_text().strip()[:5000]

            return details
        finally:
            self._close_browser()
