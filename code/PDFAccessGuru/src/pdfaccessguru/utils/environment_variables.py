import os
import re
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


KEY_NAMES = ("OPENROUTER_API_KEY", "OPENAI_API_KEY")


def _env_lines_without_keys() -> list[str]:
    path = user_env_file()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line for line in lines if line.split("=", 1)[0].strip().removeprefix("export ").strip() not in KEY_NAMES]


def _write_env(lines: list[str]) -> None:
    path = user_env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(".env.new")
    temporary.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)                      # only this user can read the key
    except OSError:
        pass
    temporary.replace(path)


def save_api_key(key: str) -> str:
    """
    Save an OpenRouter or OpenAI key in the user's settings file (replacing an earlier key) and use it right away.
    OpenRouter keys start with "sk-or-". Returns the variable name. Raises ValueError if it does not look like a key.
    """
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-.]{20,300}", key):
        raise ValueError("not a key")
    name = "OPENROUTER_API_KEY" if key.startswith("sk-or-") else "OPENAI_API_KEY"
    _write_env(_env_lines_without_keys() + [f"{name}={key}"])
    for other in KEY_NAMES:
        os.environ.pop(other, None)
    os.environ[name] = key
    return name


def remove_api_keys() -> None:
    """Remove the OpenRouter and OpenAI keys from the user's settings file and from this run."""
    if user_env_file().is_file():
        _write_env(_env_lines_without_keys())
    for name in KEY_NAMES:
        os.environ.pop(name, None)


def api_key_end() -> str:
    """The last 4 characters of the key in use, so people can recognise it without it being shown."""
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    return key[-4:] if len(key) >= 20 else ""
