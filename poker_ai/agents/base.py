from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    """Minimal interface used by the tournament runner.

    Every agent receives an OpenSpiel state and returns one legal action id.
    Keeping this interface tiny makes Week 3 CFR integration much easier.
    """

    name: str = "agent"

    @abstractmethod
    def act(self, state: Any) -> int:
        raise NotImplementedError
