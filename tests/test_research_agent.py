"""Tests for ResearchAgent."""

import pytest

from src.autonomous.research_agent import ResearchAgent, ResearchFinding


SOURCES = ["arxiv", "github_trending"]


def _fake_fetcher(source, query):
    return [
        {
            "title": f"Paper on {query} from {source}",
            "summary": f"Summary of {query}",
            "url": f"https://example.com/{source}/{query}",
            "tags": [query, source],
        }
    ]


class TestResearchFinding:
    def test_to_dict_keys(self):
        f = ResearchFinding(source="arxiv", title="T", summary="S")
        d = f.to_dict()
        assert "source" in d and "title" in d and "fetched_at" in d

    def test_default_url_empty(self):
        f = ResearchFinding(source="arxiv", title="T", summary="S")
        assert f.url == ""


class TestResearchAgentInit:
    def test_requires_sources(self):
        with pytest.raises(ValueError):
            ResearchAgent(sources=[])

    def test_dry_run_uses_stub(self):
        # dry_run ignores any provided fetcher
        called = []
        agent = ResearchAgent(sources=SOURCES, fetcher=lambda s, q: called.append(1) or [], dry_run=True)
        agent.run("AI")
        assert called == []  # real fetcher never invoked


class TestResearchAgentRun:
    def test_empty_query_raises(self):
        agent = ResearchAgent(sources=SOURCES, dry_run=True)
        with pytest.raises(ValueError):
            agent.run("")

    def test_run_returns_findings(self):
        agent = ResearchAgent(sources=SOURCES, fetcher=_fake_fetcher)
        findings = agent.run("robotics")
        # one finding per source
        assert len(findings) == len(SOURCES)

    def test_findings_accumulated(self):
        agent = ResearchAgent(sources=SOURCES, fetcher=_fake_fetcher)
        agent.run("robotics")
        agent.run("NLP")
        assert len(agent.get_findings()) == 2 * len(SOURCES)

    def test_clear_resets_findings(self):
        agent = ResearchAgent(sources=SOURCES, fetcher=_fake_fetcher)
        agent.run("robotics")
        agent.clear()
        assert agent.get_findings() == []

    def test_fetcher_failure_returns_empty(self):
        def bad_fetcher(s, q):
            raise RuntimeError("unreachable")

        agent = ResearchAgent(sources=SOURCES, fetcher=bad_fetcher)
        findings = agent.run("AI")  # must not raise
        assert findings == []

    def test_dry_run_returns_stub_findings(self):
        agent = ResearchAgent(sources=["arxiv"], dry_run=True)
        findings = agent.run("AI")
        assert len(findings) == 1
        assert "stub" in findings[0].title

    def test_finding_fields(self):
        agent = ResearchAgent(sources=["arxiv"], fetcher=_fake_fetcher)
        findings = agent.run("NLP")
        f = findings[0]
        assert f.source == "arxiv"
        assert "NLP" in f.title
        assert "NLP" in f.tags
