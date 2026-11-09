"""Prevention: catch known failures in workflow files before CI ever runs them.

Every playbook lesson describes a failure *after* it happened. A prevention rule
looks for the cause in the source instead, so the same failure never happens in
another repository. Each rule carries a ``bad`` and a ``good`` example, and
``selftest()`` proves that every rule flags its bad example and passes its good
one, the same guarantee the playbook gives for lessons.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SEVERITY_ORDER = ("error", "warning", "info")


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    path: str
    line: int
    evidence: str
    message: str
    fix: str
    prevents: str


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    prevents: str  # playbook lesson id this rule stops from recurring
    message: str
    fix: str
    bad: str
    good: str
    check: Callable[[str, Path | None], list[tuple[int, str]]]


def _uses(text: str, pattern: str) -> list[tuple[int, str]]:
    regex = re.compile(rf"^\s*-?\s*uses:\s*['\"]?({pattern})['\"]?\s*(#.*)?$")
    return [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1) if regex.match(line)]


def _grants(text: str, scope: str) -> bool:
    return bool(re.search(rf"^\s*{re.escape(scope)}:\s*write\b", text, re.M)
                or re.search(r"^\s*permissions:\s*write-all\b", text, re.M))


def _check_retired_artifact(text, root):
    return _uses(text, r"actions/(?:upload|download)-artifact@v[123](?:\.[\d.]+)?")


def _check_codeql_v3(text, root):
    return _uses(text, r"github/codeql-action/[\w-]+@v[123](?:\.[\d.]+)?")


def _check_old_core_actions(text, root):
    return _uses(text, r"actions/(?:checkout@v[123]|setup-python@v[1234]|setup-node@v[123])(?:\.[\d.]+)?")


def _check_unpinned(text, root):
    return _uses(text, r"[\w.-]+/[\w./-]+@(?:master|main|HEAD)")


def _check_push_permission(text, root):
    if _grants(text, "contents"):
        return []
    hits = _uses(text, r"peter-evans/create-pull-request@\S+")
    hits += [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1)
             if re.search(r"(^|[\s;&|])git push\b", line) and not line.strip().startswith("#")]
    return hits


def _check_sarif_permission(text, root):
    return [] if _grants(text, "security-events") else _uses(text, r"github/codeql-action/upload-sarif@\S+")


_FILE_REFS = re.compile(r"(?:pip3? install(?: [^\n]*?)? -r|python3? )\s*([\w./-]+\.(?:txt|py))\b")


def _check_missing_files(text, root):
    if root is None:
        return []
    dirs = [root] + [root / d for d in re.findall(r"working-directory:\s*['\"]?([\w./-]+)", text)]
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("#") or "${{" in line:
            continue
        for ref in _FILE_REFS.findall(line):
            if not any((d / ref).exists() for d in dirs):
                hits.append((n, line.strip()))
    return hits


def _check_dependency_review(text, root):
    return _uses(text, r"actions/dependency-review-action@\S+")


RULES = [
    Rule("retired-artifact-action", "error", "deprecated-artifact-action",
         "actions/upload-artifact or download-artifact v1-v3 is retired; GitHub fails the job at 'Set up job'.",
         "Use @v4 and give each upload a unique name.",
         "      - uses: actions/upload-artifact@v3\n", "      - uses: actions/upload-artifact@v4\n",
         _check_retired_artifact),
    Rule("missing-referenced-file", "error", "missing-requirements-file",
         "The workflow runs or installs a file that does not exist in the repository.",
         "Commit the file, fix the path, or remove the step.",
         "        run: pip install -r requirements-does-not-exist.txt\n",
         "        run: python -m unittest\n", _check_missing_files),
    Rule("push-without-write-permission", "error", "actions-push-denied",
         "The workflow pushes or opens a PR, but never grants 'contents: write', so the token may be read-only.",
         "Add 'permissions: {contents: write, pull-requests: write}' to that workflow or job.",
         "jobs:\n  update:\n    steps:\n      - uses: peter-evans/create-pull-request@v6\n",
         "permissions:\n  contents: write\n  pull-requests: write\njobs:\n  update:\n    steps:\n"
         "      - uses: peter-evans/create-pull-request@v6\n", _check_push_permission),
    Rule("sarif-without-permission", "error", "sarif-upload-permission",
         "upload-sarif needs 'security-events: write'; without it the upload fails "
         "with 'Resource not accessible by integration'.",
         "Grant 'security-events: write' on the scanning job only.",
         "      - uses: github/codeql-action/upload-sarif@v4\n",
         "    permissions:\n      security-events: write\n    steps:\n"
         "      - uses: github/codeql-action/upload-sarif@v4\n", _check_sarif_permission),
    Rule("codeql-action-v3", "warning", "",
         "github/codeql-action v3 is deprecated in December 2026.",
         "Move every github/codeql-action/* step to @v4.",
         "      - uses: github/codeql-action/init@v3\n", "      - uses: github/codeql-action/init@v4\n",
         _check_codeql_v3),
    Rule("outdated-core-action", "warning", "",
         "This core action version runs on a retired Node.js runtime and will start failing.",
         "Use actions/checkout@v4+, actions/setup-python@v5+, actions/setup-node@v4+.",
         "      - uses: actions/setup-python@v4\n", "      - uses: actions/setup-python@v5\n",
         _check_old_core_actions),
    Rule("unpinned-action", "warning", "",
         "A third-party action is pinned to a moving branch; any push to it runs in your CI with your token.",
         "Pin to a release tag, or better, a full commit SHA.",
         "      - uses: aquasecurity/trivy-action@master\n", "      - uses: aquasecurity/trivy-action@0.28.0\n",
         _check_unpinned),
    Rule("dependency-review-needs-setting", "info", "dependency-graph-disabled",
         "Dependency review only works when the repository's Dependency graph is enabled; "
         "otherwise every PR fails it.",
         "Confirm Settings > Code security > Dependency graph is on (free for public repos).",
         "      - uses: actions/dependency-review-action@v4\n", "      - uses: actions/checkout@v4\n",
         _check_dependency_review),
]


def scan_text(text: str, path: str = "<text>", root: Path | None = None,
              rules: list[Rule] = RULES) -> list[Finding]:
    findings = []
    for rule in rules:
        for line, evidence in rule.check(text, root):
            findings.append(Finding(rule.id, rule.severity, path, line, evidence[:200],
                                    rule.message, rule.fix, rule.prevents))
    order = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    return sorted(findings, key=lambda f: (order[f.severity], f.path, f.line))


def scan_repository(root: str | Path) -> list[Finding]:
    root = Path(root)
    workflows = root / ".github" / "workflows"
    findings = []
    for path in sorted(workflows.glob("*.y*ml")) if workflows.is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        findings += scan_text(text, str(path.relative_to(root)), root)
    order = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    return sorted(findings, key=lambda f: (order[f.severity], f.path, f.line))


def selftest(rules: list[Rule] = RULES) -> list[str]:
    problems = []
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        problems.append("duplicate rule ids")
    for rule in rules:
        if rule.severity not in SEVERITY_ORDER:
            problems.append(f"{rule.id}: bad severity {rule.severity!r}")
        root = Path(__file__).parent
        if not rule.check(rule.bad, root):
            problems.append(f"{rule.id}: does not flag its bad example")
        if rule.check(rule.good, root):
            problems.append(f"{rule.id}: flags its good example")
    for rule_id in AUTOFIXES:
        rule = next((r for r in rules if r.id == rule_id), None)
        if rule is None:
            problems.append(f"autofix {rule_id}: no such rule")
            continue
        fixed, applied = autofix_text(rule.bad)
        if rule_id not in applied or rule.check(fixed, Path(__file__).parent):
            problems.append(f"autofix {rule_id}: does not clear its own bad example")
    return problems


# ── Auto-fix ──────────────────────────────────────────────────────────────────
# Only fixes that are a pure, local substitution are automatic. Structural edits
# (adding permission blocks, pinning to a SHA that needs a network lookup) stay
# findings for an agent or person, because a wrong YAML edit can break a workflow.

_USES_PREFIX = r"(^\s*-?\s*uses:\s*['\"]?)"
AUTOFIXES: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "retired-artifact-action": [
        (re.compile(_USES_PREFIX + r"(actions/(?:upload|download)-artifact)@v[123](?:\.[\d.]+)?", re.M),
         r"\1\2@v4"),
    ],
    "codeql-action-v3": [
        (re.compile(_USES_PREFIX + r"(github/codeql-action/[\w-]+)@v[123](?:\.[\d.]+)?", re.M), r"\1\2@v4"),
    ],
    "outdated-core-action": [
        (re.compile(_USES_PREFIX + r"(actions/checkout)@v[123](?:\.[\d.]+)?", re.M), r"\1\2@v4"),
        (re.compile(_USES_PREFIX + r"(actions/setup-python)@v[1234](?:\.[\d.]+)?", re.M), r"\1\2@v5"),
        (re.compile(_USES_PREFIX + r"(actions/setup-node)@v[123](?:\.[\d.]+)?", re.M), r"\1\2@v4"),
    ],
}


def autofix_text(text: str) -> tuple[str, list[str]]:
    """Apply every automatic fix. Returns the new text and the rule ids applied."""
    applied = []
    for rule_id, substitutions in AUTOFIXES.items():
        for regex, replacement in substitutions:
            text, count = regex.subn(replacement, text)
            if count:
                applied.append(rule_id)
    return text, sorted(set(applied))


def autofix_repository(root: str | Path, write: bool = False) -> list[dict]:
    """Fix workflow files under ``root``; verify each fixed rule no longer fires.

    Returns one record per changed file with the unified diff. Raises if a fix
    leaves its own finding behind, so a bad auto-fix can never be written.
    """
    import difflib

    root = Path(root)
    changes = []
    workflows = root / ".github" / "workflows"
    for path in sorted(workflows.glob("*.y*ml")) if workflows.is_dir() else []:
        before = path.read_text(encoding="utf-8")
        after, applied = autofix_text(before)
        if after == before:
            continue
        remaining = {f.rule for f in scan_text(after, str(path), root)} & set(applied)
        if remaining:
            raise RuntimeError(f"{path}: auto-fix did not clear {sorted(remaining)}")
        rel = str(path.relative_to(root))
        diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                            f"a/{rel}", f"b/{rel}"))
        if write:
            path.write_text(after, encoding="utf-8")
        changes.append({"path": rel, "rules": applied, "diff": diff})
    return changes
