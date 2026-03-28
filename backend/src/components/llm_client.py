"""
LLM client wrapper for OpenAI chat completions.
"""

import logging
from typing import List

import openai

from src.config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper around the OpenAI SDK for chat completions."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.client = openai.OpenAI(api_key=self.api_key)
        logger.info("LLMClient initialized with model %s", self.model)

    def chat(self, messages: List[dict]) -> str:
        """Send messages to the OpenAI chat completions API.

        Args:
            messages: A list of message dicts with 'role' and 'content' keys.

        Returns:
            The assistant's response content as a string.

        Raises:
            openai.OpenAIError: If the API call fails.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content
        except Exception:
            logger.exception("OpenAI API call failed for model %s", self.model)
            raise
