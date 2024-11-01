from typing import Dict, List
from queue import Queue
from loguru import logger


class JobQueue:
    def __init__(self):
        self.queue: Queue = Queue()

    def add_url(self, url: str) -> None:
        """Add a job URL to the queue"""
        self.queue.put(url)
        logger.info(f"Added job URL to queue: {url}")

    def add_urls_from_file(self, filename: str) -> None:
        """Add multiple URLs from a file (one URL per line)"""
        try:
            with open(filename, "r") as f:
                urls = [line.strip() for line in f if line.strip()]
                for url in urls:
                    self.add_url(url)
            logger.info(f"Added {len(urls)} URLs from {filename}")
        except Exception as e:
            logger.error(f"Error reading URLs from file {filename}: {str(e)}")

    def get_next_url(self) -> str:
        """Get the next URL from the queue"""
        if not self.queue.empty():
            return self.queue.get()
        return None

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()

    def get_queue_size(self) -> int:
        """Get number of URLs in queue"""
        return self.queue.qsize()
