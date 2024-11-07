import datetime
import json
import time
from typing import Optional, Generator
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from .base_site import BaseSite, WebElementMod
from core.exceptions import ApplicationException
from loguru import logger
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from utils.utilities import extract_numbers, retry, timeout


metadata = json.loads(open("data/metadata.json").read())


@dataclass
class Selectors:
    """Centralized selectors for LinkedIn"""

    LOGIN = {
        "username": "username",  # id
        "password": "password",  # id
        "submit": '//*[@aria-label="Sign in"]',  # xpath
    }
    APPLICATION = {
        "jobs_list_item": "jobs-search-results__list-item",  # class
        "job_card": "job-card-container--clickable",  # class
        "easy_apply_div": "jobs-apply-button--top-card",  # class
        "submit_application": 'button[aria-label="Submit application"]',  # css
        "next_btn": "button[aria-label='Continue to next step']",  # css
        "review_btn": "button[aria-label='Review your application']",  # css
        "close_btn": "button[aria-label='Dismiss']",  # css
        "job_description": "article",  # tag
        "form": {
            "modal": 'div[role="dialog"]',  # css
            "section": "jobs-easy-apply-form-section__grouping",  # class
            "input_types": {"text": "text", "autocomplete": "list"},
            "dropdown_options": "basic-typeahead__selectable",  # class
            "error": "artdeco-inline-feedback__message",
        },
    }
    PROFILE = {
        "nav_menu": "global-nav-search",  # id
    }


