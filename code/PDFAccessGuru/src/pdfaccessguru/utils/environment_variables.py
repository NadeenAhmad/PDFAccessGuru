from pathlib import Path

from dotenv import load_dotenv
from platformdirs import user_config_dir

APP_NAME = "pdfaccessguru"


def user_env_file() -> Path:
    """The .env file in the user's settings folder (e.g. ~/.config/pdfaccessguru/.env on Linux)."""
    return Path(user_config_dir(APP_NAME)) / ".env"


def load_environment_variables() -> None:
    """
    Load settings such as API keys from .env files, without overriding variables that are
    already set. Looked up in this order:
    1. the user's settings folder (installed tool),
    2. the code folder of a source checkout (developers),
    3. the current working directory.
    """
    source_checkout_env = Path(__file__).resolve().parents[3] / ".env"
    for env_file in (user_env_file(), source_checkout_env, Path.cwd() / ".env"):
        if env_file.is_file():
            load_dotenv(env_file, override=False)
