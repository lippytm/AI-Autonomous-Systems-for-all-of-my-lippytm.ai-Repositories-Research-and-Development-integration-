"""AI Content Generation Agent.

Generates blog posts, README updates, release notes, and social media
content for every lippytm repository using an LLM backend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ContentRequest:
    """Specification for a piece of content to generate."""

    repo_name: str
    content_type: str  # blog_post | readme | release_notes | social_media | tutorial
    topic: str
    language: str = "English"
    tone: str = "professional"
    max_words: int = 500
    extra_context: str = ""


@dataclass
class GeneratedContent:
    """Output from the content generation agent."""

    repo_name: str
    content_type: str
    title: str
    body: str
    tags: list[str]
    word_count: int
    model_used: str


class ContentGeneratorAgent:
    """Autonomous agent that produces AI-generated content for all repositories.

    Supports OpenAI (default) and Anthropic backends, selected by the
    ``AI_PROVIDER`` environment variable (``openai`` or ``anthropic``).
    """

    CONTENT_TEMPLATES: dict[str, str] = {
        "blog_post": (
            "Write a {tone} blog post about {topic} for the {repo} repository. "
            "Focus on how this project advances AI and Web3 capabilities. "
            "Include an introduction, key features, use cases, and a conclusion. "
            "Keep it under {max_words} words."
        ),
        "readme": (
            "Write a comprehensive README.md for the {repo} GitHub repository. "
            "Include: project overview, features, installation, usage examples, "
            "contributing guidelines, and license section. "
            "Repository context: {extra_context}"
        ),
        "release_notes": (
            "Generate professional release notes for {repo} covering: {topic}. "
            "Format as a changelog with Added / Changed / Fixed sections. "
            "Be concise and developer-focused."
        ),
        "social_media": (
            "Write 3 engaging social media posts (Twitter/X, LinkedIn, and a general one) "
            "about {topic} for the {repo} project. "
            "Each post should be concise, include relevant hashtags, and highlight "
            "the AI and Web3 innovation aspects."
        ),
        "tutorial": (
            "Write a step-by-step tutorial about {topic} for {repo}. "
            "Include code examples where appropriate. "
            "Target audience: developers interested in AI and blockchain. "
            "Maximum {max_words} words."
        ),
    }

    def __init__(
        self,
        api_key: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self._provider = (provider or os.getenv("AI_PROVIDER", "openai")).lower()
        self._model = model or os.getenv("AI_MODEL", "gpt-4o")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate(self, request: ContentRequest) -> GeneratedContent:
        """Generate content for the given request.

        Dispatches to the configured provider.  Falls back to a structured
        placeholder when no API key is available (useful in CI).
        """
        prompt = self._build_prompt(request)
        if self._api_key:
            body = self._call_llm(prompt)
        else:
            body = self._placeholder_content(request)

        title = self._extract_title(body, request)
        tags = self._extract_tags(request)

        return GeneratedContent(
            repo_name=request.repo_name,
            content_type=request.content_type,
            title=title,
            body=body,
            tags=tags,
            word_count=len(body.split()),
            model_used=self._model if self._api_key else "placeholder",
        )

    def generate_for_repo(
        self,
        repo_name: str,
        content_type: str = "blog_post",
        topic: str = "",
        **kwargs: Any,
    ) -> GeneratedContent:
        """Convenience wrapper to generate a single content piece for a repo."""
        if not topic:
            topic = f"the latest developments in {repo_name}"
        request = ContentRequest(
            repo_name=repo_name,
            content_type=content_type,
            topic=topic,
            **kwargs,
        )
        return self.generate(request)

    def generate_portfolio_digest(self, repo_names: list[str]) -> GeneratedContent:
        """Generate a portfolio-wide weekly digest post."""
        repos_list = "\n".join(f"- {name}" for name in repo_names)
        request = ContentRequest(
            repo_name="lippytm.ai",
            content_type="blog_post",
            topic=f"weekly digest of all lippytm repositories:\n{repos_list}",
            tone="engaging",
            max_words=800,
            extra_context="This is a high-level overview for the community.",
        )
        return self.generate(request)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, req: ContentRequest) -> str:
        template = self.CONTENT_TEMPLATES.get(req.content_type, self.CONTENT_TEMPLATES["blog_post"])
        return template.format(
            repo=req.repo_name,
            topic=req.topic,
            tone=req.tone,
            max_words=req.max_words,
            extra_context=req.extra_context,
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider."""
        if self._provider == "anthropic":
            return self._call_anthropic(prompt)
        return self._call_openai(prompt)

    def _call_openai(self, prompt: str) -> str:
        try:
            import openai  # type: ignore[import]
            client = openai.OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert technical writer and AI developer "
                            "specialising in full-stack AI, Web3, and autonomous systems "
                            "for the lippytm.ai ecosystem."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            return f"[OpenAI error: {exc}]\n\n{self._placeholder_content(None)}"  # type: ignore[arg-type]

    def _call_anthropic(self, prompt: str) -> str:
        try:
            import anthropic  # type: ignore[import]
            client = anthropic.Anthropic(api_key=self._api_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as exc:
            return f"[Anthropic error: {exc}]\n\n{self._placeholder_content(None)}"  # type: ignore[arg-type]

    def _placeholder_content(self, request: ContentRequest | None) -> str:
        if request is None:
            return "Content generation placeholder – configure an API key to enable AI generation."
        return (
            f"# {request.content_type.replace('_', ' ').title()}: {request.topic}\n\n"
            f"Repository: **{request.repo_name}**\n\n"
            "This is a placeholder generated without an LLM API key. "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable AI-powered content generation.\n\n"
            f"Topic: {request.topic}\n"
            f"Tone: {request.tone}\n"
            f"Max words: {request.max_words}\n"
        )

    def _extract_title(self, body: str, request: ContentRequest) -> str:
        for line in body.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:120]
        return f"{request.content_type.replace('_', ' ').title()} – {request.repo_name}"

    def _extract_tags(self, request: ContentRequest) -> list[str]:
        base_tags = ["lippytm", "ai", "autonomous-systems", request.content_type]
        if "web3" in request.repo_name.lower() or "web3" in request.topic.lower():
            base_tags.append("web3")
        if "bot" in request.repo_name.lower():
            base_tags.append("bots")
        if "typescript" in request.repo_name.lower():
            base_tags.append("typescript")
        return list(dict.fromkeys(base_tags))
