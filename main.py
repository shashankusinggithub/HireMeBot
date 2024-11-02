from typing import Dict
import json
from loguru import logger
from config.settings import settings
from core.browser_manager import BrowserManager
from core.queue_manager import JobQueue
from core.url_processor import URLProcessor
from sites.linkedin import LinkedInSite
from sites.microsoft import MicrosoftSite
from utils.logger import setup_logger


def load_credentials() -> Dict[str, Dict[str, str]]:
    try:
        with open(settings.CREDENTIALS_FILE) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load credentials: {str(e)}")
        raise


def main():
    setup_logger()
    logger.info("Starting job application bot")

    # Initialize components
    browser_manager = BrowserManager(headless=False)
    job_queue = JobQueue()

    try:
        driver = browser_manager.init_driver()
        credentials = load_credentials()

        # Initialize site handlers
        site_handlers = {
            "linkedin": LinkedInSite(driver),
            "microsoft": MicrosoftSite(driver),
        }

        url_processor = URLProcessor(site_handlers)

        # Add jobs to queue
        # job_queue.add_url(
        #     "microsoft.com"
        # )
        job_queue.add_url("linkedin.com")

        # Optional: Add jobs from file
        # job_queue.add_urls_from_file("job_urls.txt")

        # Process all URLs in queue
        while not job_queue.is_empty():
            url = job_queue.get_next_url()
            try:
                url_processor.process_url(url, credentials)
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                continue

    finally:
        browser_manager.quit()


if __name__ == "__main__":
    main()

    # sample_jobs = [
    #     "https://jobs.careers.microsoft.com/global/en/job/1748714/Software-Engineer",
    #     # "https://careers.microsoft.com/job/456",
    # ]
