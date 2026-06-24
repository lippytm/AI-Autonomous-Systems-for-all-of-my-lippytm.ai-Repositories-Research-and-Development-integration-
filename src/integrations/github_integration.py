"""
GitHub API integration for AI Autonomous Systems.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from github import Github, GithubException
from github.Repository import Repository

from src.core.config import Config
from src.core.logger import get_logger


logger = get_logger(__name__)


class GitHubIntegration:
    """Wraps PyGitHub to provide high-level repository operations."""

    def __init__(self, config: Config) -> None:
        self._config = config
        token = config.github_token
        if not token:
            raise ValueError(
                "GitHub token is required. Set the GITHUB_TOKEN environment variable."
            )
        self._client = Github(token)

    # ------------------------------------------------------------------ #
    # Repository helpers                                                   #
    # ------------------------------------------------------------------ #

    def get_repository(self, full_name: str) -> Repository:
        """Return a GitHub Repository object for *full_name* (``owner/repo``)."""
        return self._client.get_repo(full_name)

    def list_repositories(self) -> List[Repository]:
        """Return Repository objects for all configured repositories."""
        repos: List[Repository] = []
        for name in self._config.github_repositories:
            try:
                repos.append(self.get_repository(name))
            except GithubException as exc:
                logger.warning("Could not access repository %s: %s", name, exc)
        return repos

    # ------------------------------------------------------------------ #
    # File helpers                                                         #
    # ------------------------------------------------------------------ #

    def get_file_content(self, repo: Repository, path: str, ref: str = "") -> Optional[str]:
        """Return decoded text content of *path* in *repo*, or ``None`` if missing.

        Args:
            repo: Target GitHub repository.
            path: File path relative to the repository root.
            ref: Optional git ref (branch name, tag, or commit SHA) to read from.
        """
        try:
            kwargs: Dict[str, Any] = {}
            if ref:
                kwargs["ref"] = ref
            contents = repo.get_contents(path, **kwargs)
            if isinstance(contents, list):
                return None
            return contents.decoded_content.decode("utf-8", errors="replace")
        except GithubException:
            return None

    def list_files(
        self,
        repo: Repository,
        path: str = "",
        extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """Recursively list file paths in *repo* under *path*.

        Args:
            repo: Target GitHub repository.
            path: Sub-directory to start from (empty string = root).
            extensions: If provided, only return files with these extensions.

        Returns:
            List of file paths relative to the repository root.
        """
        results: List[str] = []
        try:
            contents = repo.get_contents(path)
            if not isinstance(contents, list):
                contents = [contents]
            for item in contents:
                if item.type == "dir":
                    results.extend(self.list_files(repo, item.path, extensions))
                else:
                    if extensions is None or any(
                        item.path.endswith(ext) for ext in extensions
                    ):
                        results.append(item.path)
        except GithubException as exc:
            logger.warning("Error listing files in %s at '%s': %s", repo.full_name, path, exc)
        return results

    # ------------------------------------------------------------------ #
    # Issue helpers                                                        #
    # ------------------------------------------------------------------ #

    def create_issue(
        self,
        repo: Repository,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """Create a GitHub issue and return it, or ``None`` on failure."""
        try:
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or self._config.notification_assignees,
            )
            logger.info("Created issue #%d in %s", issue.number, repo.full_name)
            return issue
        except GithubException as exc:
            logger.error("Failed to create issue in %s: %s", repo.full_name, exc)
            return None

    # ------------------------------------------------------------------ #
    # Pull-request helpers                                                 #
    # ------------------------------------------------------------------ #

    def create_pull_request(
        self,
        repo: Repository,
        title: str,
        body: str,
        head: str,
        base: str = "",
        labels: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """Create a pull request and return it, or ``None`` on failure."""
        if not base:
            base = self._config.github_default_branch
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
            )
            for label in (labels or self._config.github_pr_labels):
                try:
                    pr.add_to_labels(label)
                except GithubException:
                    pass
            logger.info("Created PR #%d in %s", pr.number, repo.full_name)
            return pr
        except GithubException as exc:
            logger.error("Failed to create PR in %s: %s", repo.full_name, exc)
            return None
