"""Quality-assurance monitor.

Runs configurable health checks (lint, test, coverage threshold) and
reports pass/fail results.  All shell commands are delegated to a
*runner* callable so the module stays testable without spawning real
subprocesses.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# A runner receives (command, cwd) and returns (return_code, stdout, stderr).
RunnerType = Callable[[List[str], Optional[str]], Tuple[int, str, str]]


@dataclass
class CheckResult:
    """Result of a single QA check."""

    name: str
    passed: bool
    message: str
    ran_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "ran_at": self.ran_at.isoformat(),
        }


class QAMonitor:
    """Runs quality-assurance checks on a project.

    Parameters
    ----------
    project_root:
        Filesystem path to the project to check.
    checks:
        Which checks to run.  Supported values: ``"lint"``, ``"test"``,
        ``"coverage"``.
    coverage_threshold:
        Minimum acceptable test-coverage percentage (0–100).
    runner:
        Callable ``(cmd_list, cwd) -> (returncode, stdout, stderr)``.
        Defaults to a real :func:`subprocess.run` wrapper.
    dry_run:
        When ``True`` all checks are skipped and reported as passed.
    """

    SUPPORTED_CHECKS = frozenset({"lint", "test", "coverage"})

    def __init__(
        self,
        project_root: str,
        checks: Optional[List[str]] = None,
        coverage_threshold: float = 80.0,
        runner: Optional[RunnerType] = None,
        dry_run: bool = False,
    ) -> None:
        if not project_root:
            raise ValueError("project_root must not be empty.")
        if coverage_threshold < 0 or coverage_threshold > 100:
            raise ValueError("coverage_threshold must be between 0 and 100.")

        requested = set(checks or list(self.SUPPORTED_CHECKS))
        unknown = requested - self.SUPPORTED_CHECKS
        if unknown:
            raise ValueError(f"Unknown check(s): {sorted(unknown)}")

        self.project_root = project_root
        self.checks = list(requested)
        self.coverage_threshold = coverage_threshold
        self.dry_run = dry_run
        self._runner: RunnerType = runner or self._subprocess_runner
        self._history: List[CheckResult] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> List[CheckResult]:
        """Execute all configured checks.

        Returns the list of :class:`CheckResult` objects for this run.
        """
        results: List[CheckResult] = []
        for check in self.checks:
            result = self._run_check(check)
            self._history.append(result)
            results.append(result)
            level = logging.INFO if result.passed else logging.WARNING
            logger.log(level, "QA check '%s': %s", check, "PASS" if result.passed else "FAIL")
        return results

    def all_passed(self, results: List[CheckResult]) -> bool:
        """Return ``True`` if every result in *results* passed."""
        return all(r.passed for r in results)

    def summary(self) -> Dict[str, int]:
        """Aggregate pass/fail counts across all historical runs."""
        passed = sum(1 for r in self._history if r.passed)
        return {
            "total": len(self._history),
            "passed": passed,
            "failed": len(self._history) - passed,
        }

    def get_history(self) -> List[CheckResult]:
        """Return all check results from previous runs."""
        return list(self._history)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_check(self, check: str) -> CheckResult:
        if self.dry_run:
            return CheckResult(name=check, passed=True, message="dry_run — skipped")

        if check == "lint":
            return self._check_lint()
        if check == "test":
            return self._check_test()
        if check == "coverage":
            return self._check_coverage()
        return CheckResult(name=check, passed=False, message=f"Unknown check: {check}")

    def _check_lint(self) -> CheckResult:
        rc, stdout, stderr = self._runner(
            ["python", "-m", "flake8", "--max-line-length=99", "src"],
            self.project_root,
        )
        if rc == 0:
            return CheckResult(name="lint", passed=True, message="No lint issues found.")
        output = (stdout + stderr).strip()
        return CheckResult(name="lint", passed=False, message=output or "Lint errors detected.")

    def _check_test(self) -> CheckResult:
        rc, stdout, stderr = self._runner(
            ["python", "-m", "pytest", "--tb=short", "-q"],
            self.project_root,
        )
        output = (stdout + stderr).strip()
        if rc == 0:
            return CheckResult(name="test", passed=True, message=output or "All tests passed.")
        return CheckResult(name="test", passed=False, message=output or "Tests failed.")

    def _check_coverage(self) -> CheckResult:
        rc, stdout, stderr = self._runner(
            [
                "python", "-m", "pytest",
                "--cov=src",
                f"--cov-fail-under={int(self.coverage_threshold)}",
                "--cov-report=term-missing",
                "-q",
            ],
            self.project_root,
        )
        output = (stdout + stderr).strip()
        if rc == 0:
            return CheckResult(
                name="coverage",
                passed=True,
                message=output or f"Coverage >= {self.coverage_threshold}%.",
            )
        return CheckResult(
            name="coverage",
            passed=False,
            message=output or f"Coverage < {self.coverage_threshold}%.",
        )

    @staticmethod
    def _subprocess_runner(
        cmd: List[str], cwd: Optional[str]
    ) -> Tuple[int, str, str]:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError as exc:
            return 1, "", str(exc)
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out."
