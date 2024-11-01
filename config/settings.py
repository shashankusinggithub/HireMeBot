from pathlib import Path
from typing import Dict
from pydantic import BaseModel


class Settings(BaseModel):
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    CREDENTIALS_FILE: Path = DATA_DIR / "credentials.json"

    # Browser settings
    BROWSER_TIMEOUT: int = 30
    IMPLICIT_WAIT: int = 10

    # Queue settings
    MAX_RETRIES: int = 3
    QUEUE_SLEEP_TIME: int = 5

    class Config:
        case_sensitive = True


settings = Settings()
