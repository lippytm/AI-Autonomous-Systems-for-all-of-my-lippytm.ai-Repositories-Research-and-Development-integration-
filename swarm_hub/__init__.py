"""Swarm Hub: the working coordination layer for the lippytm AI Jarvis fleet.

Standard library only. Everything here is report-only: it reads, classifies,
routes and teaches, but never pushes, merges or changes a repository.
"""

from .bus import Bus, Message
from .fleet import Agent, Fleet, load_fleet
from .playbook import Diagnosis, Pattern, Playbook, load_playbook
from .triage import PullRequest, Verdict, triage

__all__ = [
    "Agent", "Bus", "Diagnosis", "Fleet", "Message", "Pattern", "Playbook",
    "PullRequest", "Verdict", "load_fleet", "load_playbook", "triage",
]
__version__ = "0.1.0"
