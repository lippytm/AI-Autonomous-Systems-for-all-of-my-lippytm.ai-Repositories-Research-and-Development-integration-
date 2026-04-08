"""Autonomous R&D research agent.

Continuously fetches summaries from configured sources (e.g. arXiv,
GitHub Trending) and stores structured findings for downstream use.
All HTTP calls are isolated behind a *fetcher* callable to keep the
class fully testable without network access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResearchFinding:
    """A single research result returned by the agent."""

    source: str
    title: str
    summary: str
    url: str = ""
    tags: List[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "tags": self.tags,
            "fetched_at": self.fetched_at.isoformat(),
        }


# Type alias for a fetcher: given source name + query returns raw data.
FetcherType = Callable[[str, str], List[Dict]]


class ResearchAgent:
    """Fetches and aggregates research findings from multiple sources.

    Parameters
    ----------
    sources:
        List of source identifiers (e.g. ``["arxiv", "github_trending"]``).
    fetcher:
        Callable ``(source, query) -> List[dict]`` that returns raw result
        dicts with at least ``title``, ``summary``, and optionally ``url``
        and ``tags`` keys.  Defaults to an empty stub so the class works
        without live connections.
    dry_run:
        When ``True`` the agent uses the stub fetcher regardless of what
        *fetcher* was passed.
    """

    def __init__(
        self,
        sources: List[str],
        fetcher: Optional[FetcherType] = None,
        dry_run: bool = False,
    ) -> None:
        if not sources:
            raise ValueError("At least one source must be specified.")

        self.sources = sources
        self.dry_run = dry_run
        self._fetcher: FetcherType = (
            self._stub_fetcher if dry_run else (fetcher or self._stub_fetcher)
        )
        self._findings: List[ResearchFinding] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, query: str) -> List[ResearchFinding]:
        """Fetch findings for *query* from all configured sources.

        Returns the new :class:`ResearchFinding` objects collected this run.
        """
        if not query:
            raise ValueError("query must not be empty.")

        new_findings: List[ResearchFinding] = []
        for source in self.sources:
            raw_items = self._safe_fetch(source, query)
            for raw in raw_items:
                finding = self._parse(source, raw)
                self._findings.append(finding)
                new_findings.append(finding)

        logger.info(
            "ResearchAgent fetched %d finding(s) for query '%s'.",
            len(new_findings),
            query,
        )
        return new_findings

    def get_findings(self) -> List[ResearchFinding]:
        """Return all accumulated findings."""
        return list(self._findings)

    def clear(self) -> None:
        """Clear accumulated findings."""
        self._findings.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _safe_fetch(self, source: str, query: str) -> List[Dict]:
        try:
            return self._fetcher(source, query)
        except Exception:
            logger.exception("Failed to fetch from source '%s'.", source)
            return []

    @staticmethod
    def _parse(source: str, raw: Dict) -> ResearchFinding:
        return ResearchFinding(
            source=source,
            title=raw.get("title", "Untitled"),
            summary=raw.get("summary", ""),
            url=raw.get("url", ""),
            tags=raw.get("tags", []),
        )

    @staticmethod
    def _stub_fetcher(source: str, query: str) -> List[Dict]:
        """Return sample findings — used when *dry_run* is True or no
        real fetcher is provided."""
        logger.debug("ResearchAgent stub_fetcher called: source=%s query=%s", source, query)
        return [
            {
                "title": f"[stub] Latest advances in {query}",
                "summary": (
                    f"A stub summary from {source} about {query}. "
                    "Replace this fetcher with a real implementation."
                ),
                "url": "",
                "tags": [query, source],
            }
        ]
