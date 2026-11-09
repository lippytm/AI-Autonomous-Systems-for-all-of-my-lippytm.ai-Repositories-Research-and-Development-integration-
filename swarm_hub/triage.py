"""Pull-request triage: decide what each open PR needs, without touching it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

BOTS = {"dependabot[bot]", "renovate[bot]"}
STALE_DAYS = 120
HUGE_ADDITIONS = 20_000


@dataclass(frozen=True)
class PullRequest:
    repo: str
    number: int
    title: str
    author: str
    draft: bool
    mergeable: bool | None
    mergeable_state: str
    additions: int
    changed_files: int
    created: date
    ci: str  # pass | fail | pending | none


@dataclass(frozen=True)
class Verdict:
    action: str
    reason: str


# Actions, roughly in the order an owner should work through them.
ACTIONS = (
    "merge-ready",        # non-draft, clean, green
    "review-then-merge",  # clean and green or no CI, but still a draft
    "fix-ci",             # merges cleanly, a check is red
    "split-or-reject",    # far too large to review
    "close-stale",        # conflicting and old: almost certainly superseded
    "rebase",             # conflicting but recent
    "close-empty",        # no changes at all
    "wait",               # GitHub has not computed mergeability yet
)


def triage(pr: PullRequest, today: date) -> Verdict:
    age = (today - pr.created).days
    if pr.changed_files == 0:
        return Verdict("close-empty", "PR has no changes")
    if pr.mergeable is None or pr.mergeable_state == "unknown":
        return Verdict("wait", "GitHub is still computing mergeability; re-run triage")
    if pr.mergeable_state == "dirty" or pr.mergeable is False:
        if age > STALE_DAYS:
            return Verdict("close-stale", f"conflicts with base and is {age} days old")
        return Verdict("rebase", "conflicts with base branch")
    if pr.additions > HUGE_ADDITIONS:
        return Verdict("split-or-reject", f"+{pr.additions} lines is too large to review safely")
    if pr.ci == "fail":
        return Verdict("fix-ci", "merges cleanly but a required check is failing")
    if pr.ci == "pending":
        return Verdict("wait", "checks still running")
    if pr.draft:
        return Verdict("review-then-merge", "clean draft; owner must review and mark ready")
    if pr.ci == "none" and pr.author not in BOTS:
        return Verdict("review-then-merge", "clean but no CI ran; needs a manual check")
    return Verdict("merge-ready", "clean, not a draft, checks green")
