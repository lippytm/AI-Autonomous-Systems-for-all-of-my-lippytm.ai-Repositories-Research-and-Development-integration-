"""
Code Improvement Agent — analyzes source files and surfaces improvement suggestions.
"""
from __future__ import annotations

import os
from typing import Any, List

from github.Repository import Repository

from src.agents.base_agent import AgentResult, BaseAgent


class CodeImprovementAgent(BaseAgent):
    """Scans source files and uses AI to suggest code improvements.

    Optionally creates GitHub issues for each finding when
    ``notifications.github_issues`` is enabled.
    """

    name = "code_improvement"

    # ------------------------------------------------------------------ #
    # Implementation                                                       #
    # ------------------------------------------------------------------ #

    def _run(self, repo: Repository, result: AgentResult) -> None:
        cfg = self._agent_config
        if not cfg.get("enabled", True):
            self._logger.info("Code improvement agent disabled for %s", repo.full_name)
            return

        extensions: List[str] = cfg.get("target_extensions", [".py", ".js", ".ts"])
        max_files: int = int(cfg.get("max_files_per_run", 10))
        min_lines: int = int(cfg.get("min_lines", 5))

        self._logger.info("Listing source files in %s", repo.full_name)
        all_files = self._github.list_files(repo, extensions=extensions)
        target_files = all_files[:max_files]

        self._logger.info(
            "Analysing %d/%d files in %s", len(target_files), len(all_files), repo.full_name
        )

        for file_path in target_files:
            self._analyse_file(repo, file_path, min_lines, result)

    def _analyse_file(
        self,
        repo: Repository,
        file_path: str,
        min_lines: int,
        result: AgentResult,
    ) -> None:
        content = self._github.get_file_content(repo, file_path)
        if content is None:
            return

        lines = content.splitlines()
        if len(lines) < min_lines:
            return

        _, ext = os.path.splitext(file_path)
        language = _EXT_LANGUAGE.get(ext, "")

        self._logger.debug("Analysing %s (%d lines)", file_path, len(lines))
        try:
            suggestions = self._ai.analyze_code(content, language)
        except Exception as exc:  # noqa: BLE001
            result.add_error(f"AI analysis failed for {file_path}: {exc}")
            return

        if suggestions.strip():
            result.add_finding(
                category="code_quality",
                description=f"**{file_path}**\n\n{suggestions}",
                severity="info",
            )
            self._logger.info("Improvement suggestions generated for %s", file_path)

            if self._config.notify_github_issues:
                self._github.create_issue(
                    repo,
                    title=f"[AI] Code improvement suggestions for `{file_path}`",
                    body=(
                        f"The AI Autonomous System analyzed `{file_path}` "
                        f"and found the following suggestions:\n\n{suggestions}"
                    ),
                    labels=["ai-autonomous", "code-quality"],
                )
                result.add_action(f"Created GitHub issue for {file_path}")


# Mapping of file extension → language name for AI prompts
_EXT_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".php": "php",
    ".sh": "bash",
}
