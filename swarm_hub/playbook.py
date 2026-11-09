"""Shared repair playbook: how the swarm learns from, and teaches, real failures.

Each pattern pairs a regex over CI logs with a diagnosis, a fix, the capability
of the agent that should own it, and a real example line. The examples make the
playbook self-testing: ``Playbook.selftest()`` proves every lesson still
recognises the failure it was learned from. When an agent solves a new problem,
``learn()`` records it so every other agent can diagnose it next time.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PLAYBOOK = Path(__file__).with_name("playbook.json")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{1,63}")
_REQUIRED = ("id", "match", "diagnosis", "fix", "capability", "severity", "example")
SEVERITIES = ("blocking", "flaky", "warning")


@dataclass(frozen=True)
class Pattern:
    id: str
    match: str
    diagnosis: str
    fix: str
    capability: str
    severity: str
    example: str
    learned_from: str = ""

    def __post_init__(self):
        if not _ID.fullmatch(self.id):
            raise ValueError(f"Invalid pattern id: {self.id!r}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.id}: severity must be one of {SEVERITIES}")
        try:
            re.compile(self.match, re.MULTILINE)
        except re.error as exc:
            raise ValueError(f"{self.id}: invalid regex: {exc}") from None

    @property
    def regex(self) -> re.Pattern[str]:
        return re.compile(self.match, re.MULTILINE)


@dataclass(frozen=True)
class Diagnosis:
    pattern: Pattern
    evidence: str
    count: int


class Playbook:
    def __init__(self, patterns: list[Pattern], path: Path | None = None):
        ids = [p.id for p in patterns]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate pattern ids in playbook")
        self.patterns = list(patterns)
        self.path = path

    def diagnose(self, log_text: str) -> list[Diagnosis]:
        """Return every known problem found in ``log_text``, blocking issues first."""
        found = []
        for pattern in self.patterns:
            matches = list(pattern.regex.finditer(log_text))
            if matches:
                start = log_text.rfind("\n", 0, matches[0].start()) + 1
                end = log_text.find("\n", matches[0].end())
                line = log_text[start:end if end != -1 else None].strip()
                found.append(Diagnosis(pattern, line[:300], len(matches)))
        order = {s: i for i, s in enumerate(SEVERITIES)}
        return sorted(found, key=lambda d: order[d.pattern.severity])

    def learn(self, pattern: Pattern, save: bool = True) -> None:
        """Add a lesson. It must recognise its own example before it is accepted."""
        missing = [name for name in _REQUIRED if not str(getattr(pattern, name)).strip()]
        if missing:
            raise ValueError(f"{pattern.id}: missing {', '.join(missing)}")
        if any(p.id == pattern.id for p in self.patterns):
            raise ValueError(f"Pattern already known: {pattern.id}")
        if not pattern.regex.search(pattern.example):
            raise ValueError(f"{pattern.id}: regex does not match its own example")
        self.patterns.append(pattern)
        if save and self.path:
            self.save()

    def selftest(self) -> list[str]:
        """Return a list of problems; empty means every lesson still works."""
        problems = []
        for pattern in self.patterns:
            if not pattern.regex.search(pattern.example):
                problems.append(f"{pattern.id}: does not match its example")
        return problems

    def save(self) -> None:
        data = {"version": 1, "patterns": [asdict(p) for p in self.patterns]}
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_playbook(path: str | Path = DEFAULT_PLAYBOOK) -> Playbook:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    patterns = []
    for entry in data["patterns"]:
        missing = [k for k in _REQUIRED if not entry.get(k)]
        if missing:
            raise ValueError(f"{entry.get('id', '?')}: missing {', '.join(missing)}")
        patterns.append(Pattern(**entry))
    return Playbook(patterns, path)
