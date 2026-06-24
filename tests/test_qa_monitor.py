"""Tests for QAMonitor."""

import pytest

from src.quality.qa_monitor import CheckResult, QAMonitor


PROJECT_ROOT = "."
ALL_CHECKS = ["lint", "test", "coverage"]


def _pass_runner(cmd, cwd):
    return 0, "ok", ""


def _fail_runner(cmd, cwd):
    return 1, "", "error output"


class TestCheckResult:
    def test_to_dict_keys(self):
        r = CheckResult(name="lint", passed=True, message="clean")
        d = r.to_dict()
        assert {"name", "passed", "message", "ran_at"} == set(d.keys())


class TestQAMonitorInit:
    def test_empty_project_root_raises(self):
        with pytest.raises(ValueError):
            QAMonitor(project_root="")

    def test_invalid_coverage_threshold(self):
        with pytest.raises(ValueError):
            QAMonitor(project_root=PROJECT_ROOT, coverage_threshold=110)

    def test_unknown_check_raises(self):
        with pytest.raises(ValueError, match="Unknown check"):
            QAMonitor(project_root=PROJECT_ROOT, checks=["unknown_check"])

    def test_valid_init(self):
        monitor = QAMonitor(project_root=PROJECT_ROOT, checks=["lint"], dry_run=True)
        assert monitor.project_root == PROJECT_ROOT


class TestQAMonitorRun:
    def test_dry_run_all_pass(self):
        monitor = QAMonitor(project_root=PROJECT_ROOT, checks=ALL_CHECKS, dry_run=True)
        results = monitor.run()
        assert all(r.passed for r in results)
        assert len(results) == len(ALL_CHECKS)

    def test_all_passed_true(self):
        monitor = QAMonitor(project_root=PROJECT_ROOT, dry_run=True)
        results = monitor.run()
        assert monitor.all_passed(results) is True

    def test_pass_runner_gives_pass(self):
        monitor = QAMonitor(
            project_root=PROJECT_ROOT,
            checks=["lint"],
            runner=_pass_runner,
        )
        results = monitor.run()
        assert results[0].passed is True

    def test_fail_runner_gives_fail(self):
        monitor = QAMonitor(
            project_root=PROJECT_ROOT,
            checks=["lint"],
            runner=_fail_runner,
        )
        results = monitor.run()
        assert results[0].passed is False

    def test_all_passed_false_on_failure(self):
        monitor = QAMonitor(
            project_root=PROJECT_ROOT,
            checks=["lint", "test"],
            runner=_fail_runner,
        )
        results = monitor.run()
        assert monitor.all_passed(results) is False

    def test_history_accumulates(self):
        monitor = QAMonitor(project_root=PROJECT_ROOT, checks=["lint"], dry_run=True)
        monitor.run()
        monitor.run()
        assert len(monitor.get_history()) == 2

    def test_summary_counts(self):
        monitor = QAMonitor(project_root=PROJECT_ROOT, checks=ALL_CHECKS, dry_run=True)
        monitor.run()
        s = monitor.summary()
        assert s["total"] == len(ALL_CHECKS)
        assert s["passed"] == len(ALL_CHECKS)
        assert s["failed"] == 0


class TestMultipleChecks:
    def test_mixed_results(self):
        call_count = [0]

        def mixed_runner(cmd, cwd):
            call_count[0] += 1
            # first call passes, second fails
            return (0, "ok", "") if call_count[0] == 1 else (1, "", "fail")

        monitor = QAMonitor(
            project_root=PROJECT_ROOT,
            checks=["lint", "test"],
            runner=mixed_runner,
        )
        results = monitor.run()
        assert results[0].passed is True
        assert results[1].passed is False
        assert monitor.all_passed(results) is False
