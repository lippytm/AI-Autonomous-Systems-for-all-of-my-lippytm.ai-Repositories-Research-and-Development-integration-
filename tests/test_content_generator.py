"""Tests for ContentGeneratorAgent."""

from __future__ import annotations

import pytest

from src.autonomous.content_generator import (
    ContentGeneratorAgent,
    ContentRequest,
    GeneratedContent,
)


@pytest.fixture()
def agent() -> ContentGeneratorAgent:
    """Agent without API key – uses placeholder content."""
    return ContentGeneratorAgent(api_key="", provider="openai", model="gpt-4o")


class TestContentGeneratorAgent:
    def test_generate_returns_generated_content(self, agent: ContentGeneratorAgent) -> None:
        req = ContentRequest(
            repo_name="Web3AI",
            content_type="blog_post",
            topic="Web3 and AI integration",
        )
        result = agent.generate(req)
        assert isinstance(result, GeneratedContent)
        assert result.repo_name == "Web3AI"
        assert result.content_type == "blog_post"
        assert len(result.body) > 0
        assert result.word_count > 0
        assert result.model_used == "placeholder"

    def test_generate_for_repo_convenience(self, agent: ContentGeneratorAgent) -> None:
        result = agent.generate_for_repo("Factory.ai", content_type="social_media")
        assert result.repo_name == "Factory.ai"
        assert result.content_type == "social_media"

    def test_all_content_types_supported(self, agent: ContentGeneratorAgent) -> None:
        for ct in ["blog_post", "readme", "release_notes", "social_media", "tutorial"]:
            result = agent.generate_for_repo("Web3AI", content_type=ct)
            assert result.content_type == ct

    def test_tags_include_base_tags(self, agent: ContentGeneratorAgent) -> None:
        result = agent.generate_for_repo("Web3AI", content_type="blog_post", topic="web3")
        assert "lippytm" in result.tags
        assert "ai" in result.tags

    def test_web3_tag_added_for_web3_repos(self, agent: ContentGeneratorAgent) -> None:
        result = agent.generate_for_repo("Web3AI", content_type="blog_post", topic="blockchain")
        assert "web3" in result.tags

    def test_bot_tag_added_for_bot_repos(self, agent: ContentGeneratorAgent) -> None:
        result = agent.generate_for_repo("Chatlippytm.ai.Bots", content_type="blog_post")
        assert "bots" in result.tags

    def test_generate_portfolio_digest(self, agent: ContentGeneratorAgent) -> None:
        repos = ["Web3AI", "AllBots.com", "Factory.ai"]
        result = agent.generate_portfolio_digest(repos)
        assert result.repo_name == "lippytm.ai"
        assert result.content_type == "blog_post"
        assert len(result.body) > 0

    def test_title_extraction_from_body(self, agent: ContentGeneratorAgent) -> None:
        req = ContentRequest(repo_name="Web3AI", content_type="blog_post", topic="test")
        result = agent.generate(req)
        assert len(result.title) > 0

    def test_build_prompt_includes_repo_name(self, agent: ContentGeneratorAgent) -> None:
        req = ContentRequest(repo_name="MyRepo", content_type="blog_post", topic="test topic")
        prompt = agent._build_prompt(req)
        assert "MyRepo" in prompt

    def test_no_duplicate_tags(self, agent: ContentGeneratorAgent) -> None:
        result = agent.generate_for_repo("Web3AI", content_type="blog_post", topic="web3 ai")
        assert len(result.tags) == len(set(result.tags))
