import time
from typing import Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)
from .base_site import BaseSite
from core.exceptions import ApplicationException
from loguru import logger
import re
import json
from AI import choose_option
from selenium.webdriver.support.ui import Select


class MicrosoftSite(BaseSite):
    BASE_URL = "https://careers.microsoft.com"
    LOGIN_URL = "https://login.microsoftonline.com"

    SELECTORS = {
        "login": {
            "email": "input[type='email']",  # css
            "password": "input[type='password']",  # css
            "next_btn": "input[type='submit']",  # css
        },
        "application": {
            "apply_btn": "button#apply-button",  # css
            "next_btn": "button#next-button",  # css
            "submit_btn": "button#submit-button",  # css
            "form_fields": {
                "resume": "input#resume-upload",  # css
                "cover_letter": "input#cover-letter-upload",  # css
                "education": "select#education",  # css
                "experience": "textarea#experience",  # css
            },
        },
        "profile": {
            "account_menu": "div.account-menu",  # css
        },
    }

    def is_applicable(self, url: str) -> bool:
        return bool(re.search(self.domain_pattern, url))

    def get_cookies(self):
        try:
            with open("cookie_file.json", "r") as file:
                cookies = json.load(file)
            return cookies.get("microsoft")
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def linkedin_login(self):
        wait = WebDriverWait(self.driver, 10)
        if self.is_logged_in():
            return

        try:
            # Try to find LinkedIn login button
            linkedin_button = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div[aria-label="Sign in with LinkedIn"][role="button"]',
            )[0]
            sign_in = self.driver.find_elements(By.XPATH, "//*[text()='Sign in']")[0]

            if not linkedin_button and sign_in:
                sign_in = self.driver.find_element(By.XPATH, "//*[text()='Sign in']")
                if sign_in:
                    sign_in.click()
                    linkedin_button = wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                'div[aria-label="Sign in with LinkedIn"][role="button"]',
                            )
                        )
                    )

            if linkedin_button:
                linkedin_button.click()
            time.sleep(7)
            username_input = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            if username_input:
                # Fill LinkedIn credentials
                username_input.send_keys(self.credentials["username"])
                time.sleep(2)
                password_input = self.driver.find_element(By.ID, "password")
                password_input.send_keys(self.credentials["password"])

                # Submit login form
                self.driver.find_element(
                    By.CSS_SELECTOR, 'button[type="submit"]'
                ).click()
        except Exception as e:
            logger.error(e)

            # Wait for page to load
        self.wait_for_page_load()

        try:
            # Check for and handle authorization button
            authorize_button = self.driver.find_elements(
                By.CSS_SELECTOR,
                'button[value="authorize"][name="action"]',
            )
            if authorize_button:
                authorize_button[0].click()
        except Exception as e:
            logger.error(e)

    def add_cookies(self):
        cookies = self.get_cookies()
        if cookies:
            # Add cookies to the driver
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Failed to add cookie: {str(e)}")

            self.driver.refresh()

    def save_cookies(self):
        current_cookies = self.driver.get_cookies()
        try:
            with open("cookie_file.json", "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        data["microsoft"] = current_cookies

        with open("cookie_file.json", "w") as f:
            json.dump(data, f, indent=2)

        # Wait for page to fully load
        time.sleep(5)

    def login(self, credentials: Dict[str, str] = None) -> None:
        """Login to Microsoft Careers using provided credentials"""
        wait = WebDriverWait(self.driver, 10)

        for attempt in range(3):
            logger.info(f"Login attempt: {attempt + 1}")
            try:
                # Try to use saved cookies first
                self.add_cookies()
                self.driver.refresh()
                if self.is_logged_in():
                    logger.info("Successfully logged in using cookies")
                    return

                # Click Sign in button
                try:
                    sign_in = wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//*[text()='Sign in']"))
                    )
                    sign_in.click()
                except ElementClickInterceptedException:
                    # If direct click fails, try JavaScript click
                    sign_in = self.driver.find_element(
                        By.XPATH, "//*[text()='Sign in']"
                    )
                    self.driver.execute_script("arguments[0].click();", sign_in)

                time.sleep(5)  # Wait for login options to load

                self.linkedin_login()

                # Save new cookies
                self.save_cookies()

            except Exception as e:
                logger.error(f"Login attempt {attempt + 1} failed: {str(e)}")
                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(3)

            if self.is_logged_in():
                logger.info("Login successful!")
                return

        raise Exception("Failed to login after 3 attempts")

    def is_logged_in(self) -> bool:
        try:
            # Check for "Account manager" text
            account_manager = self.driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'Account manager') or contains(text(), 'Account Manager')]",
            )
            if account_manager:
                logger.info("Found 'Account Manager' text - user is logged in")
                return True

            logger.info("Account Manager text not found - user is not logged in")
            return False

        except Exception as e:
            logger.error(f"Error checking login status: {str(e)}")
            return False

    def apply_to_job(self, job_url: str) -> bool:
        self.wait_for_page_load()

        for _ in self.get_all_jobs():
            try:
                apply_button = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'button[aria-label="Apply"], button[aria-label="Complete application"]',
                )

                if apply_button and not self.is_logged_in():
                    apply_button[0].click()
                    self.linkedin_login()
                    self.wait_for_page_load()

                    apply_button = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        'button[aria-label="Apply"], button[aria-label="Complete application"]',
                    )

                if apply_button:
                    apply_button[0].click()
                    self._fill_application()

            except Exception as e:
                logger.error(f"Application failed: {str(e)}")
        return False

    def switch_new_tab(self):
        original_tab = self.driver.current_window_handle
        new_tab = [tab for tab in self.driver.window_handles if tab != original_tab][0]
        self.driver.switch_to.window(new_tab)

    def _click_confirm_button(self):
        submit_buttons = self.driver.find_elements(
            By.CSS_SELECTOR, 'input[value="Submit"]'
        )
        primary_buttons = self.driver.find_elements(By.CLASS_NAME, "ms-Button--primary")
        confirm_button = submit_buttons + primary_buttons
        if confirm_button:
            confirm_button[0].click()
        else:
            return
        time.sleep(2)

        modal = self.driver.find_elements(By.CLASS_NAME, "ms-Modal")

        if modal:
            submit_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, 'input[value="Submit"]'
            )
            primary_buttons = self.driver.find_elements(
                By.CLASS_NAME, "ms-Button--primary"
            )
            confirm_button = submit_buttons + primary_buttons
            confirm_button[-1].click()

    def _fill_application(self) -> bool:
        original_tab = self.driver.current_window_handle
        self.switch_new_tab()
        self.wait_for_page_load()
        time.sleep(4)
        try:
            job_id = self.driver.current_url.split("Job_id=")[1].split("&")[0]
        except Exception as e:
            logger.error(f"Error getting job ID from URL: {str(e)}")
            job_id = "1234"
        wait = WebDriverWait(self.driver, 10)

        mapper = {
            "isLegallyAuthorized-option": "Yes",
            "isImmigrationBenefitEligible": "No",
        }
        try:
            elements = self.driver.find_elements(
                By.CSS_SELECTOR, 'i[data-icon-name="CheckMark"]'
            )
            for element in elements:
                element.click()
            time.sleep(4)
            self._click_confirm_button()

            logger.info("Handling Authorization page")
            time.sleep(4)

            for key, value in mapper.items():
                drop = self.driver.find_element(By.ID, key)
                drop.click()
                option = wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH, f"//span[text()='{value}']")
                    )
                )
                option.click()
            self._click_confirm_button()
            time.sleep(4)
            question_page = 0
            while (
                not self.driver.find_elements(By.TAG_NAME, "iframe")
                and question_page < 5
            ):
                try:
                    current_url = self.driver.current_url
                    if "linkedin" in current_url:
                        self.linkedin_login()
                    logger.info("Handling other pages")
                    question_divs = self.driver.find_elements(
                        By.CLASS_NAME, "iCIMS_TableRow"
                    )[:-1]
                    if question_divs:
                        for div in question_divs:
                            question = div.find_element(By.TAG_NAME, "label").text
                            select = div.find_elements(By.TAG_NAME, "select")
                            text_area = div.find_elements(By.TAG_NAME, "textarea")
                            checkbox = div.find_elements(
                                By.TAG_NAME, "input[type='checkbox']"
                            )
                            if select:
                                options = div.find_elements(By.TAG_NAME, "option")
                                clean_options = [
                                    {
                                        "text": option.text,
                                        "value": option.get_attribute("value"),
                                    }
                                    for option in options
                                    if option.get_attribute("value")
                                ]
                                answer = self.get_answer(question, clean_options)
                                if answer:
                                    Select(select[0]).select_by_value(answer["value"])

                            elif text_area:
                                text = self.get_answer(question)["text"]
                                text_area[0].send_keys(text)

                            elif checkbox:
                                for option in checkbox:
                                    option.click()
                            else:
                                pass
                    self._click_confirm_button()
                except Exception as e:
                    logger.error(f"Error handling page {str(e)}")
                    final_step = self.driver.find_elements(
                        By.CSS_SELECTOR, "input[onclick='pageDirtyFlag=false;']"
                    )
                    if final_step:
                        final_step[0].click()
                        break
                    time.sleep(4)
                    self._click_confirm_button()
                except Exception as e:
                    logger.error(f"{str(e)}")
                question_page += 1
            logger.info("handeling i frame")
            self.wait_for_page_load()
            time.sleep(4)
            if (
                self.driver.find_elements(By.TAG_NAME, "iframe")
                and "Your application has been submitted" not in self.driver.page_source
            ):
                self.driver.switch_to.frame("icims_content_iframe")
                time.sleep(4)
                max_tries = 0
                while (
                    "Are you currently employed by a government or government agency in any capacity"
                    in self.driver.page_source
                    and max_tries < 5
                ):
                    submit_button = self.driver.find_element(
                        By.XPATH, '//*[@id="quesp_form_submit_i"]'
                    )
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView();", submit_button
                    )

                    submit_button.click()
                    time.sleep(3)
                    max_tries += 1
                if max_tries == 5:
                    raise Exception("Error handling iFrame")

                form = self.driver.find_element(
                    By.CSS_SELECTOR, 'form[name="questions"]'
                )
                rows = form.find_elements(
                    By.CSS_SELECTOR, 'div[class="iCIMS_TableRow "]'
                )

                for row in rows:
                    question = row.find_element(By.TAG_NAME, "label").text
                    select = row.find_elements(By.TAG_NAME, "select")
                    text_area = row.find_elements(By.TAG_NAME, "textarea")
                    checkbox = row.find_elements(
                        By.CSS_SELECTOR, "input[type='checkbox']"
                    )

                    if select:
                        # options = row.find_elements(By.TAG_NAME, "option")
                        # clean_options = [
                        #     {
                        #         "text": option.text,
                        #         "value": option.get_attribute("value"),
                        #     }
                        #     for option in options
                        #     if option.get_attribute("value")
                        # ]

                        # answer = self.get_answer(question, clean_options)
                        # if answer:
                        #     value = answer.get("value", "")
                        #     if not value:
                        #         value = answer.get("text", "")

                        Select(select[0]).select_by_value("Yes")

                    elif text_area:
                        text = self.get_answer(question)
                        if text is not None and len(text):
                            text_area[0].send_keys(text.get("text", "Yes I do"))
                    elif checkbox:
                        for box in checkbox:
                            box.click()
                    else:
                        pass

                self._click_confirm_button()
                time.sleep(4)

            self.driver.get_full_page_screenshot_as_file(f"screenshots/{job_id}.png")
        except Exception as e:
            logger.error(str(e))
        finally:
            self.driver.close()
            self.driver.switch_to.window(original_tab)

    def get_all_jobs(self):
        self.driver.get(
            "https://jobs.careers.microsoft.com/global/en/search?lc=India&d=Software%20Engineering&l=en_us&pg=1&pgSz=20&o=Recent"
        )
        job = self.driver.find_elements(
            By.CSS_SELECTOR,
            'div[role="listitem"][data-automationid="ListCell"]',
        )[0]
        job_link = job.find_element(By.TAG_NAME, "button")
        job_link.click()
        self.wait_for_page_load()

        apply_button = self.driver.find_element(
            By.CSS_SELECTOR,
            'button[aria-label="Apply"], button[aria-label="Complete application"]',
        )
        apply_button.click()
        self.linkedin_login()
        page = 1

        while page <= 20:
            self.driver.get(
                f"https://jobs.careers.microsoft.com/global/en/search?lc=India&d=Software%20Engineering&l=en_us&pg={page}&pgSz=20&o=Recent"
            )
            jobs = self.driver.find_elements(
                By.CSS_SELECTOR, 'div[role="listitem"][data-automationid="ListCell"]'
            )

            for job in jobs:
                try:
                    job_link = job.find_element(By.TAG_NAME, "button")
                    job_link.click()
                    self.wait_for_page_load()
                    apply_button = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        'button[aria-label="Apply"], button[aria-label="Complete application"]',
                    )
                    if apply_button:
                        description = self.driver.find_elements(
                            By.CLASS_NAME, "WzU5fAyjS4KUVs1QJGcQ"
                        )[0]
                        match = self.get_match_report(description.text)[
                            "matching_percent"
                        ]
                        match = match.replace("%", "") if match else 0
                        if int(match) > 80:
                            yield job

                except Exception as e:
                    logger.error(f"Job failed to load {str(e)}")
                    break
            else:
                page += 1
