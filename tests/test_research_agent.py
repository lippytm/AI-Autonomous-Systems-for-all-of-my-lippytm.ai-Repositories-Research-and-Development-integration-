"""Tests for ResearchAgent."""

from __future__ import annotations

import pytest

from src.autonomous.research_agent import ResearchAgent, ResearchReport, ResearchTopic


@pytest.fixture()
def agent() -> ResearchAgent:
    return ResearchAgent(api_key="", provider="openai", model="gpt-4o")


SAMPLE_REPOS = [
    {"name": "Web3AI", "description": "Web3 AI platform", "language": "Python", "open_issues": 16},
    {"name": "AllBots.com", "description": "Bot management", "language": "", "open_issues": 1},
    {"name": "Chatlippytm.ai.Bots", "description": "Chat bots", "language": "Python", "open_issues": 8},
    {"name": "AI-Full-Stack-AI-DevOps-Synthetic-Intelligence-Engines-AgentsBots-Web3-Websites-",
     "description": "AI Web3 Websites", "language": "TypeScript", "open_issues": 3},
    {"name": "lippytm-lippytm.ai-tower-control-ai",
     "description": "Control tower for ChatGPT", "language": "JavaScript", "open_issues": 9},
]


class TestResearchAgent:
    def test_analyse_portfolio_returns_topics(self, agent: ResearchAgent) -> None:
        topics = agent.analyse_portfolio(SAMPLE_REPOS)
        assert isinstance(topics, list)
        assert len(topics) > 0
        assert all(isinstance(t, ResearchTopic) for t in topics)

    def test_topics_sorted_by_priority(self, agent: ResearchAgent) -> None:
        topics = agent.analyse_portfolio(SAMPLE_REPOS)
        priorities = [t.priority for t in topics]
        order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(priorities) - 1):
            assert order[priorities[i]] <= order[priorities[i + 1]]

    def test_identify_integration_opportunities(self, agent: ResearchAgent) -> None:
        opps = agent.identify_integration_opportunities(SAMPLE_REPOS)
        assert isinstance(opps, list)
        types = {o["type"] for o in opps}
        # Python + TypeScript repos exist → polyglot_bridge expected
        assert "polyglot_bridge" in types

    def test_integration_opportunities_high_issues(self, agent: ResearchAgent) -> None:
        opps = agent.identify_integration_opportunities(SAMPLE_REPOS)
        types = {o["type"] for o in opps}
        # Web3AI has 16 issues → issue_triage expected
        assert "issue_triage" in types

    def test_integration_opportunities_bot_consolidation(self, agent: ResearchAgent) -> None:
        opps = agent.identify_integration_opportunities(SAMPLE_REPOS)
        types = {o["type"] for o in opps}
        # AllBots.com + Chatlippytm.ai.Bots → bot_consolidation expected
        assert "bot_consolidation" in types

    def test_generate_research_report_returns_report(self, agent: ResearchAgent) -> None:
        report = agent.generate_research_report(SAMPLE_REPOS)
        assert isinstance(report, ResearchReport)
        assert len(report.summary) > 0
        assert isinstance(report.findings, list)
        assert isinstance(report.recommendations, list)
        assert len(report.related_repos) == len(SAMPLE_REPOS)

    def test_generate_research_report_with_focus(self, agent: ResearchAgent) -> None:
        report = agent.generate_research_report(SAMPLE_REPOS, focus_area="Web3 Integration")
        assert "Web3 Integration" in report.title

    def test_generate_technology_trend_report(self, agent: ResearchAgent) -> None:
        report = agent.generate_technology_trend_report()
        assert "domains" in report
        assert "emerging_tech" in report
        assert "recommended_integrations" in report
        assert len(report["domains"]) > 0

    def test_extract_technologies(self, agent: ResearchAgent) -> None:
        tech = agent._extract_technologies(SAMPLE_REPOS)
        assert "Python" in tech
        assert "TypeScript" in tech

    def test_placeholder_report_contains_repo_count(self, agent: ResearchAgent) -> None:
        topics = agent.analyse_portfolio(SAMPLE_REPOS)
        opps = agent.identify_integration_opportunities(SAMPLE_REPOS)
        summary, findings, recs = agent._placeholder_report(SAMPLE_REPOS, topics, opps)
        assert str(len(SAMPLE_REPOS)) in summary
