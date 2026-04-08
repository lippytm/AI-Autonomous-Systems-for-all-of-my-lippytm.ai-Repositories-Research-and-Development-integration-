"""AI Research Agent.

Monitors all lippytm repositories, analyses trends, summarises activity,
and generates research reports on AI, Web3, and autonomous-systems topics
relevant to the portfolio.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ResearchTopic:
    """A research topic derived from repository activity."""

    topic: str
    repo_names: list[str]
    priority: str  # high | medium | low
    keywords: list[str] = field(default_factory=list)


@dataclass
class ResearchReport:
    """Output of the research agent for a set of repositories."""

    title: str
    summary: str
    findings: list[str]
    recommendations: list[str]
    related_repos: list[str]
    technologies: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    model_used: str = ""


class ResearchAgent:
    """Autonomous research agent that analyses the lippytm repository portfolio.

    Capabilities:
    - Analyse repository metadata and issue patterns
    - Identify technology trends across the portfolio
    - Generate research reports on AI, Web3, and automation
    - Recommend integration opportunities between repositories
    - Surface educational content opportunities
    """

    RESEARCH_DOMAINS: list[str] = [
        "Full-Stack AI Development",
        "Web3 and Blockchain Integration",
        "Autonomous Bot Systems",
        "Time Machine Automation",
        "Educational Technology (EdTech)",
        "Social Media AI Networks",
        "DevOps and CI/CD Automation",
        "Decentralised Applications (dApps)",
        "Natural Language Processing (NLP)",
        "Multi-Agent Orchestration",
    ]

    TECH_TAGS: dict[str, list[str]] = {
        "ai": ["openai", "gpt", "llm", "neural", "ml", "machine learning", "anthropic"],
        "web3": ["ethereum", "blockchain", "defi", "nft", "solidity", "web3"],
        "bots": ["bot", "automation", "chatbot", "manychat", "botbuilders"],
        "typescript": ["typescript", "ts", "next.js", "react", "gatsby"],
        "python": ["python", "flask", "fastapi", "django", "pydantic"],
        "devops": ["ci", "cd", "github actions", "docker", "kubernetes"],
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

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyse_portfolio(self, repo_summaries: list[dict[str, Any]]) -> list[ResearchTopic]:
        """Identify research topics from repository metadata."""
        topics: list[ResearchTopic] = []

        # Group repos by dominant technology tag
        tag_groups: dict[str, list[str]] = {}
        for repo in repo_summaries:
            name = repo.get("name", "")
            desc = (repo.get("description") or "").lower()
            lang = (repo.get("language") or "").lower()
            combined = f"{name.lower()} {desc} {lang}"

            for tag, keywords in self.TECH_TAGS.items():
                if any(kw in combined for kw in keywords):
                    tag_groups.setdefault(tag, []).append(name)

        for tag, repos in tag_groups.items():
            priority = "high" if len(repos) >= 3 else "medium" if len(repos) >= 2 else "low"
            topics.append(
                ResearchTopic(
                    topic=f"{tag.upper()} Integration Opportunities",
                    repo_names=repos,
                    priority=priority,
                    keywords=self.TECH_TAGS.get(tag, []),
                )
            )

        return sorted(topics, key=lambda t: {"high": 0, "medium": 1, "low": 2}[t.priority])

    def identify_integration_opportunities(
        self, repo_summaries: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Find repos that would benefit from deeper cross-repo integration."""
        opportunities = []

        python_repos = [r["name"] for r in repo_summaries if (r.get("language") or "").lower() == "python"]
        ts_repos = [r["name"] for r in repo_summaries if (r.get("language") or "").lower() == "typescript"]
        js_repos = [r["name"] for r in repo_summaries if (r.get("language") or "").lower() == "javascript"]

        if python_repos and ts_repos:
            opportunities.append(
                {
                    "type": "polyglot_bridge",
                    "description": "Create a shared REST/GraphQL API layer bridging Python and TypeScript repos",
                    "repos": python_repos + ts_repos,
                    "priority": "high",
                }
            )

        high_issue_repos = [r["name"] for r in repo_summaries if r.get("open_issues", 0) > 10]
        if high_issue_repos:
            opportunities.append(
                {
                    "type": "issue_triage",
                    "description": "Deploy AI issue triage agent to reduce open issue backlog",
                    "repos": high_issue_repos,
                    "priority": "medium",
                }
            )

        bot_repos = [r["name"] for r in repo_summaries if "bot" in r.get("name", "").lower()]
        if len(bot_repos) >= 2:
            opportunities.append(
                {
                    "type": "bot_consolidation",
                    "description": "Unify bot management under AllBots.com umbrella with shared SDK",
                    "repos": bot_repos,
                    "priority": "high",
                }
            )

        return opportunities

    def generate_research_report(
        self,
        repo_summaries: list[dict[str, Any]],
        focus_area: str | None = None,
    ) -> ResearchReport:
        """Generate a comprehensive research report for the portfolio."""
        topics = self.analyse_portfolio(repo_summaries)
        opportunities = self.identify_integration_opportunities(repo_summaries)
        technologies = self._extract_technologies(repo_summaries)

        if self._api_key:
            summary, findings, recommendations = self._llm_research_report(
                repo_summaries, topics, opportunities, focus_area
            )
        else:
            summary, findings, recommendations = self._placeholder_report(
                repo_summaries, topics, opportunities
            )

        return ResearchReport(
            title=f"lippytm.ai Portfolio Research Report – {focus_area or 'Full Analysis'}",
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            related_repos=[r.get("name", "") for r in repo_summaries],
            technologies=technologies,
            model_used=self._model if self._api_key else "placeholder",
        )

    def generate_technology_trend_report(self) -> dict[str, Any]:
        """Generate a technology trend analysis across all domains."""
        return {
            "domains": self.RESEARCH_DOMAINS,
            "emerging_tech": [
                "Large Language Models (LLMs) for code generation",
                "Multi-agent autonomous systems",
                "Web3 + AI convergence (AI-powered DeFi)",
                "Blockchain-based AI model provenance",
                "Edge AI for bot deployment",
            ],
            "recommended_integrations": [
                "OpenAI GPT-4o for all repos lacking AI capabilities",
                "Web3.py for Python repos to add blockchain features",
                "GitHub Actions AI reviewer for automated PR quality",
                "Unified analytics dashboard across all repositories",
            ],
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_technologies(self, repo_summaries: list[dict[str, Any]]) -> list[str]:
        tech: set[str] = set()
        for repo in repo_summaries:
            if lang := repo.get("language"):
                tech.add(lang)
            name_lower = (repo.get("name") or "").lower()
            desc_lower = (repo.get("description") or "").lower()
            for tag, keywords in self.TECH_TAGS.items():
                if any(kw in name_lower or kw in desc_lower for kw in keywords):
                    tech.add(tag.upper())
        return sorted(tech)

    def _llm_research_report(
        self,
        repo_summaries: list[dict[str, Any]],
        topics: list[ResearchTopic],
        opportunities: list[dict[str, Any]],
        focus_area: str | None,
    ) -> tuple[str, list[str], list[str]]:
        repo_list = "\n".join(
            f"- {r.get('name')}: {r.get('description', 'No description')}"
            for r in repo_summaries
        )
        topic_list = "\n".join(f"- {t.topic} (priority: {t.priority})" for t in topics)
        opp_list = "\n".join(f"- {o['type']}: {o['description']}" for o in opportunities)

        prompt = (
            f"You are a senior AI research analyst reviewing the lippytm.ai GitHub portfolio.\n\n"
            f"Repositories:\n{repo_list}\n\n"
            f"Identified research topics:\n{topic_list}\n\n"
            f"Integration opportunities:\n{opp_list}\n\n"
            f"Focus area: {focus_area or 'overall portfolio strategy'}\n\n"
            "Provide:\n"
            "1. A 2-paragraph executive summary\n"
            "2. 5 key findings (as bullet points)\n"
            "3. 5 strategic recommendations\n\n"
            "Format as JSON: {\"summary\": \"\", \"findings\": [], \"recommendations\": []}"
        )
        try:
            raw = self._call_llm(prompt)
            import json
            data = json.loads(raw)
            return (
                data.get("summary", ""),
                data.get("findings", []),
                data.get("recommendations", []),
            )
        except Exception:
            return self._placeholder_report(repo_summaries, topics, opportunities)

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
            temperature=0.5,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic  # type: ignore[import]
        client = anthropic.Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _placeholder_report(
        self,
        repo_summaries: list[dict[str, Any]],
        topics: list[ResearchTopic],
        opportunities: list[dict[str, Any]],
    ) -> tuple[str, list[str], list[str]]:
        summary = (
            f"The lippytm.ai portfolio contains {len(repo_summaries)} repositories spanning "
            "AI, Web3, bot automation, and educational technology. "
            "The portfolio demonstrates a strong focus on autonomous AI systems and blockchain integration. "
            "Configure an LLM API key to generate an AI-powered analysis."
        )
        findings = [f"Topic identified: {t.topic} (priority: {t.priority})" for t in topics[:5]]
        recommendations = [
            f"Integration opportunity: {o['description']}" for o in opportunities[:5]
        ]
        return summary, findings, recommendations
