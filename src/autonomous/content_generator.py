"""Autonomous content-generation agent.

Generates blog posts, social-media copy, and video scripts on a
configurable schedule.  All external publish calls are abstracted
behind a *publisher* callable so they can be replaced by mocks in tests.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContentItem:
    """A single piece of generated content."""

    platform: str
    topic: str
    title: str
    body: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published: bool = False

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "topic": self.topic,
            "title": self.title,
            "body": self.body,
            "created_at": self.created_at.isoformat(),
            "published": self.published,
        }


class ContentGenerator:
    """Generates and (optionally) publishes content autonomously.

    Parameters
    ----------
    platforms:
        List of target platform names (e.g. ``["blog", "social_media"]``).
    topics:
        Seed topics used when composing content.
    max_items_per_run:
        Upper bound on how many items to produce per :meth:`run` call.
    publisher:
        Callable that receives a :class:`ContentItem` and publishes it.
        Defaults to a no-op logger so the class works without real
        platform credentials.
    dry_run:
        When ``True`` the generator skips calling *publisher*.
    """

    def __init__(
        self,
        platforms: List[str],
        topics: List[str],
        max_items_per_run: int = 5,
        publisher: Optional[Callable[[ContentItem], None]] = None,
        dry_run: bool = False,
    ) -> None:
        if not platforms:
            raise ValueError("At least one platform must be specified.")
        if not topics:
            raise ValueError("At least one topic must be specified.")
        if max_items_per_run < 1:
            raise ValueError("max_items_per_run must be >= 1.")

        self.platforms = platforms
        self.topics = topics
        self.max_items_per_run = max_items_per_run
        self.publisher = publisher or self._log_publish
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> List[ContentItem]:
        """Generate and publish one batch of content items.

        Returns the list of :class:`ContentItem` objects produced.
        """
        items: List[ContentItem] = []
        for _ in range(self.max_items_per_run):
            platform = random.choice(self.platforms)
            topic = random.choice(self.topics)
            item = self._create_item(platform, topic)
            items.append(item)
            if not self.dry_run:
                self._publish(item)
        logger.info("ContentGenerator produced %d item(s).", len(items))
        return items

    def generate_for_topic(self, topic: str, platform: str) -> ContentItem:
        """Generate a single :class:`ContentItem` for an explicit topic."""
        if not topic:
            raise ValueError("topic must not be empty.")
        if not platform:
            raise ValueError("platform must not be empty.")
        item = self._create_item(platform, topic)
        if not self.dry_run:
            self._publish(item)
        return item

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_item(self, platform: str, topic: str) -> ContentItem:
        title = self._generate_title(topic)
        body = self._generate_body(topic, platform)
        return ContentItem(platform=platform, topic=topic, title=title, body=body)

    def _generate_title(self, topic: str) -> str:
        prefixes = [
            "Exploring",
            "Advances in",
            "The Future of",
            "Understanding",
            "A Deep Dive Into",
        ]
        return f"{random.choice(prefixes)} {topic}"

    def _generate_body(self, topic: str, platform: str) -> str:
        templates = {
            "blog": (
                f"In this post we explore recent developments in {topic}. "
                "Our autonomous research pipeline continuously monitors the "
                "latest publications and projects to keep you informed."
            ),
            "social_media": (
                f"🚀 Exciting updates in {topic}! "
                "Stay tuned for more from lippytm.ai. #AI #AutonomousSystems"
            ),
            "youtube": (
                f"Welcome to today's video on {topic}. "
                "Subscribe for weekly updates powered by lippytm.ai autonomous systems."
            ),
        }
        return templates.get(platform, f"Content about {topic} for {platform}.")

    def _publish(self, item: ContentItem) -> None:
        try:
            self.publisher(item)
            item.published = True
        except Exception:
            logger.exception("Failed to publish item '%s'.", item.title)

    @staticmethod
    def _log_publish(item: ContentItem) -> None:
        logger.info(
            "[ContentGenerator] Published '%s' to %s.", item.title, item.platform
        )
