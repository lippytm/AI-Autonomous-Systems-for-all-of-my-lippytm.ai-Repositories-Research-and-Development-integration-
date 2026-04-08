"""Tests for Orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.orchestrator import Orchestrator, OrchestratorConfig, OrchestratorStatus


@pytest.fixture()
def orchestrator() -> Orchestrator:
    config = OrchestratorConfig(
        github_token="test-token",
        ai_api_key="",
        ai_provider="openai",
        ai_model="gpt-4o",
    )
    return Orchestrator(config)


MOCK_REPOS = [
    {
        "name": "Web3AI",
        "full_name": "lippytm/Web3AI",
        "description": "Web3 AI integration platform",
        "language": "Python",
        "url": "https://github.com/lippytm/Web3AI",
        "stars": 2,
        "open_issues": 16,
        "last_updated": "2026-02-05T20:29:15Z",
    },
    {
        "name": "AllBots.com",
        "full_name": "lippytm/AllBots.com",
        "description": "Bot management and automations",
        "language": "",
        "url": "https://github.com/lippytm/AllBots.com",
        "stars": 1,
        "open_issues": 1,
        "last_updated": "2026-03-01T16:20:32Z",
    },
]


class TestOrchestrator:
    def test_init_creates_all_agents(self, orchestrator: Orchestrator) -> None:
        assert orchestrator.repo_manager is not None
        assert orchestrator.content_agent is not None
        assert orchestrator.ad_agent is not None
        assert orchestrator.research_agent is not None
        assert orchestrator.bot_agent is not None
        assert orchestrator.web3_agent is not None
        assert orchestrator.qa_monitor is not None

    def test_get_status_returns_status(self, orchestrator: Orchestrator) -> None:
        status = orchestrator.get_status()
        assert isinstance(status, OrchestratorStatus)
        assert status.running is True
        assert len(status.agents_active) > 0

    def test_sync_repositories_uses_repo_manager(self, orchestrator: Orchestrator) -> None:
        with patch.object(orchestrator.repo_manager, "list_all_repos", return_value=[]):
            repos = orchestrator.sync_repositories()
        assert repos == []
        assert orchestrator._last_sync != ""

    def test_sync_repositories_handles_exception(self, orchestrator: Orchestrator) -> None:
        with patch.object(
            orchestrator.repo_manager, "list_all_repos", side_effect=Exception("network error")
        ):
            repos = orchestrator.sync_repositories()
        assert repos == []  # returns empty on error

    def test_run_health_check_structure(self, orchestrator: Orchestrator) -> None:
        orchestrator._repo_cache = MOCK_REPOS
        report = orchestrator.run_health_check()
        assert "overall_score" in report
        assert "total_repos" in report
        assert report["total_repos"] == len(MOCK_REPOS)
        assert "repo_scores" in report

    def test_generate_content_returns_dict(self, orchestrator: Orchestrator) -> None:
        result = orchestrator.generate_content("Web3AI", "blog_post", "AI and Web3")
        assert "title" in result
        assert "body" in result
        assert "tags" in result
        assert result["repo"] == "Web3AI"

    def test_generate_portfolio_digest_triggers_sync(self, orchestrator: Orchestrator) -> None:
        orchestrator._repo_cache = MOCK_REPOS
        result = orchestrator.generate_portfolio_digest()
        assert "title" in result
        assert "body" in result

    def test_create_ad_campaign_returns_dict(self, orchestrator: Orchestrator) -> None:
        result = orchestrator.create_ad_campaign(
            "Web3AI", channel="twitter", target_audience="developers", budget_usd=50.0
        )
        assert "campaign_id" in result
        assert result["repo"] == "Web3AI"
        assert result["channel"] == "twitter"

    def test_create_ad_campaign_invalid_channel_raises(self, orchestrator: Orchestrator) -> None:
        with pytest.raises(ValueError):
            orchestrator.create_ad_campaign("Web3AI", channel="invalid_channel")

    def test_run_research_uses_cache(self, orchestrator: Orchestrator) -> None:
        orchestrator._repo_cache = MOCK_REPOS
        result = orchestrator.run_research()
        assert "title" in result
        assert "findings" in result
        assert "recommendations" in result

    def test_get_integration_opportunities(self, orchestrator: Orchestrator) -> None:
        orchestrator._repo_cache = MOCK_REPOS
        opps = orchestrator.get_integration_opportunities()
        assert isinstance(opps, list)

    def test_get_bot_fleet_status(self, orchestrator: Orchestrator) -> None:
        status = orchestrator.get_bot_fleet_status()
        assert "total_bots" in status
        assert status["total_bots"] > 0

    def test_send_bot_message(self, orchestrator: Orchestrator) -> None:
        result = orchestrator.send_bot_message("allbots-main", "Hello!")
        assert result["bot_id"] == "allbots-main"
        assert "response" in result

    def test_send_bot_message_unknown_bot_raises(self, orchestrator: Orchestrator) -> None:
        with pytest.raises(ValueError):
            orchestrator.send_bot_message("no-such-bot", "Hi")

    def test_get_web3_summary(self, orchestrator: Orchestrator) -> None:
        summary = orchestrator.get_web3_summary()
        assert "supported_networks" in summary

    def test_analyse_defi(self, orchestrator: Orchestrator) -> None:
        result = orchestrator.analyse_defi("Uniswap", 1_000_000, 10.0, "medium")
        assert "protocol" in result
        assert "summary" in result
        assert result["protocol"] == "Uniswap"

    def test_get_portfolio_summary_syncs_if_no_cache(self, orchestrator: Orchestrator) -> None:
        with patch.object(
            orchestrator.repo_manager, "get_portfolio_summary", return_value={"owner": "lippytm"}
        ):
            with patch.object(orchestrator, "sync_repositories", return_value=MOCK_REPOS) as mock_sync:
                orchestrator._repo_cache = []
                result = orchestrator.get_portfolio_summary()
        mock_sync.assert_called_once()
        assert "owner" in result
