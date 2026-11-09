"""Registry of every repository agent in the swarm."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FLEET = Path(__file__).with_name("fleet.json")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")


@dataclass(frozen=True)
class Agent:
    id: str
    repo: str
    role: str
    capabilities: frozenset[str]
    owner: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


class Fleet:
    def __init__(self, owner: str, agents: list[Agent]):
        self.owner = owner
        self._agents: dict[str, Agent] = {}
        for agent in agents:
            if agent.id in self._agents:
                raise ValueError(f"Duplicate agent id: {agent.id}")
            self._agents[agent.id] = agent

    def __iter__(self):
        return iter(self._agents.values())

    def __len__(self) -> int:
        return len(self._agents)

    def get(self, agent_id: str) -> Agent:
        try:
            return self._agents[agent_id]
        except KeyError:
            raise KeyError(f"Unknown agent: {agent_id}") from None

    def by_repo(self, repo: str) -> Agent | None:
        repo = repo.split("/")[-1].casefold()
        return next((a for a in self if a.repo.casefold() == repo), None)

    def with_capability(self, capability: str) -> list[Agent]:
        return [a for a in self if capability in a.capabilities]


def load_fleet(path: str | Path = DEFAULT_FLEET) -> Fleet:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    owner = data["owner"]
    agents = []
    for entry in data["repositories"]:
        if not _ID.fullmatch(entry["id"]):
            raise ValueError(f"Invalid agent id: {entry['id']!r}")
        agents.append(Agent(entry["id"], entry["repo"], entry["role"],
                            frozenset(entry.get("capabilities", [])), owner))
    return Fleet(owner, agents)