class LinkedInSite(BaseSite):
    BASE_URL = "https://www.linkedin.com"
    LOGIN_URL = f"{BASE_URL}/login"

    def __init__(self, driver, wait_timeout: int = 2):
        super().__init__(driver)
        self.wait = WebDriverWait(driver, wait_timeout)
        self.selectors = Selectors()

    @retry()
    def login(self) -> None:
        """Login to LinkedIn using provided credentials"""
        try:
            logger.info("Attempting to login to LinkedIn")
            self.driver.get(self.LOGIN_URL)

            if self.add_cookies():
                self.wait_for_page_load()
                if self.is_logged_in():
                    logger.info("Successfully logged in using cookies")
                    return

            # Fill credentials
            if username_field := self._get_element(
                By.ID, self.selectors.LOGIN["username"]
            ):
                username_field.send_keys(self.credentials["username"])

                if password_field := self._get_element(
                    By.ID, self.selectors.LOGIN["password"]
                ):
                    password_field.send_keys(self.credentials["password"])

                    if submit_btn := self._get_element(
                        By.XPATH, self.selectors.LOGIN["submit"]
                    ):
                        self._safe_click(submit_btn)
                while (
                    "resend" in self.driver.page_source.lower()
                    or "security check" in self.driver.page_source.lower()
                ):
                    logger.info("Waiting for LinkedIn to authorize...")
                    time.sleep(5)

            # Verify login success
            if nav_bar := self._get_element(By.ID, self.selectors.PROFILE["nav_menu"]):
                logger.info("Successfully logged in to LinkedIn")
                self.save_cookies()
            else:
                raise ApplicationException("Login verification failed")

        except Exception as e:
            raise ApplicationException(f"LinkedIn login failed: {str(e)}")

    def is_logged_in(self) -> bool:
        """Check if user is currently logged in"""
        try:
            return bool(
                self._get_element(
                    By.ID, self.selectors.PROFILE["nav_menu"], 5),
            )
        except Exception:
            return False

    def apply_to_job(self, job_url: str) -> None:
        """Apply to a job posting"""
        for _ in self.get_all_jobs(job_url):
            try:
                if easy_apply_div := self._get_element(
                    By.CLASS_NAME, self.selectors.APPLICATION["easy_apply_div"]
                ):
                    if easy_apply_btn := easy_apply_div._get_element(
                        By.TAG_NAME, "button"
                    ):
                        self._safe_click(easy_apply_btn)
                        self._get_form_fields(checking=True)
                        if self.questions:
                            self.get_answers()
                            self._get_form_fields()

            except Exception as e:
                logger.error(f"Error applying to job: {str(e)}")
            finally:
                try:
                    if close_button := self._get_element(
                        By.CSS_SELECTOR, self.selectors.APPLICATION["close_btn"]
                    ):
                        close_button.click()
                except ElementClickInterceptedException:
                    self._safe_click(close_button)
                except Exception as e:
                    logger.info("Unable to close the modal")

                if modal := self._get_element(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["form"]["modal"]
                ):
                    self.driver.refresh()
                self.response_data = {}

    def get_all_jobs(self, job_url: str) -> Generator:
        """Get all matching jobs from LinkedIn"""
        if urlparse(job_url).netloc:
            self.driver.get(job_url)
            yield job_url
            return

        base_url = "https://www.linkedin.com/jobs/search/"
        params = "?f_AL=true&geoId=102713980&f_TPR=r86400"

        for page in range(21):
            try:
                self.driver.get(f"{base_url}{params}&start={page*25}")
                job_card = self._get_element(
                    By.CLASS_NAME, self.selectors.APPLICATION["jobs_list_item"], 5
                )
                job_cards = self._get_elements(
                    By.CLASS_NAME, self.selectors.APPLICATION["jobs_list_item"]
                )
                card_number = 0
                while card_number < 25:
                    try:
                        job = self._process_job_card(job_cards[card_number])
                        if job:
                            yield job
                        card_number += 1
                    except StaleElementReferenceException as e:
                        logger.error("Stale element reference exception")
                        job_cards = self._get_elements(
                            By.CLASS_NAME, self.selectors.APPLICATION["jobs_list_item"]
                        )
                    except Exception as e:
                        logger.error(f"Error processing job card: {str(e)}")
                        continue

            except Exception as e:
                logger.warning(f"Error on page {page}: {str(e)}")

    def _process_job_card(self, card: WebElementMod) -> Optional[WebElementMod]:
        """Process a single job card"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView();", card)
            job_card = card._get_element(
                By.CLASS_NAME, self.selectors.APPLICATION["job_card"]
            )

            if "Applied" in job_card.text:
                return None

            self._safe_click(job_card)
            self.wait_for_page_load()

            if not (
                job_description := self._get_element(
                    By.TAG_NAME, self.selectors.APPLICATION["job_description"], 5
                )
            ):
                return None

            if not (
                easy_apply_div := self._get_element(
                    By.CLASS_NAME, self.selectors.APPLICATION["easy_apply_div"]
                )
            ):
                return None

            match = self.get_match_report(job_description.text)
            if not match:
                return None
            logger.info(f"Matching percentage is {match}%")
            return job_card
        except StaleElementReferenceException as e:
            raise StaleElementReferenceException(
                f"Stale element reference error: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Error processing job card: {str(e)}")
            return None

    def _handle_form_section(self, section: WebElementMod) -> None:
        """Handle a single form section"""

        try:
            try:
                question = section._get_element(By.TAG_NAME, "label").text
            except NoSuchElementException as e:
                question = (
                    section._get_element(
                        By.XPATH, "./preceding-sibling::*[2]").text
                    + section._get_element(By.XPATH,
                                           "./preceding-sibling::*[1]").text
                )
            if fieldsets := section._get_elements(By.TAG_NAME, "fieldset"):
                try:
                    question = section._get_element(By.TAG_NAME, "legend").text
                except NoSuchElementException as e:
                    question = (
                        section._get_element(
                            By.XPATH, "./preceding-sibling::*[2]").text
                        + section._get_element(
                            By.XPATH, "./preceding-sibling::*[1]"
                        ).text
                    )
                self._handle_fieldset_field(fieldsets[0], question)
            elif inputs := section._get_elements(By.TAG_NAME, "input"):
                self._handle_input_field(inputs[0], question)
            elif text_boxes := section._get_elements(By.TAG_NAME, "textarea"):
                self._handle_text_box_field(text_boxes[0], question)
            elif selects := section._get_elements(By.TAG_NAME, "select"):
                self._handle_select_field(selects[0], question)

        except Exception as e:
            logger.error(f"Error handling form section: {str(e)}")

    def _handle_autocomplete_input(
        self, input_field: WebElementMod, answer_text: str
    ) -> bool:
        """
        Handle autocomplete input field
        Args:
            input_field: The input WebElement
            answer: The answer dictionary containing value/text
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the answer text

            # Send keys to input field
            input_field.send_keys(answer_text)
            time.sleep(1)  # Wait for autocomplete suggestions

            # Update input value and trigger events
            self.driver.execute_script(
                """
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """,
                input_field,
                answer_text,
            )

            # Find the parent section and look for dropdown options
            parent_section = input_field._get_element(
                By.XPATH,
                "./ancestor::div[contains(@class, 'jobs-easy-apply-form-section__grouping')]",
            )
            dropdown_options = parent_section._get_elements(
                By.CLASS_NAME, self.selectors.APPLICATION["form"]["dropdown_options"]
            )

            if dropdown_options:
                # Try to find exact match first
                for option in dropdown_options:
                    if option.text.lower() == answer_text.lower():
                        return self._safe_click(option)

                # If no exact match, click first option
                return self._safe_click(dropdown_options[0])

            # If no dropdown appears but input accepted, return success
            return True

        except Exception as e:
            logger.error(f"Error handling autocomplete input: {str(e)}")
            try:
                # Fallback: try to just set the value directly
                self.driver.execute_script(
                    "arguments[0].value = arguments[1];", input_field, answer_text
                )
                return True
            except Exception as e2:
                logger.error(
                    f"Fallback for autocomplete input failed: {str(e2)}")
                return False

    def _handle_input_field(self, input_field: WebElementMod, question: str) -> bool:
        """Handle input field in form"""
        if self.response_data and question not in self.response_data:
            return True
        try:
            if (
                input_field.get_attribute("value")
                and input_field.get_attribute("value") != "1"
            ) or not input_field.get_property("required"):
                return True
            answer_text = metadata.get(question.replace("\n", "").lower(), "")
            if not self.response_data and not answer_text:
                self.questions.append({"question": question, "type": "text"})
                try:
                    self._handle_autocomplete_input(input_field, "1")
                except Exception as e:
                    input_field.send_keys(0)
                if error := self._get_element(
                    By.CLASS_NAME, self.selectors.APPLICATION["form"]["error"]
                ):
                    if "mm/dd/yyyy" in error.text:
                        date = datetime.datetime.now().strftime("%x")
                        input_field.send_keys(date)
                return True

            if not answer_text:
                answer_text = self.response_data.get(question, " ")
                input_field.clear()

            if answer_text:
                if (
                    input_field.get_attribute("type")
                    == self.selectors.APPLICATION["form"]["input_types"]["text"]
                ):
                    if (
                        input_field.get_attribute("aria-autocomplete")
                        == self.selectors.APPLICATION["form"]["input_types"][
                            "autocomplete"
                        ]
                    ):
                        self._handle_autocomplete_input(
                            input_field, answer_text)
                    else:
                        input_field.send_keys(answer_text)
                if error := self._get_element(
                    By.CLASS_NAME, self.selectors.APPLICATION["form"]["error"]
                ):
                    input_field.clear()

                    if "mm/dd/yyyy" in error.text:
                        date = datetime.datetime.now().strftime("%x")
                        input_field.send_keys(date)
                    elif error.text:
                        input_field.send_keys(extract_numbers(answer_text))
                    else:
                        input_field.send_keys(0)

                return True
        except Exception as e:
            logger.error(f"Error handling input field: {str(e)}")
        return False

    def _handle_text_box_field(self, text_box: WebElementMod, question: str) -> bool:
        """Handle input field in form"""
        if self.response_data and question not in self.response_data:
            return True
        try:
            if (
                text_box.get_attribute("value")
                and text_box.get_attribute("value") != "0"
            ) or not text_box.get_property("required"):
                return True
            answer_text = metadata.get(question.replace("\n", "").lower(), "")
            if not self.response_data and not answer_text:
                self.questions.append({"question": question, "type": "text"})
                text_box.send_keys(0)
                return True

            if not answer_text:
                answer_text = self.response_data.get(question, "")
                text_box.clear()

            text_box.send_keys(answer_text)

            return True
        except Exception as e:
            logger.error(f"Error handling input field: {str(e)}")
        return False

    def _handle_select_field(self, select_field: WebElementMod, question: str) -> bool:
        """Handle select field in form"""
        try:
            if (
                not self.response_data
                and "select" not in select_field.get_attribute("value").lower()
            ):
                return True

            if self.response_data and question not in self.response_data:
                return True

            options = select_field._get_elements(By.TAG_NAME, "option")
            clean_options = [
                opt.get_attribute("value")
                for opt in options
                if opt.get_attribute("value") != "Select an option"
            ]
            if not self.response_data:
                self.questions.append(
                    {"question": question, "type": "options",
                        "options": clean_options}
                )
                for value in [
                    "Yes",
                    options[-1].get_attribute("value"),
                ]:
                    try:
                        Select(select_field).select_by_value(value)
                        return True
                    except Exception:
                        continue
                return True

            if answer := self.response_data.get(question):
                for value in [
                    answer,
                    "Yes",
                    options[1].get_attribute("value"),
                ]:
                    try:
                        Select(select_field).select_by_value(value)
                        return True
                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"Error handling select field: {str(e)}")
        return False

    def _handle_fieldset_field(self, fieldset: WebElementMod, question: str) -> bool:
        """Handle select field in form"""
        if self.response_data and question not in self.response_data:
            return True
        try:
            options = [
                {"component": opt, "text": opt.text}
                for opt in fieldset._get_elements(By.TAG_NAME, "label")
            ]
            clean_options = [opt["text"] for opt in options]

            if not self.response_data:
                self.questions.append(
                    {"question": question, "type": "options",
                        "options": clean_options}
                )
                for option in options:
                    try:
                        option["component"].click()
                        return True
                    except Exception as e4:
                        logger.error(
                            f"Error handling fieldset field: {str(e4)}")
                    return True

            answer_text = metadata.get(question.replace("\n", "").lower(), "")
            if not answer_text:
                answer_text = self.response_data.get(question, " ")

            if answer_text:
                for value in [
                    answer_text,
                    "Yes",
                    options[0],
                ]:
                    try:
                        for option_all in options:
                            try:
                                if option_all["text"] == value:
                                    option_all["component"].click()

                                    return True

                            except StaleElementReferenceException as e2:
                                logger.error(
                                    f"Error handling fieldset field: {str(e2)}"
                                )
                                raise StaleElementReferenceException(
                                    "Stale element reference"
                                )
                            except Exception as e3:
                                logger.error(
                                    f"Error handling fieldset field: {str(e3)}"
                                )
                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"Error handling select field: {str(e)}")

    @timeout(100)
    def _get_form_fields(self, checking=False) -> None:
        """Fill out the complete application form"""
        try:
            if modal := self._get_element(
                By.CSS_SELECTOR, self.selectors.APPLICATION["form"]["modal"]
            ):
                self.wait_for_page_load()
                while self.next_button():
                    pb4s = modal._get_elements(By.CLASS_NAME, "pb4")
                    for pb4 in pb4s:
                        if h3 := pb4._get_element(By.TAG_NAME, "h3"):
                            if h3.text == "Resume":
                                continue
                        self.wait_for_page_load()

                        for section in pb4._get_elements(
                            By.CLASS_NAME, self.selectors.APPLICATION["form"]["section"]
                        ):
                            self._handle_form_section(section)
                    next_button = self.next_button()
                    if (
                        checking
                        and next_button
                        and next_button.text == "Submit application"
                        and self.questions
                    ):
                        while back_button := self.back_button():
                            self._safe_click(back_button)

                        return True
                    self._safe_click(self.next_button())

        except Exception as e:
            logger.error(f"Error filling form fields: {str(e)}")

    def _save_application_screenshot(self) -> None:
        """Save screenshot of completed application"""
        try:
            parsed_url = urlparse(self.driver.current_url)
            query_params = parse_qs(parsed_url.query)
            job_id = query_params.get("postApplyJobId", [None])[0]
            return self.save_screenshot(job_id)
        except Exception as e:
            logger.error(f"Error saving application screenshot: {str(e)}")

    def next_button(
        self, footer: Optional[WebElementMod] = None
    ) -> Optional[WebElementMod]:
        """Get the next button from footer or modal"""
        try:
            if footer:
                buttons = footer._get_elements(By.TAG_NAME, "button")
                return buttons[-1] if buttons else None
            raise StaleElementReferenceException("No footer found")
        except StaleElementReferenceException as e:
            try:
                if modal := self._get_element(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["form"]["modal"]
                ):
                    footer = modal._get_element(By.TAG_NAME, "footer")
                    if not footer:
                        return None
                    buttons = footer._get_elements(By.TAG_NAME, "button")
                    return buttons[-1] if buttons else None
            except Exception as e:
                logger.error(f"{str(e)}")

        except Exception as e:
            logger.error(f"Error finding next button: {str(e)}")
            return None

    def back_button(
        self, footer: Optional[WebElementMod] = None
    ) -> Optional[WebElementMod]:
        """Get the next button from footer or modal"""
        try:
            if footer:
                buttons = footer._get_elements(By.TAG_NAME, "button")
                return buttons[0] if len(buttons) > 1 else None
            raise StaleElementReferenceException("No footer found")
        except StaleElementReferenceException as e:
            try:
                if modal := self._get_element(
                    By.CSS_SELECTOR, self.selectors.APPLICATION["form"]["modal"]
                ):
                    footer = modal._get_element(By.TAG_NAME, "footer")
                    buttons = footer._get_elements(By.TAG_NAME, "button")
                    return buttons[0] if len(buttons) > 1 else None
            except Exception as e:
                logger.error(f"{str(e)}")

        except Exception as e:
            logger.error(f"Error finding next button: {str(e)}")
            return None
