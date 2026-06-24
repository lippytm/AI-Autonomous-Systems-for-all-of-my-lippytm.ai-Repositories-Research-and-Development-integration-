"""Repository-integration manager.

Discovers GitHub repositories for a given organisation and exposes a
lightweight API for fetching repo metadata.  All HTTP calls go through
a *http_client* callable so the class is fully testable without a live
GitHub token.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Type alias: given (url, headers) returns a list of raw repo dicts.
HttpClientType = Callable[[str, Dict[str, str]], List[Dict]]


@dataclass
class RepoInfo:
    """Metadata for a single repository."""

    name: str
    full_name: str
    description: str
    url: str
    default_branch: str = "main"
    language: Optional[str] = None
    stars: int = 0
    open_issues: int = 0
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "url": self.url,
            "default_branch": self.default_branch,
            "language": self.language,
            "stars": self.stars,
            "open_issues": self.open_issues,
            "fetched_at": self.fetched_at.isoformat(),
        }


class RepoManager:
    """Discovers and caches metadata for repositories in a GitHub org.

    Parameters
    ----------
    org:
        GitHub organisation / user name.
    token:
        Optional GitHub personal access token for authenticated requests.
    http_client:
        Callable ``(url, headers) -> List[dict]`` returning raw GitHub
        API repo objects.  Defaults to a stub that returns sample data.
    dry_run:
        When ``True`` the stub client is always used.
    """

    _GITHUB_API = "https://api.github.com"

    def __init__(
        self,
        org: str,
        token: Optional[str] = None,
        http_client: Optional[HttpClientType] = None,
        dry_run: bool = False,
    ) -> None:
        if not org:
            raise ValueError("org must not be empty.")

        self.org = org
        self._token = token
        self.dry_run = dry_run
        self._client: HttpClientType = (
            self._stub_client if dry_run else (http_client or self._stub_client)
        )
        self._repos: Dict[str, RepoInfo] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover(self) -> List[RepoInfo]:
        """Fetch repositories for the configured org.

        Returns the list of :class:`RepoInfo` objects discovered.
        """
        url = f"{self._GITHUB_API}/orgs/{self.org}/repos?per_page=100&type=all"
        headers = self._auth_headers()
        raw_repos = self._safe_fetch(url, headers)

        discovered: List[RepoInfo] = []
        for raw in raw_repos:
            info = self._parse(raw)
            self._repos[info.full_name] = info
            discovered.append(info)

        logger.info("RepoManager discovered %d repo(s) for org '%s'.", len(discovered), self.org)
        return discovered

    def get_repo(self, full_name: str) -> Optional[RepoInfo]:
        """Return a cached :class:`RepoInfo` by its full name, or ``None``."""
        return self._repos.get(full_name)

    def list_repos(self) -> List[RepoInfo]:
        """Return all cached repositories."""
        return list(self._repos.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _safe_fetch(self, url: str, headers: Dict[str, str]) -> List[Dict]:
        try:
            return self._client(url, headers)
        except Exception:
            logger.exception("RepoManager failed to fetch '%s'.", url)
            return []

    @staticmethod
    def _parse(raw: Dict) -> RepoInfo:
        return RepoInfo(
            name=raw.get("name", "unknown"),
            full_name=raw.get("full_name", raw.get("name", "unknown")),
            description=raw.get("description") or "",
            url=raw.get("html_url", raw.get("url", "")),
            default_branch=raw.get("default_branch", "main"),
            language=raw.get("language"),
            stars=raw.get("stargazers_count", 0),
            open_issues=raw.get("open_issues_count", 0),
        )

    @staticmethod
    def _stub_client(url: str, headers: Dict[str, str]) -> List[Dict]:
        logger.debug("RepoManager stub_client called for url=%s", url)
        return [
            {
                "name": "stub-repo",
                "full_name": "lippytm/stub-repo",
                "description": "Stub repository — replace with real GitHub client.",
                "html_url": "https://github.com/lippytm/stub-repo",
                "default_branch": "main",
                "language": "Python",
                "stargazers_count": 0,
                "open_issues_count": 0,
            }
        ]
