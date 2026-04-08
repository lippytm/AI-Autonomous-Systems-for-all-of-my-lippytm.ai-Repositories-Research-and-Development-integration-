"""Quality Assurance Monitor.

Monitors all lippytm repositories for code quality, open issues,
stale PRs, missing documentation, and CI/CD health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class QualityScore:
    """Quality score for a single repository."""

    repo_name: str
    overall_score: float  # 0.0 – 1.0
    issue_score: float
    activity_score: float
    documentation_score: float
    ci_score: float
    issues: list[str] = field(default_factory=list)  # quality issues found
    recommendations: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")


@dataclass
class PortfolioHealthReport:
    """Health report covering all repositories."""

    total_repos: int
    healthy_repos: int
    warning_repos: int
    critical_repos: int
    overall_score: float
    repo_scores: list[QualityScore] = field(default_factory=list)
    global_recommendations: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")


class QAMonitor:
    """Autonomous quality-assurance monitor for the lippytm.ai portfolio.

    Thresholds
    ----------
    healthy   : overall_score >= 0.70
    warning   : 0.40 <= overall_score < 0.70
    critical  : overall_score < 0.40
    """

    # Scoring weights (must sum to 1.0)
    WEIGHTS: dict[str, float] = {
        "issue_score": 0.25,
        "activity_score": 0.30,
        "documentation_score": 0.25,
        "ci_score": 0.20,
    }

    # Thresholds
    HIGH_ISSUE_COUNT = 15
    STALE_DAYS = 60
    MIN_DESCRIPTION_LEN = 20

    def __init__(
        self,
        stale_days: int = 60,
        high_issue_threshold: int = 15,
    ) -> None:
        self._stale_days = stale_days
        self._high_issue_threshold = high_issue_threshold

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_repo(self, repo_data: dict[str, Any]) -> QualityScore:
        """Compute a quality score for a single repository."""
        issues_found: list[str] = []
        recommendations: list[str] = []

        # ── Issue score ──────────────────────────────────────────────
        open_issues = repo_data.get("open_issues", 0)
        if open_issues >= self._high_issue_threshold:
            issue_score = max(0.0, 1.0 - (open_issues - self._high_issue_threshold) / 30)
            issues_found.append(f"High open-issue count: {open_issues}")
            recommendations.append("Triage and close stale issues")
        else:
            issue_score = 1.0

        # ── Activity score ───────────────────────────────────────────
        last_updated = repo_data.get("last_updated", "")
        activity_score = self._compute_activity_score(last_updated, issues_found, recommendations)

        # ── Documentation score ──────────────────────────────────────
        description = repo_data.get("description", "") or ""
        if len(description) < self.MIN_DESCRIPTION_LEN:
            documentation_score = 0.4
            issues_found.append("Missing or very short repository description")
            recommendations.append("Add a meaningful description to the repository")
        elif len(description) < 60:
            documentation_score = 0.7
        else:
            documentation_score = 1.0

        # ── CI/CD score ──────────────────────────────────────────────
        language = repo_data.get("language", "")
        has_ci = repo_data.get("has_ci", False)
        if not language:
            ci_score = 0.5  # no language = no CI expectation
        elif has_ci:
            ci_score = 1.0
        else:
            ci_score = 0.3
            issues_found.append("No CI/CD pipeline detected")
            recommendations.append(f"Add GitHub Actions CI/CD workflow for {language} project")

        # ── Overall ──────────────────────────────────────────────────
        overall = (
            self.WEIGHTS["issue_score"] * issue_score
            + self.WEIGHTS["activity_score"] * activity_score
            + self.WEIGHTS["documentation_score"] * documentation_score
            + self.WEIGHTS["ci_score"] * ci_score
        )

        return QualityScore(
            repo_name=repo_data.get("name", "unknown"),
            overall_score=round(overall, 3),
            issue_score=round(issue_score, 3),
            activity_score=round(activity_score, 3),
            documentation_score=round(documentation_score, 3),
            ci_score=round(ci_score, 3),
            issues=issues_found,
            recommendations=recommendations,
        )

    def _compute_activity_score(
        self,
        last_updated: str,
        issues_found: list[str],
        recommendations: list[str],
    ) -> float:
        if not last_updated:
            return 0.5
        try:
            updated_dt = datetime.fromisoformat(last_updated.rstrip("Z")).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_since = (now - updated_dt).days
            if days_since > self._stale_days:
                issues_found.append(f"Repository not updated in {days_since} days")
                recommendations.append("Resume active development or archive if no longer maintained")
                return max(0.0, 1.0 - (days_since - self._stale_days) / 180)
            return min(1.0, 1.0 - days_since / self._stale_days)
        except (ValueError, TypeError):
            return 0.5

    # ------------------------------------------------------------------
    # Portfolio analysis
    # ------------------------------------------------------------------

    def analyse_portfolio(self, repo_list: list[dict[str, Any]]) -> PortfolioHealthReport:
        """Analyse the health of the entire repository portfolio."""
        scores = [self.score_repo(repo) for repo in repo_list]

        healthy = sum(1 for s in scores if s.overall_score >= 0.70)
        warning = sum(1 for s in scores if 0.40 <= s.overall_score < 0.70)
        critical = sum(1 for s in scores if s.overall_score < 0.40)
        overall = sum(s.overall_score for s in scores) / len(scores) if scores else 0.0

        global_recs = self._global_recommendations(scores)

        return PortfolioHealthReport(
            total_repos=len(scores),
            healthy_repos=healthy,
            warning_repos=warning,
            critical_repos=critical,
            overall_score=round(overall, 3),
            repo_scores=scores,
            global_recommendations=global_recs,
        )

    def _global_recommendations(self, scores: list[QualityScore]) -> list[str]:
        recs: list[str] = []
        no_ci = [s.repo_name for s in scores if s.ci_score < 0.5]
        stale = [s.repo_name for s in scores if s.activity_score < 0.3]
        high_issues = [s.repo_name for s in scores if s.issue_score < 0.5]

        if no_ci:
            recs.append(
                f"Add CI/CD to {len(no_ci)} repos: {', '.join(no_ci[:3])}"
                + (" and more..." if len(no_ci) > 3 else "")
            )
        if stale:
            recs.append(
                f"{len(stale)} repos are stale (>60 days inactive): "
                + ", ".join(stale[:3])
                + (" and more..." if len(stale) > 3 else "")
            )
        if high_issues:
            recs.append(
                f"Reduce open issues in: {', '.join(high_issues[:3])}"
                + (" and more..." if len(high_issues) > 3 else "")
            )
        if not recs:
            recs.append("Portfolio health is good – keep up the great work!")
        return recs

    def get_critical_repos(self, health_report: PortfolioHealthReport) -> list[QualityScore]:
        """Return repositories with critical quality scores."""
        return [s for s in health_report.repo_scores if s.overall_score < 0.40]

    def get_top_repos(self, health_report: PortfolioHealthReport, n: int = 5) -> list[QualityScore]:
        """Return the top N repositories by quality score."""
        return sorted(health_report.repo_scores, key=lambda s: s.overall_score, reverse=True)[:n]
