"""AI Advertising Management Agent.

Automatically creates, optimises, and tracks ad campaigns for lippytm
projects across multiple channels (social media, search, and Web3).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AdChannel(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    GITHUB_SPONSORS = "github_sponsors"
    WEB3_DEFI = "web3_defi"
    NEWSLETTER = "newsletter"
    DISCORD = "discord"


class AdStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class AdCampaign:
    """Represents an advertising campaign for a repository."""

    campaign_id: str
    repo_name: str
    channel: AdChannel
    headline: str
    body_copy: str
    call_to_action: str
    target_audience: str
    budget_usd: float
    status: AdStatus = AdStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class CampaignMetrics:
    """Performance metrics for a campaign."""

    campaign_id: str
    impressions: int
    clicks: int
    conversions: int
    ctr: float  # click-through rate
    cvr: float  # conversion rate
    spend_usd: float
    cpc_usd: float  # cost per click
    roas: float  # return on ad spend


class AdManagerAgent:
    """Autonomous agent that manages AI-driven advertising for all repositories.

    Responsibilities:
    - Generate targeted ad copy using LLM
    - Optimise campaigns based on performance metrics
    - Report cross-channel performance
    - Suggest budget reallocation
    """

    AUDIENCE_PROFILES: dict[str, str] = {
        "developers": "Software developers interested in AI, blockchain, and automation tools",
        "web3_builders": "Web3 and DeFi builders looking for AI-powered development tools",
        "bot_creators": "Bot developers and automation enthusiasts",
        "enterprise": "Enterprise teams seeking AI and DevOps integration solutions",
        "learners": "Developers wanting to learn AI, blockchain, and full-stack development",
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
        self._campaigns: dict[str, AdCampaign] = {}

    # ------------------------------------------------------------------
    # Campaign creation
    # ------------------------------------------------------------------

    def create_campaign(
        self,
        repo_name: str,
        channel: AdChannel,
        target_audience: str = "developers",
        budget_usd: float = 100.0,
    ) -> AdCampaign:
        """Create a new ad campaign with AI-generated copy."""
        campaign_id = f"{repo_name}-{channel.value}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        audience_desc = self.AUDIENCE_PROFILES.get(target_audience, target_audience)

        if self._api_key:
            headline, body, cta = self._generate_ad_copy(repo_name, channel, audience_desc)
        else:
            headline, body, cta = self._placeholder_ad_copy(repo_name, channel)

        campaign = AdCampaign(
            campaign_id=campaign_id,
            repo_name=repo_name,
            channel=channel,
            headline=headline,
            body_copy=body,
            call_to_action=cta,
            target_audience=target_audience,
            budget_usd=budget_usd,
            tags=["lippytm", "ai", channel.value],
        )
        self._campaigns[campaign_id] = campaign
        return campaign

    def create_multi_channel_campaign(
        self,
        repo_name: str,
        channels: list[AdChannel] | None = None,
        budget_per_channel_usd: float = 50.0,
    ) -> list[AdCampaign]:
        """Create campaigns across multiple channels for a repository."""
        if channels is None:
            channels = [AdChannel.TWITTER, AdChannel.LINKEDIN, AdChannel.DISCORD]
        return [
            self.create_campaign(repo_name, channel, budget_usd=budget_per_channel_usd)
            for channel in channels
        ]

    # ------------------------------------------------------------------
    # Campaign management
    # ------------------------------------------------------------------

    def activate_campaign(self, campaign_id: str) -> bool:
        """Activate a draft campaign."""
        if campaign_id in self._campaigns:
            self._campaigns[campaign_id].status = AdStatus.ACTIVE
            return True
        return False

    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause an active campaign."""
        if campaign_id in self._campaigns:
            self._campaigns[campaign_id].status = AdStatus.PAUSED
            return True
        return False

    def update_metrics(self, campaign_id: str, impressions: int, clicks: int, conversions: int) -> bool:
        """Update performance metrics for a campaign."""
        if campaign_id not in self._campaigns:
            return False
        campaign = self._campaigns[campaign_id]
        campaign.impressions = impressions
        campaign.clicks = clicks
        campaign.conversions = conversions
        return True

    # ------------------------------------------------------------------
    # Reporting and optimisation
    # ------------------------------------------------------------------

    def get_campaign_metrics(self, campaign_id: str) -> CampaignMetrics | None:
        """Calculate performance metrics for a campaign."""
        if campaign_id not in self._campaigns:
            return None
        c = self._campaigns[campaign_id]
        ctr = c.clicks / c.impressions if c.impressions > 0 else 0.0
        cvr = c.conversions / c.clicks if c.clicks > 0 else 0.0
        spend = min(c.budget_usd, c.clicks * 0.50)  # assume $0.50 CPC estimate
        cpc = spend / c.clicks if c.clicks > 0 else 0.0
        roas = (c.conversions * 10.0) / spend if spend > 0 else 0.0

        return CampaignMetrics(
            campaign_id=campaign_id,
            impressions=c.impressions,
            clicks=c.clicks,
            conversions=c.conversions,
            ctr=round(ctr, 4),
            cvr=round(cvr, 4),
            spend_usd=round(spend, 2),
            cpc_usd=round(cpc, 2),
            roas=round(roas, 2),
        )

    def get_portfolio_report(self) -> dict[str, Any]:
        """Generate a summary report across all campaigns."""
        all_metrics = []
        for cid in self._campaigns:
            m = self.get_campaign_metrics(cid)
            if m:
                all_metrics.append(m)

        total_impressions = sum(m.impressions for m in all_metrics)
        total_clicks = sum(m.clicks for m in all_metrics)
        total_conversions = sum(m.conversions for m in all_metrics)
        total_spend = sum(m.spend_usd for m in all_metrics)

        return {
            "total_campaigns": len(self._campaigns),
            "active_campaigns": sum(
                1 for c in self._campaigns.values() if c.status == AdStatus.ACTIVE
            ),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "overall_ctr": round(total_clicks / total_impressions, 4) if total_impressions else 0,
            "total_spend_usd": round(total_spend, 2),
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        }

    def suggest_optimisations(self) -> list[str]:
        """Return AI-generated suggestions for campaign optimisation."""
        suggestions: list[str] = []
        for cid, campaign in self._campaigns.items():
            metrics = self.get_campaign_metrics(cid)
            if not metrics:
                continue
            if campaign.status == AdStatus.ACTIVE and metrics.ctr < 0.01:
                suggestions.append(
                    f"Campaign '{cid}': Low CTR ({metrics.ctr:.2%}). "
                    "Consider refreshing the ad copy or narrowing the target audience."
                )
            if metrics.cvr < 0.02 and metrics.clicks > 50:
                suggestions.append(
                    f"Campaign '{cid}': Low conversion rate ({metrics.cvr:.2%}). "
                    "Review the landing page or call-to-action."
                )
            if metrics.roas > 5:
                suggestions.append(
                    f"Campaign '{cid}': Strong ROAS ({metrics.roas:.1f}x). "
                    "Consider increasing budget to scale results."
                )
        return suggestions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_ad_copy(
        self,
        repo_name: str,
        channel: AdChannel,
        audience_desc: str,
    ) -> tuple[str, str, str]:
        """Generate ad headline, body, and CTA using the LLM."""
        prompt = (
            f"Create a {channel.value} advertisement for the GitHub project '{repo_name}'. "
            f"Target audience: {audience_desc}. "
            "Provide: 1) Headline (max 60 chars), 2) Body copy (max 150 chars), "
            "3) Call-to-action button text (max 25 chars). "
            "Focus on AI, automation, and Web3 innovation. "
            "Format as JSON: {\"headline\": \"\", \"body\": \"\", \"cta\": \"\"}"
        )
        try:
            raw = self._call_llm(prompt)
            import json
            data = json.loads(raw)
            return data.get("headline", ""), data.get("body", ""), data.get("cta", "")
        except Exception:
            return self._placeholder_ad_copy(repo_name, channel)

    def _call_llm(self, prompt: str) -> str:
        if self._provider == "anthropic":
            return self._call_anthropic(prompt)
        return self._call_openai(prompt)

    def _call_openai(self, prompt: str) -> str:
        import openai  # type: ignore[import]
        client = openai.OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic  # type: ignore[import]
        client = anthropic.Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _placeholder_ad_copy(
        self, repo_name: str, channel: AdChannel
    ) -> tuple[str, str, str]:
        short = repo_name[:30].rstrip("-")
        return (
            f"Build AI-powered {short}",
            f"Explore {repo_name} – full-stack AI & Web3 tools for modern developers. "
            "Join the lippytm.ai ecosystem today.",
            "Star on GitHub",
        )
