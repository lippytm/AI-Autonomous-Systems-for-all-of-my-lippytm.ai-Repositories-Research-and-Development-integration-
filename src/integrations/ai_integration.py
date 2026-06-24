"""
AI model integration supporting OpenAI and Anthropic.
"""
from __future__ import annotations

import importlib
from typing import List, Optional, Union

from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import Config
from src.core.logger import get_logger


logger = get_logger(__name__)


class AIIntegration:
    """Unified interface for calling AI model APIs.

    Supports OpenAI (``openai`` provider) and Anthropic (``anthropic`` provider).
    The active provider is determined by :attr:`Config.ai_provider`.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._provider = config.ai_provider.lower()
        self._client = self._build_client()

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _build_client(self) -> object:
        """Instantiate the provider-specific SDK client."""
        if self._provider == "openai":
            try:
                import openai  # noqa: PLC0415

                return openai.OpenAI()
            except ImportError:
                raise ImportError("Install 'openai' to use the OpenAI provider.")
        elif self._provider == "anthropic":
            try:
                import anthropic  # noqa: PLC0415

                return anthropic.Anthropic()
            except ImportError:
                raise ImportError("Install 'anthropic' to use the Anthropic provider.")
        else:
            raise ValueError(f"Unsupported AI provider: {self._provider!r}")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        messages: Optional[List[dict]] = None,
    ) -> str:
        """Send a completion request and return the response text.

        Args:
            prompt: User message / prompt text.
            system: Optional system instruction.
            messages: Optional pre-built message list (overrides *prompt* and *system*).

        Returns:
            Model response as a plain string.
        """
        if self._provider == "openai":
            return self._openai_complete(prompt, system, messages)
        return self._anthropic_complete(prompt, system)

    def _openai_complete(
        self,
        prompt: str,
        system: Optional[str],
        messages: Optional[List[dict]],
    ) -> str:
        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._config.ai_model,
            messages=messages,
            max_tokens=self._config.ai_max_tokens,
            temperature=self._config.ai_temperature,
        )
        return response.choices[0].message.content or ""

    def _anthropic_complete(self, prompt: str, system: Optional[str]) -> str:
        kwargs = {
            "model": self._config.ai_model,
            "max_tokens": self._config.ai_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""

    def analyze_code(self, code: str, language: str = "") -> str:
        """Ask the AI to analyze *code* and suggest improvements."""
        lang_hint = f" ({language})" if language else ""
        system = (
            "You are an expert software engineer specializing in code quality, "
            "security, and performance. Provide concise, actionable feedback."
        )
        prompt = (
            f"Analyze the following code{lang_hint} and suggest specific improvements "
            "for readability, performance, security, and best practices. "
            "Format your response as a numbered list.\n\n"
            f"```{language}\n{code}\n```"
        )
        return self.complete(prompt, system=system)

    def summarize_repository(self, readme: str, file_list: List[str]) -> str:
        """Summarize a repository given its README and file list."""
        system = "You are an expert software architect. Be concise."
        file_sample = "\n".join(file_list[:50])
        prompt = (
            "Summarize this repository, identify its purpose, and suggest the top 3 "
            "improvements that would have the highest impact.\n\n"
            f"README:\n{readme[:3000]}\n\nFile list (sample):\n{file_sample}"
        )
        return self.complete(prompt, system=system)
