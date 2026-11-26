"""
agent.py - what the Runner and the Hunters have in common.

MOVEMENT  Agents glide smoothly from tile to tile. `cell` is the tile being left, `target` the
          tile being entered, and `progress` (0 -> 1) says how far along the agent is.
          Decisions are only taken in the MIDDLE of a tile (progress == 0), so the AI can think
          in whole tiles while the screen still shows smooth motion.

PLANNING  plan_route() runs the agent's search algorithm and stores the route (`plan`), its
          `goal`, and the full SearchResult (used by the overlays and the side panel).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..algorithms import SearchResult, find_path
from ..maze import Cell, Direction, Maze

if TYPE_CHECKING:
    from ..game import Game

INFINITY = float("inf")


def steps(count: int) -> str:
    """'1 step', '2 steps' - for the explanations shown in the side panel."""
    return f"{count} step" if count == 1 else f"{count} steps"


class Agent:
    def __init__(self, maze: Maze, name: str, algorithm: str, speed: float,
                 color: tuple[int, int, int], spawn: Cell) -> None:
        self.maze = maze
        self.name = name
        self.algorithm = algorithm          # "BFS", "DFS", "A*" or "Greedy"
        self.base_speed = speed             # tiles per second
        self.color = color
        self.spawn = spawn

        # What the AI is doing right now (shown in the side panel and the overlays)
        self.mode = ""
        self.thought = ""                   # one sentence explaining the last decision
        self.goal: Cell | None = None       # where the current plan leads
        self.plan: list[Cell] = []          # tiles still to walk, next tile first
        self.last_search: SearchResult | None = None

        # Statistics
        self.searches = 0
        self.nodes_expanded = 0
        self.search_ms = 0.0

        self.place_at(spawn)

    # ------------------------------------------------------------------------------------
    # Decision making - every kind of agent implements this
    # ------------------------------------------------------------------------------------
    def choose_next_cell(self, game: Game) -> Cell | None:
        """Called in the middle of a tile: return the neighbouring tile to walk to (or None)."""
        raise NotImplementedError

    # ------------------------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------------------------
    def place_at(self, cell: Cell) -> None:
        self.cell = cell
        self.target = cell
        self.prev_cell: Cell | None = None
        self.progress = 0.0
        self.direction: Direction = (0, 0)

    @property
    def speed(self) -> float:
        return self.base_speed

    @property
    def is_moving(self) -> bool:
        return self.target != self.cell

    @property
    def next_cell(self) -> Cell:
        """The tile the agent is walking into (or standing on)."""
        return self.target

    @property
    def position(self) -> tuple[float, float]:
        """Exact (row, col) position as decimals - in between two tiles while moving."""
        return (self.cell[0] + self.direction[0] * self.progress,
                self.cell[1] + self.direction[1] * self.progress)

    def advance(self, dt: float, game: Game) -> list[Cell]:
        """Walk for `dt` seconds. Returns the tiles the agent arrived at (usually none or one)."""
        arrived: list[Cell] = []
        distance = self.speed * dt                        # tiles to travel during this update
        while distance > 1e-9:
            if not self.is_moving:                        # in the middle of a tile: think!
                next_cell = self.choose_next_cell(game)
                if next_cell is None or next_cell == self.cell:
                    break                                 # nothing to do -> stand still
                self.target = next_cell
                self.direction = self.maze.direction(self.cell, next_cell)
            step = min(distance, 1.0 - self.progress)
            self.progress += step
            distance -= step
            if self.progress >= 1.0 - 1e-9:               # reached the middle of the next tile
                self.prev_cell, self.cell = self.cell, self.target
                self.progress = 0.0
                arrived.append(self.cell)
        return arrived

    def turn_around(self) -> None:
        """Reverse immediately, even halfway between two tiles (used when hunters get scared)."""
        if self.is_moving:
            self.cell, self.target = self.target, self.cell
            self.progress = 1.0 - self.progress
            self.direction = (-self.direction[0], -self.direction[1])
            self.prev_cell = None
        self.forget_plan()

    # ------------------------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------------------------
    def plan_route(self, goal: Cell, blocked: frozenset[Cell] = frozenset()) -> SearchResult:
        """Run this agent's search algorithm from where it stands to `goal` and keep the route."""
        result = find_path(self.algorithm, self.maze, self.cell, goal, blocked)
        self.last_search = result
        self.searches += 1
        self.nodes_expanded += len(result.expanded)
        self.search_ms += result.time_ms
        self.goal = goal
        self.plan = result.path[1:]          # the first tile of the path is where we stand
        return result

    def forget_plan(self) -> None:
        self.plan = []
        self.goal = None
