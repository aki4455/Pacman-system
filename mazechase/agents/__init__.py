"""The two kinds of AI agents: the Runner (the hero) and the Hunters (the enemies)."""

from .agent import Agent
from .hunter import CHASING, RESPAWNING, SCARED, WAITING, Hunter
from .runner import EAT, ESCAPE, HUNT, TRAPPED, Runner

__all__ = ["Agent", "Hunter", "Runner", "CHASING", "RESPAWNING", "SCARED", "WAITING",
           "EAT", "ESCAPE", "HUNT", "TRAPPED"]
