import re
import threading
from functools import wraps
import time
from core.exceptions import TimeoutException
from loguru import logger
from typing import Type, Union, Tuple


def extract_numbers(mixed_string: str) -> str:
    """Extract only numbers from a mixed alphanumeric string."""
    text = "".join(re.findall(r"\d+", mixed_string))
    return text if text else 0


def timeout(seconds=12):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Start the function in a separate thread
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                # If the thread is still running, raise a TimeoutException
                logger.error("Application timeout after 100 seconds")
                raise TimeoutException(f"Function timed out after {seconds} seconds")
            if exception[0]:
                raise exception[0]
            return result[0]

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
):
    """
    A decorator that retries a function if it raises specified exceptions.

    Args:
        max_attempts (int): Maximum number of retry attempts (default: 3)
        delay (float): Initial delay between retries in seconds (default: 1.0)
        backoff_factor (float): Multiplier applied to delay between retries (default: 2.0)
        exceptions: Exception or tuple of exceptions to catch (default: Exception)

    Returns:
        The decorated function

    Example:
        @retry(max_attempts=3, delay=1, exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            # Your code here
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    attempts += 1

                    if attempts == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts. "
                            f"Final exception: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"Attempt {attempts} failed for function {func.__name__}. "
                        f"Retrying in {current_delay} seconds... "
                        f"Exception: {str(e)}"
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff_factor

        return wrapper

    return decorator
