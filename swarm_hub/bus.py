"""Hermes message bus: topic pub/sub plus capability routing between agents.

Topics are dotted names (``swarm.tasks.ci``). A subscription pattern may end in
``.*`` (one level) or ``.#`` (any depth). Messages nobody handles, and handlers
that raise, land in the dead-letter list instead of being lost.
"""

from __future__ import annotations

import itertools
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from .fleet import Agent, Fleet

Handler = Callable[["Message"], Any]
_ids = itertools.count(1)


@dataclass(frozen=True)
class Message:
    topic: str
    payload: dict[str, Any]
    sender: str = "hub"
    id: int = field(default_factory=lambda: next(_ids))


def topic_matches(pattern: str, topic: str) -> bool:
    p, t = pattern.split("."), topic.split(".")
    if p[-1] == "#":
        return t[:len(p) - 1] == p[:-1] and len(t) >= len(p) - 1
    if len(p) != len(t):
        return False
    return all(a == "*" or a == b for a, b in zip(p, t))


class Bus:
    def __init__(self, fleet: Fleet | None = None, history: int = 500):
        self.fleet = fleet
        self._subs: list[tuple[str, str, Handler]] = []
        self.history: deque[Message] = deque(maxlen=history)
        self.dead_letters: list[tuple[Message, str]] = []

    def subscribe(self, pattern: str, handler: Handler, subscriber: str = "anon") -> None:
        self._subs.append((pattern, subscriber, handler))

    def publish(self, message: Message) -> list[Any]:
        self.history.append(message)
        results = []
        handled = False
        for pattern, subscriber, handler in list(self._subs):
            if topic_matches(pattern, message.topic):
                handled = True
                try:
                    results.append(handler(message))
                except Exception as exc:  # isolate one broken agent from the rest
                    self.dead_letters.append((message, f"{subscriber}: {type(exc).__name__}: {exc}"))
        if not handled:
            self.dead_letters.append((message, "no subscriber"))
        return results

    def route(self, capability: str, payload: dict[str, Any], sender: str = "hub") -> list[Agent]:
        """Send a task to every agent that declares ``capability``.

        Each agent receives it on ``agent.<id>.tasks``. Returns the agents chosen,
        so callers can see who was assigned (an empty list means nobody can do it).
        """
        if self.fleet is None:
            raise RuntimeError("Routing needs a fleet")
        agents = self.fleet.with_capability(capability)
        if not agents:
            self.dead_letters.append(
                (Message(f"route.{capability}", payload, sender), "no agent has capability"))
        for agent in agents:
            self.publish(Message(f"agent.{agent.id}.tasks", {**payload, "capability": capability}, sender))
        return agents
