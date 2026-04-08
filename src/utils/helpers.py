"""
Utility helpers for AI Autonomous Systems.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List


def truncate(text: str, max_length: int = 500, suffix: str = "…") -> str:
    """Truncate *text* to *max_length* characters, appending *suffix* if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def slugify(text: str) -> str:
    """Convert *text* to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def utc_now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def sha256(text: str) -> str:
    """Return the SHA-256 hex digest of *text*."""
    return hashlib.sha256(text.encode()).hexdigest()


def flatten_findings(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten nested findings from an orchestrator report into a single list."""
    findings = []
    for result in results:
        for finding in result.get("findings", []):
            findings.append(
                {
                    **finding,
                    "agent": result.get("agent"),
                    "repository": result.get("repository"),
                }
            )
    return findings


def group_by(items: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    """Group a list of dicts by the value of *key*."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        k = str(item.get(key, "unknown"))
        groups.setdefault(k, []).append(item)
    return groups
