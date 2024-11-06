from typing import Dict, Optional, List, Generator
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from .base_site import BaseSite, WebElementMod
from loguru import logger
import json
import time
from dataclasses import dataclass
from contextlib import contextmanager
from utils.utilities import retry


@dataclass
class Selectors:
    """Centralized selectors for the Microsoft site"""

    LOGIN = {
        "linkedin_button": 'div[aria-label="Sign in with LinkedIn"][role="button"]',
        "sign_in": "//*[text()='Sign in']",
        "username": "username",
        "password": "password",
        "submit": 'button[type="submit"]',
        "authorize": 'button[value="authorize"][name="action"]',
    }

    APPLICATION = {
        "apply_button": 'button[aria-label="Apply"], button[aria-label="Complete application"]',
        "checkmark": 'i[data-icon-name="CheckMark"]',
        "confirm_button": {
            "submit": 'input[value="Submit"]',
            "primary": "ms-Button--primary",
        },
        "modal": "ms-Modal",
        "questions": {
            "row": "iCIMS_TableRow",
            "label": "label",
            "select": "select",
            "textarea": "textarea",
            "checkbox": "input[type='checkbox']",
            "option": "option",
        },
        "iframe": "icims_content_iframe",
        "final_submit": "input[onclick='pageDirtyFlag=false;']",
    }

    JOB_SEARCH = {
        "list_item": 'div[role="listitem"][data-automationid="ListCell"]',
        "description": "WzU5fAyjS4KUVs1QJGcQ",
    }


