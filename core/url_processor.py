from typing import Dict
from urllib.parse import urlparse
from loguru import logger
from core.exceptions import JobBotException


class URLProcessor:
    def __init__(self, site_handlers: Dict):
        self.site_handlers = site_handlers

    def get_site_type(self, url: str) -> str:
        """Determine the site type from URL"""
        domain = urlparse(url).netloc.lower()

        if "linkedin.com" in domain:
            return "linkedin"
        elif "microsoft.com" in domain:
            return "microsoft"
        else:
            raise JobBotException(f"Unsupported job site: {domain}")

    def process_url(self, url: str, credentials: Dict) -> None:
        """Process a single job URL"""
        try:
            site_type = self.get_site_type(url)

            if site_type not in self.site_handlers:
                raise JobBotException(f"No handler found for site type: {site_type}")

            handler = self.site_handlers[site_type]
            handler.credentials = credentials[site_type]
            handler.site_type = site_type

            # Login if needed

            # if not handler.is_logged_in():
            #     handler.login(credentials[site_type])

            # Apply to job
            handler.apply_to_job(url)
            logger.success(f"Successfully processed job: {url}")

        except Exception as e:
            logger.error(f"Failed to process job {url}: {str(e)}")
            raise
