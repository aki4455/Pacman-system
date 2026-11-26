"""
hunter.py - the Hunters. Each hunter has a search ALGORITHM and a personality (STRATEGY).

At every tile a hunter first runs one BFS from itself (a distance map). If the runner is within
the hunter's sense radius it has noticed the runner and hunts it with its own strategy;
otherwise it PATROLS: it walks to a random tile of the maze, planned with its own algorithm.

    Stalker   A*       chase      goal = the tile the runner is on (or walking into)
    Ambusher  BFS      intercept  goal = the first tile of the runner's PLANNED route that the
                                         ambusher can reach no later than the runner
                                         (read straight from its BFS distance map)
    Rusher    Greedy   chase      goal = the runner's tile, but Greedy trusts the heuristic
                                         only, so walls fool it
    Wanderer  DFS      wander     goal = the runner's tile, but it commits to each long, winding
                                         DFS route for a while before planning again

Rules for every hunter:
  * No U-turns: while planning, the tile it just left counts as a wall (unless that is the
    only way to go). This keeps the movement natural and stops back-and-forth wobbling.
  * Life cycle:  WAITING at the spawn -> active (PATROL / CHASE / ...) -> (power orb) SCARED
                 -> (eaten) RESPAWNING at the spawn -> active ...
  * While SCARED it runs away: it steps to the neighbour farthest from the runner, measured
    with a BFS distance map from the runner.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..algorithms import bfs_distances
from ..config import RESPAWN_DELAY, SCARED_SPEED_FACTOR, WANDER_COMMIT_STEPS, HunterProfile
from ..maze import Cell, Maze
from .agent import INFINITY, Agent, steps

if TYPE_CHECKING:
    from ..game import Game
    from .runner import Runner

# Life-cycle states
WAITING, CHASING, SCARED, RESPAWNING = "WAITING", "CHASING", "SCARED", "RESPAWNING"
# What an active hunter is doing (shown in the side panel)
PATROL = "PATROL"


class Hunter(Agent):
    def __init__(self, maze: Maze, profile: HunterProfile, spawn: Cell, release_delay: float,
                 rng: random.Random) -> None:
        super().__init__(maze, profile.name, profile.algorithm, profile.speed, profile.color, spawn)
        self.profile = profile
        self.strategy = profile.strategy       # "chase", "intercept" or "wander"
        self.release_delay = release_delay
        self.rng = rng
        self.state = WAITING
        self.timer = release_delay             # counts down while WAITING or RESPAWNING
        self.steps_on_plan = 0
        self.patrol_target: Cell | None = None
        self.mode, self.thought = WAITING, "waiting at the spawn"

    # ------------------------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------------------------
    @property
    def speed(self) -> float:
        return self.base_speed * (SCARED_SPEED_FACTOR if self.state == SCARED else 1.0)

    @property
    def is_dangerous(self) -> bool:
        """Touching this hunter costs the runner a life."""
        return self.state in (WAITING, CHASING)

    @property
    def is_threat(self) -> bool:
        """Dangerous now or very soon: a respawning hunter will reappear at its spawn."""
        return self.state != SCARED

    @property
    def is_scared(self) -> bool:
        return self.state == SCARED

    @property
    def is_visible(self) -> bool:
        return self.state != RESPAWNING

    @property
    def can_move(self) -> bool:
        return self.state in (CHASING, SCARED)

    def reset(self) -> None:
        """Back to the spawn at the start of a new life."""
        self.place_at(self.spawn)
        self.forget_plan()
        self.state, self.timer = WAITING, self.release_delay
        self.mode, self.thought = WAITING, "waiting at the spawn"

    def tick_timer(self, dt: float) -> None:
        if self.state in (WAITING, RESPAWNING):
            self.timer -= dt
            if self.timer <= 0:
                self.state = CHASING
                self.forget_plan()

    def frighten(self) -> None:
        """The runner ate a power orb: turn around and run."""
        if self.state == CHASING:
            self.state = SCARED
            self.turn_around()

    def calm_down(self) -> None:
        """The power orb wore off."""
        if self.state == SCARED:
            self.state = CHASING
            self.forget_plan()

    def get_eaten(self) -> None:
        self.place_at(self.spawn)
        self.forget_plan()
        self.state, self.timer = RESPAWNING, RESPAWN_DELAY
        self.mode, self.thought = RESPAWNING, "eaten - back at the spawn soon"

    # ------------------------------------------------------------------------------------
    # Decision making
    # ------------------------------------------------------------------------------------
    def choose_next_cell(self, game: Game) -> Cell | None:
        if self.state == SCARED:
            return self._flee_step(game.runner)

        my_steps = bfs_distances(self.maze, [self.cell])     # how far is every tile from me?
        runner = game.runner
        if my_steps.get(runner.cell, INFINITY) <= self.profile.sense_radius:
            mode = self.strategy.upper()                      # CHASE / INTERCEPT / WANDER
            goal, reason = self._hunting_goal(runner, my_steps)
        else:
            mode = PATROL
            goal, reason = self._patrol_goal()

        if self._needs_new_plan(mode, goal):
            self._plan_without_u_turn(goal)
            self.steps_on_plan = 0
        self.mode, self.thought = mode, reason

        if not self.plan:
            return None
        self.steps_on_plan += 1
        return self.plan.pop(0)

    def _hunting_goal(self, runner: Runner, my_steps: dict[Cell, int]) -> tuple[Cell, str]:
        if self.strategy == "intercept":
            return self._intercept_point(runner, my_steps)
        if self.strategy == "wander":
            return runner.next_cell, "following a long DFS route toward the runner"
        return runner.next_cell, "heading straight for the runner's tile"

    def _intercept_point(self, runner: Runner, my_steps: dict[Cell, int]) -> tuple[Cell, str]:
        """Where to cut the runner off.

        The runner's predicted route is the tile it is walking into followed by its plan. The
        BFS distance map tells how many steps WE need to every tile, so we pick the first route
        tile that we can reach no later than the runner does.
        """
        route = [runner.next_cell] + runner.plan
        for runner_steps, tile in enumerate(route):
            if my_steps.get(tile, INFINITY) <= runner_steps:
                return tile, f"cutting the runner off {steps(runner_steps)} ahead of it"
        return route[-1], "racing to where the runner is going"

    def _patrol_goal(self) -> tuple[Cell, str]:
        """Walk to a random tile; pick a new one when it is reached."""
        if self.patrol_target is None or self.patrol_target == self.cell:
            self.patrol_target = self.rng.choice(self.maze.open_cells)
        return self.patrol_target, "patrolling - the runner is out of range"

    def _needs_new_plan(self, mode: str, goal: Cell) -> bool:
        if not self.plan or mode != self.mode:
            return True
        if mode == PATROL:
            return goal != self.goal
        if self.strategy == "wander":
            return self.steps_on_plan >= WANDER_COMMIT_STEPS   # stubborn: keep the route a while
        return goal != self.goal

    def _plan_without_u_turn(self, goal: Cell) -> None:
        behind = frozenset()
        if self.prev_cell is not None and len(self.maze.neighbors(self.cell)) > 1:
            behind = frozenset([self.prev_cell])
        result = self.plan_route(goal, behind)
        if not result.found and behind:
            self.plan_route(goal)               # the only way is back: allow the U-turn

    def _flee_step(self, runner: Runner) -> Cell:
        """Scared: step to the neighbour farthest from the runner (random among equals)."""
        options = [tile for tile in self.maze.neighbors(self.cell) if tile != self.prev_cell]
        if not options:
            options = self.maze.neighbors(self.cell)
        runner_steps = bfs_distances(self.maze, [runner.cell])
        self.forget_plan()
        self.mode, self.thought = SCARED, "running away from the runner"
        return max(options, key=lambda tile: (runner_steps.get(tile, INFINITY), self.rng.random()))
