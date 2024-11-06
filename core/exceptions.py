class JobBotException(Exception):
    """Base exception for job application bot"""

    pass


class BrowserException(JobBotException):
    """Raised when browser-related operations fail"""

    pass


class ApplicationException(JobBotException):
    """Raised when job application fails"""

    pass


class TimeoutException(Exception):
    pass
