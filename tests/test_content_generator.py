"""Tests for ContentGenerator."""

import pytest

from src.autonomous.content_generator import ContentItem, ContentGenerator


PLATFORMS = ["blog", "social_media", "youtube"]
TOPICS = ["AI research", "autonomous systems"]


class TestContentItem:
    def test_to_dict_keys(self):
        item = ContentItem(platform="blog", topic="AI", title="Hello", body="World")
        d = item.to_dict()
        assert set(d.keys()) == {"platform", "topic", "title", "body", "created_at", "published"}

    def test_to_dict_values(self):
        item = ContentItem(platform="blog", topic="AI", title="Hello", body="World")
        assert item.to_dict()["platform"] == "blog"
        assert item.to_dict()["published"] is False


class TestContentGeneratorInit:
    def test_requires_platforms(self):
        with pytest.raises(ValueError, match="platform"):
            ContentGenerator(platforms=[], topics=TOPICS)

    def test_requires_topics(self):
        with pytest.raises(ValueError, match="topic"):
            ContentGenerator(platforms=PLATFORMS, topics=[])

    def test_invalid_max_items(self):
        with pytest.raises(ValueError, match="max_items_per_run"):
            ContentGenerator(platforms=PLATFORMS, topics=TOPICS, max_items_per_run=0)


class TestContentGeneratorRun:
    def _make(self, max_items=3, dry_run=True):
        return ContentGenerator(
            platforms=PLATFORMS,
            topics=TOPICS,
            max_items_per_run=max_items,
            dry_run=dry_run,
        )

    def test_run_returns_correct_count(self):
        gen = self._make(max_items=4)
        items = gen.run()
        assert len(items) == 4

    def test_run_items_have_known_platform(self):
        gen = self._make(max_items=10)
        for item in gen.run():
            assert item.platform in PLATFORMS

    def test_run_items_have_known_topic(self):
        gen = self._make(max_items=10)
        for item in gen.run():
            assert item.topic in TOPICS

    def test_dry_run_does_not_publish(self):
        published = []
        gen = ContentGenerator(
            platforms=PLATFORMS,
            topics=TOPICS,
            max_items_per_run=3,
            publisher=lambda item: published.append(item),
            dry_run=True,
        )
        gen.run()
        assert published == []

    def test_publisher_called_when_not_dry_run(self):
        published = []
        gen = ContentGenerator(
            platforms=PLATFORMS,
            topics=TOPICS,
            max_items_per_run=3,
            publisher=lambda item: published.append(item),
            dry_run=False,
        )
        gen.run()
        assert len(published) == 3

    def test_publisher_failure_does_not_raise(self):
        def bad_publisher(item):
            raise RuntimeError("network down")

        gen = ContentGenerator(
            platforms=PLATFORMS,
            topics=TOPICS,
            max_items_per_run=2,
            publisher=bad_publisher,
            dry_run=False,
        )
        items = gen.run()  # must not raise
        assert len(items) == 2
        for item in items:
            assert item.published is False


class TestGenerateForTopic:
    def test_single_item(self):
        gen = ContentGenerator(platforms=PLATFORMS, topics=TOPICS, dry_run=True)
        item = gen.generate_for_topic("machine learning", "blog")
        assert item.topic == "machine learning"
        assert item.platform == "blog"

    def test_empty_topic_raises(self):
        gen = ContentGenerator(platforms=PLATFORMS, topics=TOPICS, dry_run=True)
        with pytest.raises(ValueError):
            gen.generate_for_topic("", "blog")

    def test_empty_platform_raises(self):
        gen = ContentGenerator(platforms=PLATFORMS, topics=TOPICS, dry_run=True)
        with pytest.raises(ValueError):
            gen.generate_for_topic("AI", "")
