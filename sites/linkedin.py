import time
from typing import Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from .base_site import BaseSite
from core.exceptions import ApplicationException
from loguru import logger
from selenium.webdriver.remote.webelement import WebElement
from urllib.parse import urlparse, parse_qs


class LinkedInSite(BaseSite):
    BASE_URL = "https://www.linkedin.com"
    LOGIN_URL = f"{BASE_URL}/login"
    COOKIE_FILE = "cookie_file.json"

    # Selectors
    SELECTORS = {
        "login": {
            "username": "username",  # id
            "password": "password",  # id
            "submit": '//*[@aria-label="Sign in"]',  # xpath
        },
        "application": {
            "jobs_list_item": "jobs-search-results__list-item",  # class
            "easy_apply_div": "jobs-apply-button--top-card",  #  class
            "submit_application": 'button[aria-label="Submit application"]',  # css
            "next_btn": "button[aria-label='Continue to next step']",  # css
            "review_btn": "button[aria-label='Review your application']",  # css
            "close_btn": "button[aria-label='Dismiss']",  # css
            "form_fields": {
                "phone": "input[id*='phoneNumber']",  # css
                "resume": "input[name='resume']",  # css
                "experience": "input[id*='experience']",  # css
            },
        },
        "profile": {
            "nav_menu": "global-nav-search",  # id
        },
    }

    def __init__(self, driver, wait_timeout: int = 10):
        super().__init__(driver)
        self.wait = WebDriverWait(driver, wait_timeout)

    def login(self) -> None:
        """Login to LinkedIn using provided credentials"""
        try:
            logger.info("Attempting to login to LinkedIn")
            self.driver.get(self.LOGIN_URL)
            if self.add_cookies():
                return

            # Wait for and fill username
            username_field = self._get_element(
                By.ID, self.SELECTORS["login"]["username"]
            )

            if username_field:
                username_field.send_keys(self.credentials["username"])

                # Fill password
                password_field = self._get_element(
                    By.ID, self.SELECTORS["login"]["password"]
                )
                password_field.send_keys(self.credentials["password"])

                # Submit login form
                submit_btn = self._get_element(
                    By.XPATH, self.SELECTORS["login"]["submit"]
                )
                submit_btn.click()

            # Wait for navigation menu to confirm successful login
            nav_bar = self._get_element(By.ID, self.SELECTORS["profile"]["nav_menu"])
            if nav_bar:
                logger.info("Successfully logged in to LinkedIn")
            self.save_cookies()
        except (TimeoutException, NoSuchElementException) as e:
            raise ApplicationException(f"LinkedIn login failed: {str(e)}")

    def is_logged_in(self) -> bool:
        """Check if user is currently logged in to LinkedIn"""
        try:
            return bool(
                self.driver.find_element(By.ID, self.SELECTORS["profile"]["nav_menu"])
            )
        except NoSuchElementException:
            return False

    def get_all_jobs(self, job_url):
        """Get all jobs from a given LinkedIn job page URL"""
        try:
            base_url = "https://www.linkedin.com/jobs/search/"
            params = "?f_AL=true"
            page = 0

            if urlparse(job_url).netloc:
                self.driver.get(job_url)
                yield job_url
                return
            while page < 21:
                try:
                    self.driver.get(f"{base_url}{params}&start={page*25}")
                    job_cards = self._get_elements(
                        By.CLASS_NAME, self.SELECTORS["application"]["jobs_list_item"]
                    )

                    for i in range(25):
                        try:
                            try:
                                card = job_cards[i]
                                job_card = card.find_elements(
                                    By.CLASS_NAME, "job-card-container--clickable"
                                )
                            except StaleElementReferenceException as e:
                                job_cards = self._get_elements(
                                    By.CLASS_NAME,
                                    self.SELECTORS["application"]["jobs_list_item"],
                                )
                                card = job_cards[i]
                                job_card = card.find_elements(
                                    By.CLASS_NAME, "job-card-container--clickable"
                                )
                            finally:
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView();", job_card[0]
                                )

                            if "Applied" in job_card[0].text:
                                continue

                            if job_card:
                                job_card[0].click()
                                self.wait_for_page_load()
                                time.sleep(3)
                                job_description = self._get_element(
                                    By.TAG_NAME, "article"
                                ).text
                                if not job_description:
                                    continue

                                easy_apply_div = self._get_element(
                                    By.CLASS_NAME,
                                    self.SELECTORS["application"]["easy_apply_div"],
                                )

                                if not easy_apply_div:
                                    continue

                                match = self.get_match_report(job_description)[
                                    "matching_percent"
                                ]
                                if not match or int(match.replace("%", "")) < 60:
                                    continue

                                yield job_card[0]
                        except NoSuchElementException as e:
                            logger.warning(
                                f"No job link found on page {page} of LinkedIn: {str(e)}"
                            )

                        except StaleElementReferenceException as e:
                            logger.warning(
                                f"Stale element reference error on page {page} of LinkedIn:  {str(e)}"
                            )
                            break
                        except Exception as e:
                            logger.error(
                                f"Error getting job links from LinkedIn: {str(e)}"
                            )

                    else:
                        page += 1
                except Exception as e:
                    logger.warning(
                        f"No jobs found on page {page} of LinkedIn:  {str(e)}"
                    )

        except (NoSuchElementException, TimeoutException) as e:
            raise ApplicationException(
                f"Failed to get all jobs from LinkedIn: {str(e)}"
            )
        except Exception as e:
            raise ApplicationException(
                f"Error getting job links from LinkedIn:  {str(e)}"
            )

    def apply_to_job(self, job_url: str) -> None:
        """Apply to a specific job posting on LinkedIn"""
        for _ in self.get_all_jobs(job_url):
            try:
                # Wait until the job card is visible and click it
                job_card = self._get_element(
                    By.CLASS_NAME, self.SELECTORS["application"]["jobs_list_item"]
                )
                if not job_card:
                    logger.warning("No job cards found on LinkedIn")
                    continue

                easy_apply_div = self._get_element(
                    By.CLASS_NAME, self.SELECTORS["application"]["easy_apply_div"]
                )
                easy_apply_btn = easy_apply_div.find_element(By.TAG_NAME, "button")
                easy_apply_btn.click()
                self._fill_form_fields()
                close_button = self._get_element(
                    By.CSS_SELECTOR, self.SELECTORS["application"]["close_btn"]
                )
                close_button.click()

            except (NoSuchElementException, TimeoutException):
                logger.info("No job cards found on LinkedIn")

    def _fill_form_fields(self, metadata: Optional[Dict] = None) -> None:
        """Fill out form fields based on metadata and available fields"""
        metadata = metadata or {}

        # Check for phone number field
        try:
            modal = self._get_element(By.CSS_SELECTOR, 'div[role="dialog"]')
            if modal:
                footer = modal.find_elements(By.TAG_NAME, "footer")[0]
                while self.next_button(footer):
                    next_button = self.next_button(footer)

                    h3 = modal.find_element(By.TAG_NAME, "h3").text
                    if h3 == "Resume":
                        next_button = self.next_button(footer)
                        next_button.click()
                        continue
                    sections = modal.find_elements(
                        By.CLASS_NAME, "jobs-easy-apply-form-section__grouping"
                    )

                    for section in sections:
                        question = section.find_element(By.TAG_NAME, "label").text
                        input = section.find_elements(By.TAG_NAME, "input")
                        select = section.find_elements(
                            By.TAG_NAME,
                            "select",
                        )

                        if input and (input[0].text or input[0].get_attribute("value")):
                            continue
                        elif select and (
                            "select" not in select[0].text.lower()
                            or "select" not in select[0].get_attribute("value").lower()
                        ):
                            continue

                        if input:
                            answer = self.get_answer(question)
                            if answer:
                                if input[0].get_attribute("type") == "text":
                                    if (
                                        input[0].get_attribute("aria-autocomplete")
                                        == "list"
                                    ):
                                        input.send_keys(answer)
                                        input.value = answer
                                        self.driver.execute_script(
                                            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                                            input,
                                        )
                                        options = section.findelements(
                                            By.CLASS_NAME, "basic-typeahead__selectable"
                                        )
                                        if options:
                                            options[0].click()
                                    else:
                                        input[0].send_keys(
                                            answer.get("value", answer.get("text", 0))
                                        )
                        if select:
                            options = select[0].find_elements(By.TAG_NAME, "option")
                            clean_options = [
                                {
                                    "text": opt.text,
                                    "value": opt.get_attribute("value"),
                                }
                                for opt in options
                                if opt.get_attribute("value") != "Select an option"
                            ]
                            answer = self.get_answer(question, clean_options)
                            if answer:
                                try:
                                    Select(select[0]).select_by_value(
                                        answer.get("text", "Yes")
                                    )
                                except Exception as e:
                                    try:
                                        Select(select[0]).select_by_value("Yes")
                                    except Exception as e2:
                                        Select(select[0]).select_by_value(
                                            options[0].get_attribute("value"),
                                        )

                    next_button = self.next_button(footer)
                    if next_button:
                        next_button.click()

                submit_button = self._get_element(
                    By.CSS_SELECTOR, self.SELECTORS["application"]["submit_application"]
                )
                if submit_button:
                    submit_button.click()
                time.sleep(5)

        except NoSuchElementException as e:
            logger.warning("No form fields found on LinkedIn")
        except TimeoutException as e:
            logger.warning("No form fields found on LinkedIn")
        except Exception as e:
            logger.error(f"{str(e)}")
        finally:
            parsed_url = urlparse(self.driver.current_url)
            query_params = parse_qs(parsed_url.query)
            post_apply_job_id = query_params.get("postApplyJobId", [None])[0]

            self.driver.get_full_page_screenshot_as_file(
                f"screenshots/linkedin/{post_apply_job_id}.png"
            )

    def next_button(self, footer: Optional[WebElement] = None) -> bool:
        try:
            if footer:
                return footer.find_elements(By.TAG_NAME, "button")[-1]
            modal = self._get_element(By.CSS_SELECTOR, 'div[role="dialog"]')
            footer = modal.find_element(By.TAG_NAME, "footer")
            next_btn = footer.find_elements(By.TAG_NAME, "button")[-1]
            return next_btn

        except NoSuchElementException as e:
            logger.warning("No next button found on LinkedIn")
        except Exception as e:
            logger.error(f"{str(e)}")
