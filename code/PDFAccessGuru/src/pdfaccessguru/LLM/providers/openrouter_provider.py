"""
Kept for the correctors that import OpenRouterBaseProvider. Since Phase 4 it is the general
client in LLM/client.py: it talks to OpenRouter, OpenAI or a local Ollama, whichever is set up.

Usage example:
    provider = OpenRouterBaseProvider()
    answer = provider.send_message("You are helpful.", "What is 2+2?")
"""

from pdfaccessguru.LLM.client import LLMClient, LLMNotConfigured

OpenRouterBaseProvider = LLMClient

__all__ = ["OpenRouterBaseProvider", "LLMNotConfigured"]
