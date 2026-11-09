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
    # False when the fix is a repository setting, not a source edit; ``good`` is
    # then only a detector-negative fixture and must never be taught as a repair.
    source_fix: bool = True


def _uses(text: str, pattern: str) -> list[tuple[int, str]]:
    regex = re.compile(rf"^\s*-?\s*uses:\s*['\"]?({pattern})['\"]?\s*(#.*)?$")
    return [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1) if regex.match(line)]


def _is_content(line: str) -> bool:
    """Blank and comment-only lines never open or close a YAML block."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _child_indent(lines: list[str], start: int, end: int, default: int) -> int:
    """Indentation of the first real child line of the block at ``lines[start]``."""
    return next((len(lines[i]) - len(lines[i].lstrip()) for i in range(start + 1, end)
                 if _is_content(lines[i])), default)


def _block_end(lines: list[str], start: int) -> int:
    """Index just past the YAML block whose key is on ``lines[start]``."""
    indent = len(lines[start]) - len(lines[start].lstrip())
    for j in range(start + 1, len(lines)):
        if _is_content(lines[j]) and len(lines[j]) - len(lines[j].lstrip()) <= indent:
            return j
    return len(lines)


def _permissions_grant(lines: list[str], start: int, end: int, indent: int, scope: str) -> bool | None:
    """Does a ``permissions:`` key at ``indent`` within lines[start:end] grant ``scope: write``?

    Returns None when there is no permissions key at that level.
    """
    key = re.compile(rf"^ {{{indent}}}permissions:\s*(\S.*)?$")
    for i in range(start, end):
        m = key.match(lines[i])
        if not m:
            continue
        inline = (m.group(1) or "").split("#")[0].strip()
        if inline.startswith("{") and inline.endswith("}"):  # flow mapping: {contents: write, ...}
            pairs = dict(part.split(":", 1) for part in inline[1:-1].split(",") if ":" in part)
            return {k.strip(): v.strip() for k, v in pairs.items()}.get(scope) == "write"
        if inline:
            return inline == "write-all"
        for j in range(i + 1, _block_end(lines, i)):
            if re.match(rf"^\s*{re.escape(scope)}:\s*write\b", lines[j]):
                return True
        return False
    return None


def _job_span(lines: list[str], index: int) -> tuple[int, int, int] | None:
    """(start, end, indent) of the job containing ``lines[index]``, if any."""
    jobs = next((i for i, line in enumerate(lines) if re.match(r"^jobs:\s*(#.*)?$", line)), None)
    if jobs is None or index <= jobs:
        return None
    header = re.compile(r"^( +)[\w-]+:\s*(#.*)?$")
    job_indent = None
    for i in range(jobs + 1, len(lines)):
        m = header.match(lines[i])
        if m:
            job_indent = len(m.group(1))
            break
    if job_indent is None:
        return None
    start = None
    for i in range(index, jobs, -1):
        m = header.match(lines[i])
        if m and len(m.group(1)) == job_indent:
            start = i
            break
    if start is None:
        return None
    return start, _block_end(lines, start), job_indent


def _grants_at(text: str, line_no: int, scope: str) -> bool:
    """Effective ``scope: write`` for the job containing 1-based ``line_no``.

    A job-level ``permissions`` block replaces the workflow-level one entirely,
    as GitHub does. With neither, assume the read-only default.
    """
    lines = text.splitlines()
    job = _job_span(lines, line_no - 1)
    if job:
        start, end, indent = job
        granted = _permissions_grant(lines, start + 1, end, _child_indent(lines, start, end, indent + 2), scope)
        if granted is not None:
            return granted
    granted = _permissions_grant(lines, 0, len(lines), 0, scope)
    return bool(granted)


def _check_retired_artifact(text, root):
    return _uses(text, r"actions/(?:upload|download)-artifact@v[123](?:\.[\d.]+)?")


def _check_codeql_v3(text, root):
    return _uses(text, r"github/codeql-action/[\w-]+@v[123](?:\.[\d.]+)?")


def _check_old_core_actions(text, root):
    return _uses(text, r"actions/(?:checkout@v[123]|setup-python@v[1234]|setup-node@v[123])(?:\.[\d.]+)?")


def _check_unpinned(text, root):
    return _uses(text, r"[\w.-]+/[\w./-]+@(?:master|main|HEAD)")


def _check_push_permission(text, root):
    hits = _uses(text, r"peter-evans/create-pull-request@\S+")
    hits += [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1)
             if re.search(r"(^|[\s;&|])git push\b", line) and not line.strip().startswith("#")]
    return [(n, e) for n, e in hits if not _grants_at(text, n, "contents")]


def _check_sarif_permission(text, root):
    return [(n, e) for n, e in _uses(text, r"github/codeql-action/upload-sarif@\S+")
            if not _grants_at(text, n, "security-events")]


# A file reference only counts at a shell command position: start of the run
# text or after && || ; |. Text such as `echo "python x.py"` is not a command.
_FILE_REFS = re.compile(r"(?:^|&&|\|\||;|\|)\s*(?:pip3? install(?: [^\n;&|]*?)? -r|python3? )"
                        r"\s*([\w./-]+\.(?:txt|py))\b")
_SHELL_COMMENT = re.compile(r"(^|\s)#.*$")  # `cmd # note` and whole-line comments
_CHANGES_DIR = re.compile(r"(^|[\s;&|])(cd|pushd)\s")
_RUN_KEY = re.compile(r"^(\s*)(?:-\s+)?run:\s*(.*)$")


def _run_commands(lines: list[str]) -> list[tuple[int, str]]:
    """(index, command text) for every line of shell inside a ``run:`` value."""
    out = []
    i = 0
    while i < len(lines):
        m = _RUN_KEY.match(lines[i])
        if not m:
            i += 1
            continue
        value = _SHELL_COMMENT.sub("", m.group(2)).strip()
        if value and value[0] not in "|>":
            out.append((i, value.strip("'\"")))
            i += 1
            continue
        key_indent = len(m.group(1))
        i += 1
        moved = False  # after cd/pushd the rest of this script runs somewhere unknown
        while i < len(lines) and (not lines[i].strip() or _indent(lines[i]) > key_indent):
            command = _SHELL_COMMENT.sub("", lines[i]).strip()
            if command and _CHANGES_DIR.search(command):
                moved = True
            if command and not moved:
                out.append((i, command))
            i += 1
    return out


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


_STEP = re.compile(r"^(\s*)-\s+\S")
_WORKDIR = re.compile(r"^\s*(?:-\s+)?working-directory:\s*['\"]?([\w./-]+)")


def _step_spans(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) index pairs for every list item that looks like a step."""
    spans = []
    for i, line in enumerate(lines):
        m = _STEP.match(line)
        if not m:
            continue
        indent, end = len(m.group(1)), len(lines)
        for j in range(i + 1, len(lines)):
            if _is_content(lines[j]) and _indent(lines[j]) <= indent:
                end = j
                break
        spans.append((i, end))
    return spans


