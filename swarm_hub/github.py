"""Minimal read-only GitHub REST client (GET requests only)."""

from __future__ import annotations

import json
import os
import time
from datetime import date
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .triage import PullRequest

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token: str | None = None, opener=urlopen, timeout: int = 20):
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN", "")
        self._open = opener
        self.timeout = timeout

    def get(self, path: str):
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "swarm-hub",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with self._open(Request(API + path, headers=headers), timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            hint = ""
            if exc.code in (403, 429) and exc.headers and exc.headers.get("X-RateLimit-Remaining") == "0":
                hint = " (rate limit exhausted; set GITHUB_TOKEN)"
            raise GitHubError(f"GET {path} -> HTTP {exc.code}{hint}") from exc

    def open_pulls(self, owner: str, repo: str, settle_seconds: float = 0.0) -> list[PullRequest]:
        base = f"/repos/{quote(owner)}/{quote(repo)}"
        numbers = [p["number"] for p in self.get(f"{base}/pulls?state=open&per_page=100")]
        pulls = []
        for number in numbers:
            detail = self.get(f"{base}/pulls/{number}")
            if detail.get("mergeable") is None and settle_seconds:
                time.sleep(settle_seconds)  # first read asks GitHub to compute it
                detail = self.get(f"{base}/pulls/{number}")
            pulls.append(PullRequest(
                repo=repo, number=number, title=detail["title"], author=detail["user"]["login"],
                draft=bool(detail["draft"]), mergeable=detail.get("mergeable"),
                mergeable_state=detail.get("mergeable_state") or "unknown",
                additions=detail["additions"], changed_files=detail["changed_files"],
                created=date.fromisoformat(detail["created_at"][:10]),
                ci=self.ci_state(owner, repo, detail["head"]["sha"])))
        return pulls

    def ci_state(self, owner: str, repo: str, ref: str) -> str:
        runs = self.get(f"/repos/{quote(owner)}/{quote(repo)}/commits/{ref}/check-runs?per_page=100")
        conclusions = [r.get("conclusion") for r in runs.get("check_runs", [])]
        if not conclusions:
            return "none"
        if any(c in ("failure", "timed_out", "cancelled", "action_required") for c in conclusions):
            return "fail"
        if any(c is None for c in conclusions):
            return "pending"
        return "pass"

    def default_branch_health(self, owner: str, repo: str) -> dict[str, str]:
        meta = self.get(f"/repos/{quote(owner)}/{quote(repo)}")
        branch = meta["default_branch"]
        runs = self.get(f"/repos/{quote(owner)}/{quote(repo)}/actions/runs"
                        f"?branch={quote(branch)}&per_page=30")["workflow_runs"]
        latest: dict[str, str] = {}
        for run in runs:  # newest first: keep the latest conclusion per workflow
            latest.setdefault(run["name"], run.get("conclusion") or "in_progress")
        return latest