class MicrosoftSite(BaseSite):
    BASE_URL = "https://careers.microsoft.com"
    LOGIN_URL = "https://login.microsoftonline.com"

    def __init__(self, driver, wait_timeout: int = 10):
        super().__init__(driver)
        self.wait = WebDriverWait(driver, wait_timeout)
        self.selectors = Selectors()
        self.login_required = False

    @contextmanager
    def handle_tab(self):
        """Context manager for handling new tabs"""
        original_tab = self.driver.current_window_handle
        yield
        self.driver.close()
        self.driver.switch_to.window(original_tab)

    @retry()
    def linkedin_login(self) -> None:
        """Handle LinkedIn login process"""
        if not self.driver.get_cookies():
            self.add_cookies()

        if self.is_logged_in():
            return

        try:
            # Find and click LinkedIn button
            linkedin_button = self._get_element(
                By.CSS_SELECTOR, self.selectors.LOGIN["linkedin_button"], 3
            )
            if linkedin_button:
                self._safe_click(linkedin_button)

            # Fill credentials
            username = self._get_element(By.ID, self.selectors.LOGIN["username"], 5)
            if username:
                username.send_keys(self.credentials["username"])
                password = self._get_element(By.ID, self.selectors.LOGIN["password"])
                password.send_keys(self.credentials["password"])
                submit = self._get_element(
                    By.CSS_SELECTOR, self.selectors.LOGIN["submit"]
                )
                self._safe_click(submit)
                time.sleep(4)
                while (
                    "resend" in self.driver.page_source.lower()
                    or "security check" in self.driver.page_source.lower()
                ):
                    logger.info("Waiting for LinkedIn to authorize...")
                    time.sleep(5)
            # Handle authorization if needed
            authorize = self._get_element(
                By.CSS_SELECTOR, self.selectors.LOGIN["authorize"], 5
            )
            if authorize:
                self._safe_click(authorize)

            if self.is_logged_in():
                self.save_cookies()

        except Exception as e:
            logger.error(f"LinkedIn login failed: {str(e)}")

    def login(self) -> None:
        try:
            self.linkedin_login()

        except Exception as e:
            logger.error(f"Failed to log in with LinkedIn: {str(e)}")

    @retry()
    def _handle_questions(self, form_element) -> None:
        """Handle application form questions"""
        rows = form_element._get_elements(
            By.CSS_SELECTOR,
            f'div[class="{self.selectors.APPLICATION["questions"]["row"]} "]',
        )

        for row in rows:
            try:
                question = row._get_element(
                    By.TAG_NAME, self.selectors.APPLICATION["questions"]["label"]
                ).text

                # Handle different input types
                if select := row._get_element(
                    By.TAG_NAME, self.selectors.APPLICATION["questions"]["select"]
                ):
                    if self.response_data:
                        Select(select).select_by_value(
                            self.response_data.get(question, "Yes")
                        )
                        continue

                    options: List[WebElementMod] = select._get_elements(
                        By.TAG_NAME, self.selectors.APPLICATION["questions"]["option"]
                    )
                    clean_options = [
                        opt.get_attribute("value")
                        for opt in options
                        if opt.get_attribute("value")
                    ]
                    self.questions.append(
                        {
                            "question": question,
                            "type": "options",
                            "options": clean_options,
                        }
                    )

                elif textarea := row._get_element(
                    By.TAG_NAME, self.selectors.APPLICATION["questions"]["textarea"]
                ):
                    if self.response_data:
                        ans = self.response_data.get(question, "Yes I do")
                        textarea.send_keys(ans)
                        continue

                    self.questions.append({"question": question, "type": "text"})
                elif checkbox := row._get_elements(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["questions"]["checkbox"]
                ):
                    for box in checkbox:
                        box.click()

                    self.questions.append({"question": question, "type": "text"})
            except Exception as e:
                logger.error(e)

    def apply_to_job(self, job_url: str) -> None:
        """Apply to a job posting"""
        for _ in self.get_all_jobs(job_url):
            try:
                apply_button = self._get_element(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["apply_button"]
                )
                if apply_button and not self.is_logged_in():
                    self._safe_click(apply_button)
                    time.sleep(4)
                    self.login()
                    apply_button = self._get_element(
                        By.CSS_SELECTOR, self.selectors.APPLICATION["apply_button"]
                    )

                if apply_button:
                    self._safe_click(apply_button)
                    self._fill_application()

            except Exception as e:
                logger.error(f"Application failed: {str(e)}")

        return

    def get_all_jobs(self, job_url: str) -> Generator:
        """Get all matching jobs"""
        base_url = "https://jobs.careers.microsoft.com/global/en/search"
        params = "?lc=India&d=Software%20Engineering&l=en_us&pgSz=20&o=Recent"
        page = 1
        if urlparse(job_url).netloc:
            self.driver.get(job_url)
            yield job_url
            return
        while page < 21:
            self.driver.get(f"{base_url}{params}&pg={page}")
            self.wait_for_page_load()

            job = self._get_element(
                By.CSS_SELECTOR, self.selectors.JOB_SEARCH["list_item"], timeout=10
            )
            jobs: List[WebElementMod] = self._get_elements(
                By.CSS_SELECTOR, self.selectors.JOB_SEARCH["list_item"]
            )
            for job in jobs:
                try:
                    job_link = job._get_element(By.TAG_NAME, "button")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView();", job_link
                    )
                    if self._safe_click(job_link):
                        self.wait_for_page_load()

                        if self._should_apply_to_job():
                            yield job

                except Exception as e:
                    logger.error(f"Failed to process job: {str(e)}")
                    break
            else:
                page += 1

    def _should_apply_to_job(self) -> bool:
        """Determine if we should apply to this job"""
        try:
            if self.driver.current_url in self.get_processed:
                return False
            description = self._get_element(
                By.CLASS_NAME, self.selectors.JOB_SEARCH["description"]
            )
            if description:
                match = self.get_match_report(description.text)
                if match and "matching_percent" in match:
                    return True
                else:
                    self.save_processed()

        except Exception as e:
            logger.error(f"Failed to check job match: {str(e)}")
        return False

    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        try:
            return bool(
                self._get_elements(By.XPATH, "//*[contains(text(), 'Account manager')]")
            )
        except Exception:
            return False

    def _click_confirm_button(self) -> bool:
        """Click confirm/submit button with fallback options"""
        try:
            # Try primary submit button
            submit_buttons = self._get_elements(
                By.CSS_SELECTOR, self.selectors.APPLICATION["confirm_button"]["submit"]
            )
            primary_buttons = self._get_elements(
                By.CLASS_NAME, self.selectors.APPLICATION["confirm_button"]["primary"]
            )

            confirm_buttons = submit_buttons + primary_buttons
            if confirm_buttons and self._safe_click(confirm_buttons[0]):
                time.sleep(2)

                # Handle modal if present
                modal = self._get_elements(
                    By.CLASS_NAME, self.selectors.APPLICATION["modal"]
                )
                if modal:
                    submit_buttons = self._get_elements(
                        By.CSS_SELECTOR,
                        self.selectors.APPLICATION["confirm_button"]["submit"],
                    )
                    primary_buttons = self._get_elements(
                        By.CLASS_NAME,
                        self.selectors.APPLICATION["confirm_button"]["primary"],
                    )
                    confirm_buttons = submit_buttons + primary_buttons
                    if confirm_buttons:
                        self._safe_click(confirm_buttons[-1])
            return True
        except Exception as e:
            logger.error(f"Error clicking confirm button: {str(e)}")
            return False

    def _fill_application(self) -> bool:
        """
        Fill out the complete job application form
        Returns True if successful, False otherwise
        """
        original_tab = self.driver.current_window_handle

        try:
            if not self._switch_to_application_tab(original_tab):
                return False

            job_id = self._get_job_id()

            # Execute application steps in sequence
            steps = [
                self._handle_initial_checkmarks,
                self._handle_authorization_questions,
                self._handle_question_pages,
                self._handle_iframe_questions,
            ]

            for step in steps:
                if not step():
                    logger.error(f"Failed at step: {step.__name__}")
                    return False
                if "linkedin" in self.driver.current_url:
                    self.login()

            self._take_completion_screenshot(job_id)
            return True

        except Exception as e:
            logger.error(f"Error in application process: {str(e)}")
            return False

        finally:
            self._return_to_original_tab(original_tab)

    def _switch_to_application_tab(self, original_tab: str) -> bool:
        """Switch to the new application tab"""
        new_tabs = [tab for tab in self.driver.window_handles if tab != original_tab]
        if not new_tabs:
            logger.error("No new tab found")
            return False

        self.driver.switch_to.window(new_tabs[0])
        self.wait_for_page_load()
        time.sleep(4)
        return True

    def _get_job_id(self) -> str:
        """Extract job ID from URL or generate timestamp-based ID"""
        try:
            return self.driver.current_url.split("Job_id=")[1].split("&")[0]
        except Exception:
            return str(int(time.time()))

    def _handle_initial_checkmarks(self) -> bool:
        """Handle initial checkmark selections"""
        try:
            checkmarks = self._get_elements(
                By.CSS_SELECTOR, self.selectors.APPLICATION["checkmark"]
            )
            for element in checkmarks:
                self._safe_click(element)
            time.sleep(1)
            return self._click_confirm_button()
        except Exception as e:
            logger.error(f"Error handling checkmarks: {str(e)}")
            return False

    @retry()
    def _handle_authorization_questions(self) -> bool:
        """Handle authorization page questions"""
        logger.info("Handling Authorization page")
        time.sleep(4)

        auth_questions = {
            "isLegallyAuthorized-option": "Yes",
            "isImmigrationBenefitEligible": "No",
        }

        try:
            for field_id, answer in auth_questions.items():
                dropdown = self._get_element(By.ID, field_id)
                if dropdown:
                    self._safe_click(dropdown)
                    option = self._get_element(By.XPATH, f"//span[text()='{answer}']")
                    if option:
                        self._safe_click(option)
            return self._click_confirm_button()
        except Exception as e:
            logger.error(f"Error handling authorization questions: {str(e)}")
            return False

    @retry()
    def _handle_question_pages(self) -> bool:
        """Handle multiple pages of questions"""
        time.sleep(1)
        for page in range(5):
            if self._get_elements(By.TAG_NAME, "iframe"):
                return True

            try:
                if "linkedin" in self.driver.current_url:
                    self.login()

                if not self._process_question_page():
                    return False

                # Check for final submit button
                final_submit = self._get_elements(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["final_submit"]
                )
                if final_submit:
                    return self._safe_click(final_submit[0])

            except Exception as e:
                logger.error(f"Error handling question page {page}: {str(e)}")
                return False

        return True

    def _process_question_page(self) -> bool:
        """Process a single page of questions"""
        question_divs = self._get_elements(By.CLASS_NAME, "iCIMS_TableRow")[:-1]
        if not question_divs:
            return True

        for div in question_divs:
            try:
                if not self._handle_single_question(div):
                    return False
            except StaleElementReferenceException:
                continue

        return self._click_confirm_button()

    def _handle_single_question(self, div: WebElementMod) -> bool:
        """Handle a single question element"""
        question = div._get_element(By.TAG_NAME, "label").text

        # Handle different input types
        if select_elements := div._get_elements(By.TAG_NAME, "select"):
            return self._handle_select_question(select_elements[0], question, div)
        elif text_areas := div._get_elements(By.TAG_NAME, "textarea"):
            return self._handle_text_question(text_areas[0], question)
        elif checkboxes := div._get_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
            return self._handle_checkbox_question(checkboxes)

        return True

    def _handle_select_question(
        self, select_element, question: str, div: WebElementMod
    ) -> bool:
        """Handle dropdown select questions"""
        options = div._get_elements(By.TAG_NAME, "option")
        clean_options = [
            opt.get_attribute("value") for opt in options if opt.get_attribute("value")
        ]
        answer = self.get_answers(
            [{"question": question, "type": "options", "options": clean_options}]
        )
        if answer:
            Select(select_element).select_by_value(answer.get("answers", ["yes"])[0])
        return True

    def _handle_text_question(self, text_area, question: str) -> bool:
        """Handle text input questions"""
        answer = self.get_answers([{"question": question, "type": "text"}])
        if answer:
            text_area.send_keys(answer.get("answers", ["Yes I do"])[0])
        return True

    def _handle_checkbox_question(self, checkboxes) -> bool:
        """Handle checkbox questions"""
        for checkbox in checkboxes:
            checkbox.click()
        return True

    def _handle_iframe_questions(self) -> bool:
        """Handle questions within iFrame"""
        if (
            not self._get_element(By.TAG_NAME, "iframe", 10)
            or "Your application has been submitted" in self.driver.page_source
        ):
            return True

        try:
            self.driver.switch_to.frame(self.selectors.APPLICATION["iframe"])

            if not self._handle_government_question():
                return False

            form = self._get_element(By.CSS_SELECTOR, 'form[name="questions"]', 10)
            if form:
                self._handle_questions(form)
                if self.questions:
                    self.get_answers()
                self._handle_questions(form)
                return self._click_confirm_button()

            return True

        except Exception as e:
            logger.error(f"Error handling iframe questions: {str(e)}")
            return False

    def _handle_government_question(self) -> bool:
        """Handle specific government employment question"""
        max_tries = 0
        submit_button = self._get_element(
            By.XPATH, '//*[@id="quesp_form_submit_i"]', 10
        )
        while (
            "Are you currently employed by a government" in self.driver.page_source
            and max_tries < 5
        ):
            if submit_button:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView();", submit_button
                )
                self._safe_click(submit_button)
                time.sleep(3)
            max_tries += 1
            time.sleep(2)

        return max_tries < 5

    def _take_completion_screenshot(self, job_id: str) -> None:
        """Take screenshot of completed application"""
        try:
            self.save_screenshot(job_id)
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")

    def _return_to_original_tab(self, original_tab: str) -> None:
        """Return to original tab and close application tab"""
        try:
            self.driver.close()
            self.driver.switch_to.window(original_tab)
        except Exception as e:
            logger.error(f"Error closing application tab: {str(e)}")
