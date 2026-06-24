"""
Research Agent — investigates best practices and improvement opportunities.
"""
from __future__ import annotations

from typing import Any, List

from github.Repository import Repository

from src.agents.base_agent import AgentResult, BaseAgent


class ResearchAgent(BaseAgent):
    """Uses AI to research best practices and generate improvement recommendations.

    For each configured research topic, the agent summarizes the repository
    context and asks the AI model for targeted recommendations.
    """

    name = "research"

    # ------------------------------------------------------------------ #
    # Implementation                                                       #
    # ------------------------------------------------------------------ #

    def _run(self, repo: Repository, result: AgentResult) -> None:
        cfg = self._agent_config
        if not cfg.get("enabled", True):
            self._logger.info("Research agent disabled for %s", repo.full_name)
            return

        topics: List[str] = cfg.get(
            "research_topics",
            ["best practices", "security vulnerabilities", "performance optimizations"],
        )
        max_tasks: int = int(cfg.get("max_tasks_per_run", 5))

        readme = self._github.get_file_content(repo, "README.md") or ""
        file_list = self._github.list_files(repo)

        repo_summary = self._ai.summarize_repository(readme, file_list)
        result.add_finding(
            category="repository_summary",
            description=repo_summary,
            severity="info",
        )

        for topic in topics[:max_tasks]:
            self._research_topic(repo, topic, repo_summary, result)

    def _research_topic(
        self,
        repo: Repository,
        topic: str,
        repo_summary: str,
        result: AgentResult,
    ) -> None:
        self._logger.info("Researching '%s' for %s", topic, repo.full_name)
        system = (
            "You are a senior software engineer and researcher. "
            "Provide practical, specific, and actionable recommendations."
        )
        prompt = (
            f"Given the following repository summary:\n\n{repo_summary}\n\n"
            f"Research and provide the top 5 specific recommendations related to "
            f"**{topic}** for this project. "
            "Format as a numbered list with brief explanations."
        )
        try:
            recommendations = self._ai.complete(prompt, system=system)
        except Exception as exc:  # noqa: BLE001
            result.add_error(f"AI research failed for topic '{topic}': {exc}")
            return

        if recommendations.strip():
            result.add_finding(
                category=f"research_{topic.replace(' ', '_')}",
                description=f"### Research: {topic.title()}\n\n{recommendations}",
                severity="info",
            )
            self._logger.info("Research complete for topic '%s'", topic)

            if self._config.notify_github_issues:
                self._github.create_issue(
                    repo,
                    title=f"[AI Research] {topic.title()} — Recommendations",
                    body=(
                        f"The AI Research Agent has analyzed this repository and "
                        f"produced the following recommendations for **{topic}**:\n\n"
                        f"{recommendations}"
                    ),
                    labels=["ai-autonomous", "research"],
                )
                result.add_action(f"Created research issue for topic '{topic}'")
