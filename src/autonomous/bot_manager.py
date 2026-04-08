"""Bot Management Agent.

Provides unified management of all bot-related repositories in the
lippytm.ai portfolio, including AllBots.com, Chatlippytm.ai.Bots,
lippytm-lippytm.ai-tower-control-ai, and related projects.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class BotPlatform(str, Enum):
    MANYCHAT = "manychat"
    BOTBUILDERS = "botbuilders"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SLACK = "slack"
    GITHUB = "github"
    CUSTOM = "custom"


class BotStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    DEPLOYING = "deploying"
    STOPPED = "stopped"


@dataclass
class BotConfig:
    """Configuration for a managed bot."""

    bot_id: str
    name: str
    platform: BotPlatform
    repo_name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    webhook_url: str = ""
    ai_model: str = "gpt-4o"
    status: BotStatus = BotStatus.IDLE
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    last_seen: str = ""
    message_count: int = 0
    error_count: int = 0


@dataclass
class BotMessage:
    """A message processed by a bot."""

    bot_id: str
    user_input: str
    bot_response: str
    platform: BotPlatform
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    tokens_used: int = 0
    latency_ms: float = 0.0


class BotManagerAgent:
    """Autonomous agent for managing all bot deployments across the portfolio.

    Manages bots from:
    - AllBots.com / AllBots.com.ai  – central bot registry
    - Chatlippytm.ai.Bots           – AI chat bots
    - lippytm-lippytm.ai-tower-control-ai – control tower
    - Transparency-Logic-Time-Machine-Bots – logic bots
    - Factory.ai                    – factory automation bots

    Features:
    - Bot registration and lifecycle management
    - AI-powered response generation
    - Cross-platform message routing
    - Performance monitoring and alerting
    """

    # Pre-registered bots from all lippytm bot repositories
    DEFAULT_BOTS: list[dict[str, Any]] = [
        {
            "bot_id": "allbots-main",
            "name": "AllBots Central Manager",
            "platform": BotPlatform.CUSTOM,
            "repo_name": "AllBots.com",
            "description": "Central bot registry and management hub",
            "capabilities": ["registry", "routing", "monitoring", "automation"],
        },
        {
            "bot_id": "allbots-ai",
            "name": "AllBots AI Assistant",
            "platform": BotPlatform.CUSTOM,
            "repo_name": "AllBots.com.ai",
            "description": "AI-enhanced bot with Factory.ai integration",
            "capabilities": ["ai-responses", "factory-workflows", "scheduling"],
        },
        {
            "bot_id": "chatlippytm-main",
            "name": "Chat lippytm AI Bot",
            "platform": BotPlatform.MANYCHAT,
            "repo_name": "Chatlippytm.ai.Bots",
            "description": "Business AI bot for ManyChat and BotBuilders.com",
            "capabilities": ["business-automation", "lead-gen", "customer-service"],
        },
        {
            "bot_id": "tower-control",
            "name": "Tower Control AI",
            "platform": BotPlatform.CUSTOM,
            "repo_name": "lippytm-lippytm.ai-tower-control-ai",
            "description": "Control tower integrating ChatGPT with external platforms",
            "capabilities": ["orchestration", "platform-integration", "monitoring"],
        },
        {
            "bot_id": "transparency-logic-bot",
            "name": "Transparency Logic Time Machine Bot",
            "platform": BotPlatform.CUSTOM,
            "repo_name": "Transparency-Logic-Time-Machine-Bots-",
            "description": "Logic and reasoning bot with time-machine capabilities",
            "capabilities": ["logic", "reasoning", "time-machine", "transparency"],
        },
        {
            "bot_id": "factory-ai-bot",
            "name": "Factory AI Workflow Bot",
            "platform": BotPlatform.GITHUB,
            "repo_name": "Factory.ai",
            "description": "Factory automation bot for GitHub and ChatGPT workflows",
            "capabilities": ["workflow-automation", "github-integration", "ci-cd"],
        },
    ]

    def __init__(
        self,
        api_key: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self._provider = (provider or os.getenv("AI_PROVIDER", "openai")).lower()
        self._model = model or os.getenv("AI_MODEL", "gpt-4o")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
        self._bots: dict[str, BotConfig] = {}
        self._message_log: list[BotMessage] = []
        self._load_default_bots()

    # ------------------------------------------------------------------
    # Bot lifecycle
    # ------------------------------------------------------------------

    def _load_default_bots(self) -> None:
        for cfg in self.DEFAULT_BOTS:
            self.register_bot(**cfg)

    def register_bot(
        self,
        bot_id: str,
        name: str,
        platform: BotPlatform,
        repo_name: str,
        description: str,
        capabilities: list[str] | None = None,
        ai_model: str = "gpt-4o",
        webhook_url: str = "",
    ) -> BotConfig:
        """Register a new bot."""
        config = BotConfig(
            bot_id=bot_id,
            name=name,
            platform=platform,
            repo_name=repo_name,
            description=description,
            capabilities=capabilities or [],
            ai_model=ai_model,
            webhook_url=webhook_url,
        )
        self._bots[bot_id] = config
        return config

    def activate_bot(self, bot_id: str) -> bool:
        if bot_id in self._bots:
            self._bots[bot_id].status = BotStatus.ACTIVE
            self._bots[bot_id].last_seen = datetime.now(timezone.utc).isoformat() + "Z"
            return True
        return False

    def stop_bot(self, bot_id: str) -> bool:
        if bot_id in self._bots:
            self._bots[bot_id].status = BotStatus.STOPPED
            return True
        return False

    def get_bot(self, bot_id: str) -> BotConfig | None:
        return self._bots.get(bot_id)

    def list_bots(self, platform: BotPlatform | None = None) -> list[BotConfig]:
        bots = list(self._bots.values())
        if platform:
            bots = [b for b in bots if b.platform == platform]
        return bots

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    def process_message(self, bot_id: str, user_input: str) -> BotMessage:
        """Process a user message through the specified bot."""
        if bot_id not in self._bots:
            raise ValueError(f"Bot '{bot_id}' not found")

        bot = self._bots[bot_id]
        bot.message_count += 1
        bot.last_seen = datetime.now(timezone.utc).isoformat() + "Z"

        if self._api_key:
            response = self._generate_response(bot, user_input)
        else:
            response = self._placeholder_response(bot, user_input)

        msg = BotMessage(
            bot_id=bot_id,
            user_input=user_input,
            bot_response=response,
            platform=bot.platform,
        )
        self._message_log.append(msg)
        return msg

    # ------------------------------------------------------------------
    # Monitoring and reporting
    # ------------------------------------------------------------------

    def get_fleet_status(self) -> dict[str, Any]:
        """Return a status report for all managed bots."""
        status_counts: dict[str, int] = {}
        for bot in self._bots.values():
            s = bot.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "total_bots": len(self._bots),
            "status_breakdown": status_counts,
            "total_messages_processed": sum(b.message_count for b in self._bots.values()),
            "total_errors": sum(b.error_count for b in self._bots.values()),
            "platforms": list({b.platform.value for b in self._bots.values()}),
            "bots": [
                {
                    "bot_id": b.bot_id,
                    "name": b.name,
                    "platform": b.platform.value,
                    "repo": b.repo_name,
                    "status": b.status.value,
                    "messages": b.message_count,
                    "capabilities": b.capabilities,
                }
                for b in self._bots.values()
            ],
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        }

    def get_message_log(self, bot_id: str | None = None, limit: int = 50) -> list[BotMessage]:
        """Return recent messages, optionally filtered by bot."""
        log = self._message_log[-limit:]
        if bot_id:
            log = [m for m in log if m.bot_id == bot_id]
        return log

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_response(self, bot: BotConfig, user_input: str) -> str:
        system_prompt = (
            f"You are {bot.name}, an AI bot from the lippytm.ai ecosystem. "
            f"Repository: {bot.repo_name}. "
            f"Description: {bot.description}. "
            f"Your capabilities: {', '.join(bot.capabilities)}. "
            "Be helpful, concise, and focus on AI, Web3, and automation topics."
        )
        try:
            if self._provider == "anthropic":
                import anthropic  # type: ignore[import]
                client = anthropic.Anthropic(api_key=self._api_key)
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=512,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_input}],
                )
                return message.content[0].text
            else:
                import openai  # type: ignore[import]
                client = openai.OpenAI(api_key=self._api_key)
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input},
                    ],
                    temperature=0.7,
                )
                return response.choices[0].message.content or ""
        except Exception as exc:
            bot.error_count += 1
            bot.status = BotStatus.ERROR
            return f"Error processing message: {exc}"

    def _placeholder_response(self, bot: BotConfig, user_input: str) -> str:
        return (
            f"[{bot.name}] Received: '{user_input[:50]}'. "
            "AI response generation requires an API key (OPENAI_API_KEY or ANTHROPIC_API_KEY). "
            f"Bot capabilities: {', '.join(bot.capabilities)}."
        )
