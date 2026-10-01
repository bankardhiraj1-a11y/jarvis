"""Keep backend tests isolated from the user's paper-trading SQLite database."""

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import get_settings


_original_database_url = os.environ.get("DATABASE_URL")
_test_database_directory = TemporaryDirectory(prefix="jarvis2-backend-tests-")
os.environ["DATABASE_URL"] = (
    f"sqlite:///{_test_database_directory.name}/paper-tests.sqlite"
)
get_settings.cache_clear()


def pytest_sessionfinish(session, exitstatus):
    if _original_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = _original_database_url
    get_settings.cache_clear()