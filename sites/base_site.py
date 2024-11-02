from abc import ABC, abstractmethod
import json
from typing import Dict, List, Optional
from httpcore import TimeoutException
from loguru import logger
from selenium import webdriver
from core.exceptions import ApplicationException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from AI import choose_option, get_result
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)


class BaseSite(ABC):
    def __init__(self, driver: webdriver.Firefox):
        self.login_required = False
        self.driver = driver
        self.credentials = None
        self.site_type = None
        self.wait = WebDriverWait(driver, 30)
        self.login_required = True

    @abstractmethod
    def login(self) -> None:
        """Login to the job site"""
        pass

    @abstractmethod
    def apply_to_job(self, url: str, metadata: Optional[Dict] = None) -> None:
        """Apply to a specific job posting"""
        pass

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Check if user is currently logged in"""
        pass

    def wait_for_page_load(self, timeout=5, check_network=True, check_jquery=True):
        """
        Comprehensive page load waiting with multiple checks

        Args:
            timeout (int): Maximum wait time in seconds
            check_network (bool): Whether to check network requests
            check_jquery (bool): Whether to check jQuery ajax requests
        """
        try:
            # Wait for document ready state
            self.wait_for_document_ready(timeout)

            if check_jquery:
                self.wait_for_jquery(timeout)

            if check_network:
                self.wait_for_network_idle(timeout)

            # Wait for common loading indicators to disappear
            # self.wait_for_loading_elements(timeout)

            return True

        except TimeoutException as e:
            print(f"Timeout waiting for page load: {str(e)}")
            return False
        except Exception as e:
            print(f"Error waiting for page load: {str(e)}")
            return False

    def wait_for_document_ready(self, timeout=30):
        """Wait for document.readyState to be complete"""
        self.wait.until(
            lambda driver: driver.execute_script("return document.readyState")
            == "complete"
        )

    def wait_for_jquery(self, timeout=30):
        """Wait for jQuery ajax requests to complete"""
        jquery_check = """
            return (typeof jQuery !== 'undefined' && jQuery.active === 0) ||
                   typeof jQuery === 'undefined';
        """
        self.wait.until(lambda driver: driver.execute_script(jquery_check))

    def wait_for_network_idle(self, timeout=30):
        """Wait for network requests to complete"""
        network_check = """
            return window.performance.getEntriesByType('resource')
                .filter(r => !r.responseEnd).length === 0;
        """
        self.wait.until(lambda driver: driver.execute_script(network_check))

    def wait_for_loading_elements(self, timeout=30):
        """Wait for common loading indicators to disappear"""
        loading_selectors = [
            ".loading",
            ".spinner",
            '[class*="loading"]',
            '[class*="Loader"]',
            '[aria-busy="true"]',
            "#loading",
            ".skeleton",
        ]

        for selector in loading_selectors:
            try:
                self.wait.until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                )
            except Exception as e:
                continue  # Continue if selector not found

    def get_answer(self, question, options=None):
        return choose_option(question, options=None)

    def get_match_report(self, description):
        try:
            result = get_result(description, self.site_type)
            if result["matching_percent"]:
                return result
        except Exception as e:
            logger.error(f"Error getting match report for {self.site_type}: {str(e)}")

    def _get_element(self, by: By, selector: str, timeout: int = 10) -> Optional[any]:
        """Safe element getter with wait"""
        try:
            return self.wait.until(EC.presence_of_element_located((by, selector)))
        except TimeoutException:
            return None

    def _get_elements(self, by: By, selector: str) -> List[any]:
        """Safe multiple elements getter"""
        return self.driver.find_elements(by, selector)

    def _safe_click(self, element) -> bool:
        """Safely click an element with multiple attempts"""
        try:
            element.click()
            return True
        except ElementClickInterceptedException:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                logger.error(f"Failed to click element: {str(e)}")
                return False

    def get_cookies(self) -> Optional[List[Dict]]:
        """Get stored cookies"""
        try:
            with open(self.COOKIE_FILE, "r") as file:
                return json.load(file).get(self.site_type, None)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save_cookies(self) -> None:
        """Save current cookies"""
        try:
            with open(self.COOKIE_FILE, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        data[self.site_type] = self.driver.get_cookies()

        with open(self.COOKIE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def add_cookies(self):
        """Add a cookie to the browser"""
        cookies = self.get_cookies()
        if cookies:
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            if self.is_logged_in():
                return True
            else:
                return False