def _effective_workdir(lines: list[str], index: int, spans: list[tuple[int, int]]) -> str | None:
    """The working directory a command on ``lines[index]`` really runs in."""
    enclosing = [s for s in spans if s[0] <= index < s[1]]
    if enclosing:
        start, end = max(enclosing)  # innermost step
        for j in range(start, end):
            m = _WORKDIR.match(lines[j])
            if m:
                return m.group(1)
    inside_steps = {j for s, e in spans for j in range(s, e)}
    job = _job_span(lines, index)
    if job:  # job-level defaults: inside this job, outside every step
        for j in range(job[0], job[1]):
            if j not in inside_steps:
                m = _WORKDIR.match(lines[j])
                if m:
                    return m.group(1)
    jobs = next((i for i, line in enumerate(lines) if re.match(r"^jobs:\s*(#.*)?$", line)), len(lines))
    for j in range(0, jobs):  # workflow-level defaults, before `jobs:`
        m = _WORKDIR.match(lines[j])
        if m:
            return m.group(1)
    return None


def _check_missing_files(text, root):
    if root is None:
        return []
    lines = text.splitlines()
    spans = _step_spans(lines)
    hits = []
    for n, command in _run_commands(lines):
        # Expressions and directory changes make the real path unknowable here; a
        # blocking error must not guess, so those commands are skipped.
        if "${{" in command or _CHANGES_DIR.search(command):
            continue
        refs = _FILE_REFS.findall(command)
        if not refs:
            continue
        workdir = _effective_workdir(lines, n, spans)
        base = root / workdir if workdir else root
        if any(not (base / ref).exists() for ref in refs):
            hits.append((n + 1, lines[n].strip()))
    return hits


def _check_dependency_review(text, root):
    return _uses(text, r"actions/dependency-review-action@\S+")


RULES = [
    Rule("retired-artifact-action", "error", "deprecated-artifact-action",
         "actions/upload-artifact or download-artifact v1-v3 is retired; GitHub fails the job at 'Set up job'.",
         "Migrate to @v4 by hand: give every upload a name unique across steps and matrix legs "
         "(e.g. include each matrix key), set include-hidden-files: true if hidden files are needed, "
         "and upgrade matching download-artifact steps in the same change.",
         "      - uses: actions/upload-artifact@v3\n        with:\n          name: reports\n",
         "      - uses: actions/upload-artifact@v4\n        with:\n          name: reports\n",
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
         "jobs:\n  scan:\n    permissions:\n      contents: read\n      security-events: write\n"
         "    steps:\n      - uses: github/codeql-action/upload-sarif@v4\n", _check_sarif_permission),
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
         _check_dependency_review, source_fix=False),
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
# upload/download-artifact v3 -> v4 is deliberately NOT automatic: v4 artifacts are
# immutable (duplicate names across steps or matrix legs fail) and exclude hidden
# files by default, so the upgrade changes behaviour and needs a real migration.

_USES_PREFIX = r"(^\s*-?\s*uses:\s*['\"]?)"
_TOKEN_END = r"(?=['\"]?\s*(?:#.*)?$)"  # the whole ref, so @v10 or @v1-custom never match
AUTOFIXES: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "codeql-action-v3": [
        (re.compile(_USES_PREFIX + r"(github/codeql-action/[\w-]+)@v[123](?:\.[\d.]+)?" + _TOKEN_END, re.M),
         r"\1\2@v4"),
    ],
    "outdated-core-action": [
        (re.compile(_USES_PREFIX + r"(actions/checkout)@v[123](?:\.[\d.]+)?" + _TOKEN_END, re.M), r"\1\2@v4"),
        (re.compile(_USES_PREFIX + r"(actions/setup-python)@v[1234](?:\.[\d.]+)?" + _TOKEN_END, re.M), r"\1\2@v5"),
        (re.compile(_USES_PREFIX + r"(actions/setup-node)@v[123](?:\.[\d.]+)?" + _TOKEN_END, re.M), r"\1\2@v4"),
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
