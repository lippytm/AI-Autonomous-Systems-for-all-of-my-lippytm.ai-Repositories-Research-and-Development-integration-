"""Tests for AdManager."""

import pytest

from src.autonomous.ad_manager import AdManager, Campaign


PLATFORMS = ["google_ads", "social_media"]
TOPICS = ["AI research", "autonomous systems", "machine learning"]


class TestCampaign:
    def test_ctr_zero_impressions(self):
        c = Campaign(name="c", platform="p", budget_usd=10.0, target_topic="t")
        assert c.ctr == 0.0

    def test_ctr_calculated(self):
        c = Campaign(name="c", platform="p", budget_usd=10.0, target_topic="t",
                     impressions=100, clicks=10)
        assert c.ctr == pytest.approx(0.1)

    def test_cpc_zero_clicks(self):
        c = Campaign(name="c", platform="p", budget_usd=10.0, target_topic="t")
        assert c.cpc == 0.0

    def test_cpc_calculated(self):
        c = Campaign(name="c", platform="p", budget_usd=10.0, target_topic="t",
                     clicks=5, spend_usd=2.50)
        assert c.cpc == pytest.approx(0.50)

    def test_to_dict_keys(self):
        c = Campaign(name="c", platform="p", budget_usd=10.0, target_topic="t")
        assert "name" in c.to_dict()
        assert "ctr" in c.to_dict()


class TestAdManagerInit:
    def test_requires_platforms(self):
        with pytest.raises(ValueError):
            AdManager(platforms=[])

    def test_invalid_budget(self):
        with pytest.raises(ValueError):
            AdManager(platforms=PLATFORMS, budget_limit_usd=0)

    def test_invalid_max_campaigns(self):
        with pytest.raises(ValueError):
            AdManager(platforms=PLATFORMS, max_campaigns_per_run=0)


class TestAdManagerRun:
    def _make(self, dry_run=True):
        return AdManager(
            platforms=PLATFORMS,
            budget_limit_usd=60.0,
            max_campaigns_per_run=3,
            dry_run=dry_run,
        )

    def test_empty_topics_returns_empty(self):
        mgr = self._make()
        assert mgr.run([]) == []

    def test_run_creates_campaigns(self):
        mgr = self._make()
        campaigns = mgr.run(TOPICS)
        assert len(campaigns) == 3

    def test_run_caps_at_max(self):
        mgr = AdManager(platforms=PLATFORMS, max_campaigns_per_run=2, dry_run=True)
        campaigns = mgr.run(TOPICS)  # 3 topics but cap is 2
        assert len(campaigns) == 2

    def test_campaigns_stored(self):
        mgr = self._make()
        mgr.run(TOPICS)
        assert len(mgr.get_campaigns()) == 3

    def test_ad_client_called_when_not_dry_run(self):
        submitted = []
        mgr = AdManager(
            platforms=PLATFORMS,
            max_campaigns_per_run=2,
            ad_client=lambda c: submitted.append(c),
            dry_run=False,
        )
        mgr.run(TOPICS[:2])
        assert len(submitted) == 2

    def test_ad_client_failure_marks_paused(self):
        def bad_client(c):
            raise RuntimeError("API down")

        mgr = AdManager(
            platforms=PLATFORMS,
            max_campaigns_per_run=1,
            ad_client=bad_client,
            dry_run=False,
        )
        campaigns = mgr.run(["AI"])
        assert campaigns[0].status == "paused"


class TestCreateCampaign:
    def test_basic_creation(self):
        mgr = AdManager(platforms=PLATFORMS, dry_run=True)
        c = mgr.create_campaign("AI", "google_ads", 50.0)
        assert c.target_topic == "AI"
        assert c.platform == "google_ads"

    def test_empty_topic_raises(self):
        mgr = AdManager(platforms=PLATFORMS, dry_run=True)
        with pytest.raises(ValueError):
            mgr.create_campaign("", "google_ads", 10.0)

    def test_zero_budget_raises(self):
        mgr = AdManager(platforms=PLATFORMS, dry_run=True)
        with pytest.raises(ValueError):
            mgr.create_campaign("AI", "google_ads", 0)


class TestUpdateMetrics:
    def test_update_existing(self):
        mgr = AdManager(platforms=PLATFORMS, dry_run=True)
        c = mgr.create_campaign("AI", "google_ads", 10.0)
        result = mgr.update_metrics(c.name, {"impressions": 1000, "clicks": 50, "spend_usd": 5.0})
        assert result is True
        assert c.impressions == 1000
        assert c.clicks == 50

    def test_update_nonexistent(self):
        mgr = AdManager(platforms=PLATFORMS, dry_run=True)
        assert mgr.update_metrics("does-not-exist", {}) is False


class TestSummary:
    def test_summary_keys(self):
        mgr = AdManager(platforms=PLATFORMS, dry_run=True)
        s = mgr.summary()
        assert "total_campaigns" in s
        assert "overall_ctr" in s

    def test_summary_totals(self):
        mgr = AdManager(platforms=PLATFORMS, dry_run=True)
        mgr.create_campaign("AI", "google_ads", 10.0)
        mgr.create_campaign("ML", "social_media", 20.0)
        assert mgr.summary()["total_campaigns"] == 2
