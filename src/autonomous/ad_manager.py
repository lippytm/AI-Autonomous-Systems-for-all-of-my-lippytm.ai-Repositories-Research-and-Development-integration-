"""Autonomous advertising-management agent.

Creates, tracks, and optimises ad campaigns across configured platforms.
All real network calls are abstracted behind an *ad_client* callable so
the class is fully testable without live credentials.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Campaign:
    """Represents a single advertising campaign."""

    name: str
    platform: str
    budget_usd: float
    target_topic: str
    status: str = "pending"          # pending | active | paused | completed
    impressions: int = 0
    clicks: int = 0
    spend_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def ctr(self) -> float:
        """Click-through rate (0–1)."""
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def cpc(self) -> float:
        """Cost per click in USD."""
        return self.spend_usd / self.clicks if self.clicks else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "platform": self.platform,
            "budget_usd": self.budget_usd,
            "target_topic": self.target_topic,
            "status": self.status,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "spend_usd": self.spend_usd,
            "ctr": self.ctr,
            "cpc": self.cpc,
            "created_at": self.created_at.isoformat(),
        }


class AdManager:
    """Creates and monitors advertising campaigns autonomously.

    Parameters
    ----------
    platforms:
        Ad platforms to target (e.g. ``["google_ads", "social_media"]``).
    budget_limit_usd:
        Maximum total spend permitted per :meth:`run` call.
    max_campaigns_per_run:
        Maximum number of new campaigns to launch per :meth:`run` call.
    ad_client:
        Callable that receives a :class:`Campaign` and submits it to an
        ad platform.  Defaults to a no-op logger.
    dry_run:
        When ``True`` the manager skips calling *ad_client*.
    """

    def __init__(
        self,
        platforms: List[str],
        budget_limit_usd: float = 100.0,
        max_campaigns_per_run: int = 3,
        ad_client: Optional[Callable[[Campaign], None]] = None,
        dry_run: bool = False,
    ) -> None:
        if not platforms:
            raise ValueError("At least one platform must be specified.")
        if budget_limit_usd <= 0:
            raise ValueError("budget_limit_usd must be > 0.")
        if max_campaigns_per_run < 1:
            raise ValueError("max_campaigns_per_run must be >= 1.")

        self.platforms = platforms
        self.budget_limit_usd = budget_limit_usd
        self.max_campaigns_per_run = max_campaigns_per_run
        self.ad_client = ad_client or self._log_submit
        self.dry_run = dry_run
        self._campaigns: List[Campaign] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, topics: List[str]) -> List[Campaign]:
        """Create and launch campaigns for the given *topics*.

        At most ``max_campaigns_per_run`` campaigns are created, with
        budget evenly distributed across platforms up to
        ``budget_limit_usd``.

        Returns the list of :class:`Campaign` objects created this run.
        """
        if not topics:
            logger.warning("AdManager.run called with no topics — skipping.")
            return []

        budget_per_campaign = self.budget_limit_usd / max(
            1, min(self.max_campaigns_per_run, len(topics))
        )
        created: List[Campaign] = []

        for idx, topic in enumerate(topics[: self.max_campaigns_per_run]):
            platform = self.platforms[idx % len(self.platforms)]
            campaign = self._build_campaign(topic, platform, budget_per_campaign)
            self._campaigns.append(campaign)
            created.append(campaign)
            if not self.dry_run:
                self._submit(campaign)

        logger.info("AdManager created %d campaign(s).", len(created))
        return created

    def create_campaign(
        self, topic: str, platform: str, budget_usd: float
    ) -> Campaign:
        """Create and submit a single campaign explicitly."""
        if not topic:
            raise ValueError("topic must not be empty.")
        if not platform:
            raise ValueError("platform must not be empty.")
        if budget_usd <= 0:
            raise ValueError("budget_usd must be > 0.")

        campaign = self._build_campaign(topic, platform, budget_usd)
        self._campaigns.append(campaign)
        if not self.dry_run:
            self._submit(campaign)
        return campaign

    def update_metrics(self, campaign_name: str, metrics: Dict[str, float]) -> bool:
        """Update performance metrics for an existing campaign.

        Returns ``True`` if the campaign was found and updated.
        """
        for campaign in self._campaigns:
            if campaign.name == campaign_name:
                campaign.impressions = int(metrics.get("impressions", campaign.impressions))
                campaign.clicks = int(metrics.get("clicks", campaign.clicks))
                campaign.spend_usd = metrics.get("spend_usd", campaign.spend_usd)
                logger.info(
                    "Updated metrics for campaign '%s': CTR=%.2f%%.",
                    campaign.name,
                    campaign.ctr * 100,
                )
                return True
        logger.warning("Campaign '%s' not found.", campaign_name)
        return False

    def get_campaigns(self) -> List[Campaign]:
        """Return a copy of the current campaign list."""
        return list(self._campaigns)

    def summary(self) -> dict:
        """Return aggregate performance across all campaigns."""
        total_spend = sum(c.spend_usd for c in self._campaigns)
        total_clicks = sum(c.clicks for c in self._campaigns)
        total_impressions = sum(c.impressions for c in self._campaigns)
        return {
            "total_campaigns": len(self._campaigns),
            "total_spend_usd": total_spend,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "overall_ctr": total_clicks / total_impressions if total_impressions else 0.0,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_campaign(
        self, topic: str, platform: str, budget_usd: float
    ) -> Campaign:
        name = f"campaign_{topic.replace(' ', '_')}_{platform}_{len(self._campaigns)}"
        return Campaign(
            name=name,
            platform=platform,
            budget_usd=budget_usd,
            target_topic=topic,
            status="active",
        )

    def _submit(self, campaign: Campaign) -> None:
        try:
            self.ad_client(campaign)
        except Exception:
            logger.exception("Failed to submit campaign '%s'.", campaign.name)
            campaign.status = "paused"

    @staticmethod
    def _log_submit(campaign: Campaign) -> None:
        logger.info(
            "[AdManager] Submitted campaign '%s' on %s (budget $%.2f).",
            campaign.name,
            campaign.platform,
            campaign.budget_usd,
        )
