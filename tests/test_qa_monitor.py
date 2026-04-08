"""Tests for QAMonitor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.quality.qa_monitor import (
    PortfolioHealthReport,
    QAMonitor,
    QualityScore,
)


@pytest.fixture()
def monitor() -> QAMonitor:
    return QAMonitor()


def _repo(
    name: str = "test-repo",
    description: str = "A well-described test repository for quality testing",
    language: str = "Python",
    open_issues: int = 5,
    has_ci: bool = True,
    days_since_update: int = 10,
) -> dict:
    updated = (datetime.now(timezone.utc) - timedelta(days=days_since_update)).isoformat()
    return {
        "name": name,
        "description": description,
        "language": language,
        "open_issues": open_issues,
        "has_ci": has_ci,
        "last_updated": updated,
    }


class TestQAMonitor:
    def test_score_repo_returns_quality_score(self, monitor: QAMonitor) -> None:
        score = monitor.score_repo(_repo())
        assert isinstance(score, QualityScore)
        assert 0.0 <= score.overall_score <= 1.0

    def test_healthy_repo_scores_high(self, monitor: QAMonitor) -> None:
        score = monitor.score_repo(_repo(has_ci=True, open_issues=2))
        assert score.overall_score >= 0.70

    def test_high_issue_count_lowers_score(self, monitor: QAMonitor) -> None:
        score_low = monitor.score_repo(_repo(open_issues=2))
        score_high = monitor.score_repo(_repo(open_issues=30))
        assert score_high.overall_score < score_low.overall_score

    def test_stale_repo_lowers_activity_score(self, monitor: QAMonitor) -> None:
        fresh = monitor.score_repo(_repo(days_since_update=5))
        stale = monitor.score_repo(_repo(days_since_update=180))
        assert stale.activity_score < fresh.activity_score

    def test_missing_description_lowers_doc_score(self, monitor: QAMonitor) -> None:
        score = monitor.score_repo(_repo(description=""))
        assert score.documentation_score < 1.0
        assert any("description" in issue.lower() for issue in score.issues)

    def test_no_ci_lowers_ci_score(self, monitor: QAMonitor) -> None:
        with_ci = monitor.score_repo(_repo(has_ci=True))
        without_ci = monitor.score_repo(_repo(has_ci=False))
        assert without_ci.ci_score < with_ci.ci_score

    def test_no_language_ci_score_neutral(self, monitor: QAMonitor) -> None:
        score = monitor.score_repo(_repo(language="", has_ci=False))
        assert score.ci_score == 0.5

    def test_score_recommendations_populated(self, monitor: QAMonitor) -> None:
        score = monitor.score_repo(_repo(has_ci=False, open_issues=20, description=""))
        assert len(score.recommendations) > 0

    def test_analyse_portfolio_returns_health_report(self, monitor: QAMonitor) -> None:
        repos = [
            _repo("repo-a", open_issues=2, has_ci=True),
            _repo("repo-b", open_issues=25, has_ci=False, description=""),
        ]
        report = monitor.analyse_portfolio(repos)
        assert isinstance(report, PortfolioHealthReport)
        assert report.total_repos == 2
        assert report.healthy_repos + report.warning_repos + report.critical_repos == 2

    def test_overall_score_between_0_and_1(self, monitor: QAMonitor) -> None:
        repos = [_repo(f"repo-{i}") for i in range(5)]
        report = monitor.analyse_portfolio(repos)
        assert 0.0 <= report.overall_score <= 1.0

    def test_get_critical_repos(self, monitor: QAMonitor) -> None:
        repos = [
            _repo("good", open_issues=1, has_ci=True),
            _repo("bad", open_issues=50, has_ci=False, description="", days_since_update=200),
        ]
        report = monitor.analyse_portfolio(repos)
        critical = monitor.get_critical_repos(report)
        assert all(s.overall_score < 0.40 for s in critical)

    def test_get_top_repos(self, monitor: QAMonitor) -> None:
        repos = [_repo(f"repo-{i}", open_issues=i * 3) for i in range(6)]
        report = monitor.analyse_portfolio(repos)
        top = monitor.get_top_repos(report, n=3)
        assert len(top) == 3
        scores = [s.overall_score for s in top]
        assert scores == sorted(scores, reverse=True)

    def test_global_recommendations_not_empty(self, monitor: QAMonitor) -> None:
        repos = [_repo("r", has_ci=False)]
        report = monitor.analyse_portfolio(repos)
        assert len(report.global_recommendations) > 0

    def test_compute_activity_score_empty_date(self, monitor: QAMonitor) -> None:
        score = monitor._compute_activity_score("", [], [])
        assert score == 0.5

    def test_compute_activity_score_invalid_date(self, monitor: QAMonitor) -> None:
        score = monitor._compute_activity_score("not-a-date", [], [])
        assert score == 0.5
