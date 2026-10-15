#!/usr/bin/env python3
"""Local, dependency-free repository health and learning assistant."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
}
MAX_SCAN_DEPTH = 5

LESSONS = {
    "repo-basics": {
        "title": "Repository fundamentals",
        "content": (
            "A repository is a project directory tracked by Git. A README explains "
            "its purpose and how people can get started. A local health scan should "
            "inspect files and Git status without changing the project."
        ),
        "question": "Which file commonly introduces a repository? (A) README (B) node_modules (C) .git/objects",
        "answer": "a",
        "explanation": "README files introduce a project's purpose and usage.",
    },
    "testing": {
        "title": "Testing and repair",
        "content": (
            "Tests help catch regressions when code changes. A useful repair workflow "
            "first identifies a specific gap, proposes a small fix, and validates it. "
            "Never let an assistant rewrite projects without review and a recoverable "
            "version-control state."
        ),
        "question": "What should come before applying a suggested repair? (A) Review and validation (B) Delete the project history (C) Ignore the change",
        "answer": "a",
        "explanation": "Review and validation keep repairs understandable and recoverable.",
    },
    "automation-safety": {
        "title": "Safe repository automation",
        "content": (
            "Multi-repository automation should be explicit about which directories "
            "it can access, avoid reading secrets, and start in report-only mode. "
            "Apply changes only with clear authorization, a narrow scope, and a way "
            "to inspect the diff."
        ),
        "question": "What is the safest default for a new multi-repository tool? (A) Report-only (B) Rewrite every file (C) Publish all files",
        "answer": "a",
        "explanation": "Report-only behavior makes findings visible before any project changes.",
    },
}


def discover_repositories(root, max_depth=MAX_SCAN_DEPTH):
    """Find Git working trees below root without following symlinks."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Scan root is not a directory: {root}")

    repositories = []
    for current, directories, _files in os.walk(root, followlinks=False):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        directories[:] = [
            name
            for name in directories
            if name not in SKIP_DIRECTORIES
            and not (current_path / name).is_symlink()
        ]
        if (current_path / ".git").exists():
            repositories.append(current_path)
        if depth >= max_depth:
            directories[:] = []
    return sorted(repositories)


def _has_tests(repository):
    for current, directories, files in os.walk(repository, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name not in SKIP_DIRECTORIES
            and not (current_path / name).is_symlink()
        ]
        if "tests" in directories or "test" in directories:
            return True
        if any(
            name.startswith("test_")
            or name.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts"))
            for name in files
        ):
            return True
    return False


def inspect_repository(repository):
    """Return metadata and actionable findings without changing the repository."""
    repository = Path(repository)
    findings = []
    readme_exists = any(
        (repository / name).is_file()
        for name in ("README.md", "README.rst", "README.txt", "README")
    )
    tests_exist = _has_tests(repository)
    ci_exists = (repository / ".github" / "workflows").is_dir()

    if not readme_exists:
        findings.append(
            {
                "level": "suggestion",
                "check": "readme",
                "message": "No README was found; document the project's purpose and setup.",
            }
        )
    if not tests_exist:
        findings.append(
            {
                "level": "suggestion",
                "check": "tests",
                "message": "No recognizable test suite was found; add checks for core behavior.",
            }
        )
    if not ci_exists:
        findings.append(
            {
                "level": "suggestion",
                "check": "continuous-integration",
                "message": "No GitHub Actions workflows were found; consider automated validation.",
            }
        )

    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "status", "--short", "--branch"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode:
            git_status = "unavailable"
            findings.append(
                {
                    "level": "warning",
                    "check": "git-status",
                    "message": "Git status could not be read; verify Git is installed and the worktree is accessible.",
                }
            )
        else:
            git_status = result.stdout.strip().splitlines()[0] if result.stdout.strip() else "clean"
    except (OSError, subprocess.TimeoutExpired):
        git_status = "unavailable"
        findings.append(
            {
                "level": "warning",
                "check": "git-status",
                "message": "Git status could not be read; verify Git is installed and the worktree is accessible.",
            }
        )

    return {
        "path": str(repository),
        "readme": readme_exists,
        "tests": tests_exist,
        "github_actions": ci_exists,
        "git_status": git_status,
        "findings": findings,
    }


def scan(root):
    root = Path(root).expanduser().resolve()
    repositories = discover_repositories(root)
    return {
        "scan_root": str(root),
        "repository_count": len(repositories),
        "repositories": [inspect_repository(path) for path in repositories],
        "safety": (
            "Report-only scan: no project files, Git settings, or remote services were changed."
        ),
    }


def print_lessons():
    print("Available interactive lessons:")
    for lesson_id, lesson in LESSONS.items():
        print(f"  {lesson_id}: {lesson['title']}")


def run_lesson(lesson_id, input_fn=input, output_fn=print):
    lesson = LESSONS[lesson_id]
    output_fn(f"\n{lesson['title']}\n")
    output_fn(lesson["content"])
    output_fn(lesson["question"])
    try:
        answer = input_fn("> ").strip().lower()
    except EOFError:
        output_fn("Lesson stopped: no answer was provided.")
        return False
    if answer == lesson["answer"]:
        output_fn(f"Correct. {lesson['explanation']}")
        return True
    output_fn(f"Not quite. {lesson['explanation']}")
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scan local Git repositories and teach safe repository practices."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    scan_parser = commands.add_parser(
        "scan", help="Inspect repositories below a directory (report only)."
    )
    scan_parser.add_argument("root", help="Directory containing repositories.")
    scan_parser.add_argument(
        "--output",
        help="Optional path for a JSON report; parent directories are not created.",
    )

    learn_parser = commands.add_parser("learn", help="Start an interactive lesson.")
    learn_parser.add_argument(
        "--lesson", choices=sorted(LESSONS), help="Lesson identifier; omit to show the lesson menu."
    )
    args = parser.parse_args(argv)

    if args.command == "scan":
        try:
            report = scan(args.root)
            rendered = json.dumps(report, indent=2)
            if args.output:
                output_path = Path(args.output).expanduser()
                output_path.write_text(rendered + "\n", encoding="utf-8")
                print(f"Wrote report to {output_path}")
            else:
                print(rendered)
            return 0
        except (OSError, ValueError) as error:
            print(f"Scan failed: {error}", file=sys.stderr)
            return 2

    if args.lesson:
        run_lesson(args.lesson)
    else:
        print_lessons()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
