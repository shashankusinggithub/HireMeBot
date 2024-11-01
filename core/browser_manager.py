# core/browser_manager.py
import os
import platform
from typing import Optional
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from config.settings import settings
from .exceptions import BrowserException
from loguru import logger


class BrowserManager:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver: Optional[webdriver.Firefox] = None

    def _get_firefox_binary(self) -> Optional[str]:
        """Get Firefox binary path based on operating system"""
        system = platform.system().lower()

        if system == "windows":
            possible_paths = [
                "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
                os.path.expanduser("~")
                + "\\AppData\\Local\\Mozilla Firefox\\firefox.exe",
            ]
        elif system == "darwin":  # macOS
            possible_paths = [
                "/Applications/Firefox.app/Contents/MacOS/firefox",
                os.path.expanduser("~/Applications/Firefox.app/Contents/MacOS/firefox"),
            ]
        else:  # Linux and others
            possible_paths = [
                "/usr/bin/firefox",
                "/usr/lib/firefox/firefox",
                "/snap/bin/firefox",
            ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Firefox binary at: {path}")
                return path

        return None

    def init_driver(self) -> webdriver.Firefox:
        try:
            options = Options()
            if self.headless:
                options.add_argument("--headless")

            # Get Firefox binary path
            binary_path = self._get_firefox_binary()
            if binary_path:
                options.binary_location = binary_path
            else:
                logger.warning("Firefox binary not found in default locations")
                logger.info(
                    "Please install Firefox or specify the binary location manually"
                )
                raise BrowserException(
                    "Firefox not found. Please install Firefox from https://www.mozilla.org/firefox/new/"
                )

            # Set up Firefox preferences
            options.set_preference("browser.download.folderList", 2)
            options.set_preference("browser.download.manager.showWhenStarting", False)
            options.set_preference("browser.download.dir", str(settings.DATA_DIR))
            options.set_preference(
                "browser.helperApps.neverAsk.saveToDisk",
                "application/pdf,application/x-pdf",
            )
            options.set_preference("browser.window.width", 1920)
            options.set_preference("browser.window.height", 1080)

            # Initialize the driver
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)

            # Configure timeouts
            driver.implicitly_wait(settings.IMPLICIT_WAIT)
            driver.set_page_load_timeout(settings.BROWSER_TIMEOUT)

            self.driver = driver
            self.driver.set_window_size(1920, 1080)
            logger.info("Firefox WebDriver initialized successfully")
            return driver

        except Exception as e:
            error_msg = str(e)
            if "binary" in error_msg.lower():
                error_msg = (
                    "Firefox not found. Please:\n"
                    "1. Install Firefox from https://www.mozilla.org/firefox/new/\n"
                    "2. Make sure Firefox is installed in a standard location\n"
                    "3. Or set the Firefox binary path manually using options.binary_location"
                )
            raise BrowserException(f"Failed to initialize browser: {error_msg}")

    def quit(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser session terminated successfully")
            except Exception as e:
                logger.error(f"Error while closing browser: {str(e)}")
            finally:
                self.driver = None
