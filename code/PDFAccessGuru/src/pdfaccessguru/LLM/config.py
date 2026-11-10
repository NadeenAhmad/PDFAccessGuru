"""
Configuration for the LLM integration.

All values are read from environment variables (or from the local .env file,
see .env.example). Never write API keys into this file or any other source file.
"""
import os

from pdfaccessguru.utils.environment_variables import load_environment_variables

load_environment_variables()


# Personal OpenRouter API key. Empty means "no key configured".
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# The OpenRouter chat completions endpoint (follows the OpenAI API format).
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# The model used for normal requests.
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "openai/gpt-6-luna")

# The vision-capable model used for prompts that include an image.
DEFAULT_IMAGE_MODEL = os.environ.get("DEFAULT_IMAGE_MODEL", "openai/gpt-6-luna")

# A more capable model for tasks that need higher accuracy.
PREMIUM_MODEL = os.environ.get("PREMIUM_MODEL", DEFAULT_MODEL)
