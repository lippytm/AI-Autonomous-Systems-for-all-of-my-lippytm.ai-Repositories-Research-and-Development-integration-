"""
Repository Management Agent — audits repositories for health and standards compliance.
"""
from __future__ import annotations

from typing import Any, List

from github.Repository import Repository

from src.agents.base_agent import AgentResult, BaseAgent


_STANDARD_FILES = ["README.md", ".gitignore", "LICENSE"]
_SECURITY_FILES = ["SECURITY.md", ".github/SECURITY.md"]
_CI_FILES = [".github/workflows", ".travis.yml", "Jenkinsfile", ".circleci/config.yml"]


class RepositoryAgent(BaseAgent):
    """Checks repositories for health indicators and best-practice files.

    Findings are surfaced as GitHub issues when notifications are enabled.
    """

    name = "repository"

    # ------------------------------------------------------------------ #
    # Implementation                                                       #
    # ------------------------------------------------------------------ #

    def _run(self, repo: Repository, result: AgentResult) -> None:
        cfg = self._agent_config
        if not cfg.get("enabled", True):
            self._logger.info("Repository agent disabled for %s", repo.full_name)
            return

        required_files: List[str] = cfg.get("check_missing_files", _STANDARD_FILES)

        self._check_missing_files(repo, required_files, result)
        self._check_security_policy(repo, result)
        self._check_ci_configuration(repo, result)
        self._check_open_issues(repo, result)

    # ------------------------------------------------------------------ #
    # Checks                                                               #
    # ------------------------------------------------------------------ #

    def _check_missing_files(
        self,
        repo: Repository,
        required_files: List[str],
        result: AgentResult,
    ) -> None:
        missing = []
        for filename in required_files:
            content = self._github.get_file_content(repo, filename)
            if content is None:
                missing.append(filename)

        if missing:
            description = (
                "The following standard files are missing from the repository:\n"
                + "\n".join(f"- `{f}`" for f in missing)
            )
            result.add_finding(
                category="repository_health",
                description=description,
                severity="warning",
            )
            if self._config.notify_github_issues:
                self._github.create_issue(
                    repo,
                    title="[AI] Missing standard repository files",
                    body=description,
                    labels=["ai-autonomous", "repository-health"],
                )
                result.add_action("Created issue for missing standard files")
        else:
            self._logger.info("All standard files present in %s", repo.full_name)

    def _check_security_policy(self, repo: Repository, result: AgentResult) -> None:
        has_policy = any(
            self._github.get_file_content(repo, f) is not None for f in _SECURITY_FILES
        )
        if not has_policy:
            result.add_finding(
                category="security",
                description=(
                    "No `SECURITY.md` policy found. "
                    "Consider adding one to document how to report vulnerabilities."
                ),
                severity="warning",
            )

    def _check_ci_configuration(self, repo: Repository, result: AgentResult) -> None:
        has_ci = False
        for path in _CI_FILES:
            content = self._github.get_file_content(repo, path)
            if content is not None:
                has_ci = True
                break
            # Also check if it's a directory (GitHub API returns list for dirs)
            files = self._github.list_files(repo, path)
            if files:
                has_ci = True
                break

        if not has_ci:
            result.add_finding(
                category="ci_cd",
                description=(
                    "No CI/CD configuration detected. "
                    "Consider adding GitHub Actions workflows or another CI system."
                ),
                severity="info",
            )

    def _check_open_issues(self, repo: Repository, result: AgentResult) -> None:
        try:
            open_issues = repo.open_issues_count
            if open_issues > 50:
                result.add_finding(
                    category="issue_management",
                    description=(
                        f"Repository has {open_issues} open issues. "
                        "Consider triaging and closing stale issues."
                    ),
                    severity="info",
                )
        except Exception as exc:  # noqa: BLE001
            result.add_error(f"Could not fetch open issue count: {exc}")
