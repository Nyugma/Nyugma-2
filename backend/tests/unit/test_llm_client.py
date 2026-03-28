"""
Unit tests for LLMClient.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.components.llm_client import LLMClient


class TestLLMClient:
    """Tests for LLMClient."""

    @patch("src.components.llm_client.openai")
    def test_init_creates_openai_client(self, mock_openai):
        client = LLMClient(api_key="test-key", model="gpt-4o-mini")

        mock_openai.OpenAI.assert_called_once_with(api_key="test-key")
        assert client.model == "gpt-4o-mini"

    @patch("src.components.llm_client.openai")
    def test_init_uses_settings_defaults(self, mock_openai):
        with patch("src.components.llm_client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "env-key"
            mock_settings.OPENAI_MODEL = "gpt-4o"
            LLMClient()

        mock_openai.OpenAI.assert_called_once_with(api_key="env-key")

    @patch("src.components.llm_client.openai")
    def test_chat_returns_response_content(self, mock_openai):
        mock_message = MagicMock()
        mock_message.content = "Hello, I can help with legal questions."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")
        messages = [
            {"role": "system", "content": "You are a legal assistant."},
            {"role": "user", "content": "What is a tort?"},
        ]
        result = client.chat(messages)

        assert result == "Hello, I can help with legal questions."
        mock_client_instance.chat.completions.create.assert_called_once()

    @patch("src.components.llm_client.openai")
    def test_chat_passes_correct_parameters(self, mock_openai):
        mock_message = MagicMock()
        mock_message.content = "response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client_instance

        with patch("src.components.llm_client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "key"
            mock_settings.OPENAI_MODEL = "gpt-4o-mini"
            mock_settings.LLM_TEMPERATURE = 0.3
            mock_settings.LLM_MAX_TOKENS = 1024

            client = LLMClient(api_key="key", model="gpt-4o-mini")
            messages = [{"role": "user", "content": "Hi"}]
            client.chat(messages)

        call_kwargs = mock_client_instance.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs.kwargs["messages"] == messages
        assert call_kwargs.kwargs["temperature"] == 0.3
        assert call_kwargs.kwargs["max_tokens"] == 1024

    @patch("src.components.llm_client.openai")
    def test_chat_raises_on_api_failure(self, mock_openai):
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.side_effect = Exception(
            "API rate limit exceeded"
        )
        mock_openai.OpenAI.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")

        with pytest.raises(Exception, match="API rate limit exceeded"):
            client.chat([{"role": "user", "content": "test"}])
