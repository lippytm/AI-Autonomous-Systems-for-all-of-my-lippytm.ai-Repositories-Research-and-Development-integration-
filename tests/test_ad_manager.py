"""Tests for AdManagerAgent."""

from __future__ import annotations

import pytest

from src.autonomous.ad_manager import (
    AdCampaign,
    AdChannel,
    AdManagerAgent,
    AdStatus,
    CampaignMetrics,
)


@pytest.fixture()
def agent() -> AdManagerAgent:
    return AdManagerAgent(api_key="", provider="openai", model="gpt-4o")


class TestAdManagerAgent:
    def test_create_campaign_returns_ad_campaign(self, agent: AdManagerAgent) -> None:
        campaign = agent.create_campaign(
            repo_name="Web3AI",
            channel=AdChannel.TWITTER,
            target_audience="developers",
            budget_usd=50.0,
        )
        assert isinstance(campaign, AdCampaign)
        assert campaign.repo_name == "Web3AI"
        assert campaign.channel == AdChannel.TWITTER
        assert campaign.status == AdStatus.DRAFT
        assert campaign.budget_usd == 50.0
        assert len(campaign.headline) > 0

    def test_create_multi_channel_campaign(self, agent: AdManagerAgent) -> None:
        campaigns = agent.create_multi_channel_campaign(
            "AllBots.com",
            channels=[AdChannel.TWITTER, AdChannel.LINKEDIN],
        )
        assert len(campaigns) == 2
        channels = {c.channel for c in campaigns}
        assert AdChannel.TWITTER in channels
        assert AdChannel.LINKEDIN in channels

    def test_activate_campaign(self, agent: AdManagerAgent) -> None:
        c = agent.create_campaign("Factory.ai", AdChannel.DISCORD)
        assert agent.activate_campaign(c.campaign_id)
        assert agent._campaigns[c.campaign_id].status == AdStatus.ACTIVE

    def test_pause_campaign(self, agent: AdManagerAgent) -> None:
        c = agent.create_campaign("Factory.ai", AdChannel.DISCORD)
        agent.activate_campaign(c.campaign_id)
        assert agent.pause_campaign(c.campaign_id)
        assert agent._campaigns[c.campaign_id].status == AdStatus.PAUSED

    def test_activate_unknown_campaign_returns_false(self, agent: AdManagerAgent) -> None:
        assert not agent.activate_campaign("does-not-exist")

    def test_update_metrics(self, agent: AdManagerAgent) -> None:
        c = agent.create_campaign("Web3AI", AdChannel.LINKEDIN)
        result = agent.update_metrics(c.campaign_id, impressions=1000, clicks=50, conversions=5)
        assert result
        updated = agent._campaigns[c.campaign_id]
        assert updated.impressions == 1000
        assert updated.clicks == 50
        assert updated.conversions == 5

    def test_get_campaign_metrics_calculates_ctr(self, agent: AdManagerAgent) -> None:
        c = agent.create_campaign("Web3AI", AdChannel.TWITTER)
        agent.update_metrics(c.campaign_id, impressions=1000, clicks=100, conversions=10)
        metrics = agent.get_campaign_metrics(c.campaign_id)
        assert metrics is not None
        assert isinstance(metrics, CampaignMetrics)
        assert metrics.ctr == pytest.approx(0.1, abs=1e-3)

    def test_get_campaign_metrics_zero_impressions(self, agent: AdManagerAgent) -> None:
        c = agent.create_campaign("Web3AI", AdChannel.NEWSLETTER)
        metrics = agent.get_campaign_metrics(c.campaign_id)
        assert metrics is not None
        assert metrics.ctr == 0.0

    def test_get_campaign_metrics_unknown_id(self, agent: AdManagerAgent) -> None:
        assert agent.get_campaign_metrics("unknown") is None

    def test_get_portfolio_report_structure(self, agent: AdManagerAgent) -> None:
        agent.create_campaign("Web3AI", AdChannel.TWITTER)
        agent.create_campaign("AllBots.com", AdChannel.DISCORD)
        report = agent.get_portfolio_report()
        assert "total_campaigns" in report
        assert report["total_campaigns"] == 2
        assert "generated_at" in report

    def test_suggest_optimisations_no_errors(self, agent: AdManagerAgent) -> None:
        c = agent.create_campaign("Web3AI", AdChannel.TWITTER)
        agent.activate_campaign(c.campaign_id)
        agent.update_metrics(c.campaign_id, impressions=10000, clicks=5, conversions=0)
        suggestions = agent.suggest_optimisations()
        assert isinstance(suggestions, list)
        # Low CTR should generate a suggestion
        assert any("CTR" in s for s in suggestions)

    def test_placeholder_ad_copy_length(self, agent: AdManagerAgent) -> None:
        headline, body, cta = agent._placeholder_ad_copy("Web3AI", AdChannel.TWITTER)
        assert len(headline) > 0
        assert len(body) > 0
        assert len(cta) > 0
