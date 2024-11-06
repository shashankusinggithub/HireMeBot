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
from .base_site import BaseSite
from loguru import logger
import json
import time
from dataclasses import dataclass
from contextlib import contextmanager


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
    COOKIE_FILE = "cookie_file.json"

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

    def linkedin_login(self) -> None:
        """Handle LinkedIn login process"""
        if not self.driver.get_cookies():
            self.add_cookies()

        if self.is_logged_in():
            return

        try:
            # Find and click LinkedIn button
            linkedin_button = self._get_element(
                By.CSS_SELECTOR, self.selectors.LOGIN["linkedin_button"]
            )
            if linkedin_button:
                self._safe_click(linkedin_button)

            time.sleep(5)  # Wait for LinkedIn form

            # Fill credentials
            username = self._get_element(By.ID, self.selectors.LOGIN["username"])
            if username:
                username.send_keys(self.credentials["username"])
                password = self._get_element(By.ID, self.selectors.LOGIN["password"])
                password.send_keys(self.credentials["password"])
                submit = self._get_element(
                    By.CSS_SELECTOR, self.selectors.LOGIN["submit"]
                )
                self._safe_click(submit)

            while "resend" in self.driver.page_source.lower():
                time.sleep(5)
            time.sleep(5)
            # Handle authorization if needed
            authorize = self._get_element(
                By.CSS_SELECTOR, self.selectors.LOGIN["authorize"]
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

    def _handle_questions(self, form_element) -> None:
        """Handle application form questions"""
        rows = form_element._get_elements(
            By.CSS_SELECTOR,
            f'div[class="{self.selectors.APPLICATION["questions"]["row"]} "]',
        )

        for row in rows:
            question = row._get_element(
                By.TAG_NAME, self.selectors.APPLICATION["questions"]["label"]
            ).text

            # Handle different input types
            if select := row._get_elements(
                By.TAG_NAME, self.selectors.APPLICATION["questions"]["select"]
            ):
                Select(select[0]).select_by_value("Yes")
            elif textarea := row._get_elements(
                By.TAG_NAME, self.selectors.APPLICATION["questions"]["textarea"]
            ):
                answer = self.get_answers([{"question": question, "type": "text"}])
                if answer:
                    textarea[0].send_keys(answer.get("answers", ["yes i do"])[0])
            elif checkbox := row._get_elements(
                By.CSS_SELECTOR, self.selectors.APPLICATION["questions"]["checkbox"]
            ):
                for box in checkbox:
                    box.click()

    def apply_to_job(self, job_url: str) -> None:
        """Apply to a job posting"""
        for _ in self.get_all_jobs(job_url):
            try:
                apply_button = self._get_element(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["apply_button"]
                )
                if apply_button and not self.is_logged_in():
                    self._safe_click(apply_button)
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
            jobs = self._get_elements(
                By.CSS_SELECTOR, self.selectors.JOB_SEARCH["list_item"]
            )
            for job in jobs:
                try:
                    job_link = job._get_element(By.TAG_NAME, "button")
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
            description = self._get_element(
                By.CLASS_NAME, self.selectors.JOB_SEARCH["description"]
            )
            if description:
                match = self.get_match_report(description.text)
                if "matching_percent" in match:
                    return True
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
                        return self._safe_click(confirm_buttons[-1])
            return False
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
            # Switch to new tab
            new_tabs = [
                tab for tab in self.driver.window_handles if tab != original_tab
            ]
            if not new_tabs:
                logger.error("No new tab found")
                return False

            self.driver.switch_to.window(new_tabs[0])
            self.wait_for_page_load()
            time.sleep(4)

            # Get job ID for tracking
            try:
                job_id = self.driver.current_url.split("Job_id=")[1].split("&")[0]
            except Exception:
                job_id = str(int(time.time()))

            # Step 1: Handle initial checkmarks
            try:
                checkmarks = self._get_elements(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["checkmark"]
                )
                for element in checkmarks:
                    self._safe_click(element)
                time.sleep(4)
                self._click_confirm_button()
            except Exception as e:
                logger.error(f"Error handling checkmarks: {str(e)}")

            # Step 2: Handle authorization questions
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
                        option = self._get_element(
                            By.XPATH, f"//span[text()='{answer}']"
                        )
                        if option:
                            self._safe_click(option)
                self._click_confirm_button()
            except Exception as e:
                logger.error(f"Error handling authorization questions: {str(e)}")

            # Step 3: Handle additional questions
            time.sleep(4)
            question_page = 0
            while question_page < 5 and not self._get_elements(By.TAG_NAME, "iframe"):
                try:
                    # Check if we're on LinkedIn page
                    if "linkedin" in self.driver.current_url:
                        self.login()

                    logger.info("Handling question page")
                    question_divs = self._get_elements(By.CLASS_NAME, "iCIMS_TableRow")[
                        :-1
                    ]

                    if question_divs:
                        for div in question_divs:
                            try:
                                question = div._get_element(By.TAG_NAME, "label").text

                                # Handle different input types
                                select_elements = div._get_elements(
                                    By.TAG_NAME, "select"
                                )
                                text_areas = div._get_elements(By.TAG_NAME, "textarea")
                                checkboxes = div._get_elements(
                                    By.CSS_SELECTOR, "input[type='checkbox']"
                                )

                                if select_elements:
                                    options = div._get_elements(By.TAG_NAME, "option")
                                    clean_options = [
                                        opt.get_attribute("value")
                                        for opt in options
                                        if opt.get_attribute("value")
                                    ]
                                    answer = self.get_answers(
                                        [
                                            {
                                                "question": question,
                                                "type": "options",
                                                "options": clean_options,
                                            }
                                        ],
                                    )
                                    if answer:
                                        Select(select_elements[0]).select_by_value(
                                            answer.get("answers", ["yes"])[0]
                                        )

                                elif text_areas:
                                    answer = self.get_answers(
                                        [{"question": question, "type": "text"}]
                                    )
                                    if answer:
                                        text_areas[0].send_keys(
                                            answer.get("answers", ["Yes I do"])[0]
                                        )

                                elif checkboxes:
                                    for checkbox in checkboxes:
                                        checkbox.click()

                            except StaleElementReferenceException:
                                continue

                        self._click_confirm_button()

                    # Check for final submit button
                    final_submit = self._get_elements(
                        By.CSS_SELECTOR, self.selectors.APPLICATION["final_submit"]
                    )
                    if final_submit:
                        self._safe_click(final_submit[0])
                        break

                except Exception as e:
                    logger.error(
                        f"Error handling question page {question_page}: {str(e)}"
                    )

                question_page += 1

            # Step 4: Handle iFrame questions if present
            if (
                self._get_elements(By.TAG_NAME, "iframe")
                and "Your application has been submitted" not in self.driver.page_source
            ):
                try:
                    self.driver.switch_to.frame(self.selectors.APPLICATION["iframe"])

                    # Handle government employment question
                    max_tries = 0
                    while (
                        "Are you currently employed by a government"
                        in self.driver.page_source
                        and max_tries < 5
                    ):
                        submit_button = self._get_element(
                            By.XPATH, '//*[@id="quesp_form_submit_i"]'
                        )
                        if submit_button:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView();", submit_button
                            )
                            self._safe_click(submit_button)
                            time.sleep(3)
                        max_tries += 1

                    if max_tries == 5:
                        raise Exception("Error handling government question")

                    # Handle final form questions
                    form = self._get_element(By.CSS_SELECTOR, 'form[name="questions"]')
                    if form:
                        self._handle_questions(form)
                        self._click_confirm_button()

                except Exception as e:
                    logger.error(f"Error handling iframe questions: {str(e)}")

            # Take screenshot of completed application
            try:
                self.save_screenshot(job_id)
            except Exception as e:
                logger.error(f"Error taking screenshot: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"Error in application process: {str(e)}")
            return False

        finally:
            # Always close the application tab and return to original
            try:
                self.driver.close()
                self.driver.switch_to.window(original_tab)
            except Exception as e:
                logger.error(f"Error closing application tab: {str(e)}")
