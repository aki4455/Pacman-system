"""
runner.py - the Runner: the hero, played entirely by search algorithms.

Every time the runner stands in the middle of a tile it runs this loop:

  1. SENSE    two BFS distance maps
                danger[t] = steps the CLOSEST dangerous hunter needs to reach tile t  (multi-source BFS)
                reach[t]  = steps the runner needs to reach tile t                    (BFS)
              The runner's TERRITORY is every tile it reaches strictly before all hunters:
                reach[t] < danger[t]          (the same idea as a Voronoi diagram)

  2. DECIDE   pick a mode and a goal tile, in this order of priority
                TRAPPED  no territory left                       -> step to the neighbour farthest from hunters
                HUNT     a scared hunter can be caught in time   -> goal = that hunter
                ESCAPE   the territory is small (boxed in),      -> grab a power orb in our territory if
                         or no food is safe                         possible, else run to where there is
                                                                    the most room (see _escape_goal)
                EAT      otherwise                               -> goal = the closest SAFE food:
                         (reach[t] + SAFETY_MARGIN <= danger[t])    a power orb first if a hunter is near

  3. PLAN     run the runner's algorithm (BFS / DFS / A* / Greedy) from here to the goal, with
              every tile OUTSIDE the territory treated as a wall. The old plan is kept while it
              is still good, so the runner does not change its mind on every tile.

  4. ACT      walk to the first tile of the plan.

Why a safe route always exists: if t is in the territory, every tile on a SHORTEST path to t is
in the territory too (proof in explanation.md). So BFS and A* always find a route that stays in
the territory. DFS and Greedy wander more, and the blocked tiles keep them out of danger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..algorithms import bfs_distances
from ..config import ALERT_DISTANCE, BOXED_IN, HUNT_REACH_FACTOR, RUNNER_COLOR, RUNNER_SPEED, SAFETY_MARGIN
from ..maze import Cell, Maze
from .agent import INFINITY, Agent, steps

if TYPE_CHECKING:
    from ..game import Game

EAT, HUNT, ESCAPE, TRAPPED = "EAT", "HUNT", "ESCAPE", "TRAPPED"


class Runner(Agent):
    def __init__(self, maze: Maze, algorithm: str) -> None:
        super().__init__(maze, "Runner", algorithm, RUNNER_SPEED, RUNNER_COLOR, maze.runner_start)
        self.danger: dict[Cell, int] = {}     # steps the closest dangerous hunter needs, per tile
        self.territory: set[Cell] = set()      # tiles the runner reaches before every hunter

    def choose_next_cell(self, game: Game) -> Cell | None:
        # 1. SENSE ---------------------------------------------------------------------------
        threats = []
        for hunter in game.hunters:
            if hunter.is_threat:                              # not scared (respawning counts too)
                threats += [hunter.cell, hunter.next_cell]    # where it is and where it is going
        self.danger = bfs_distances(self.maze, threats)
        reach = bfs_distances(self.maze, [self.cell])
        self.territory = {tile for tile, steps in reach.items() if steps < self.danger.get(tile, INFINITY)}

        # 2. DECIDE --------------------------------------------------------------------------
        mode, goal, reason = self._decide(game, reach)

        # 3. PLAN ----------------------------------------------------------------------------
        if mode == TRAPPED:
            self.plan, self.goal = [goal], goal               # no search, just the best single step
        elif self._needs_new_plan(mode, goal):
            self._plan_safe_route(game, mode, goal)
        self.mode, self.thought = mode, reason

        # 4. ACT -----------------------------------------------------------------------------
        return self.plan.pop(0) if self.plan else None

    # ------------------------------------------------------------------------------------
    # 2. DECIDE
    # ------------------------------------------------------------------------------------
    def _decide(self, game: Game, reach: dict[Cell, int]) -> tuple[str, Cell, str]:
        here = self.cell
        if len(self.territory) <= 1:
            return TRAPPED, self._dodge(), "TRAPPED - hunters on every side: dodge to the safest neighbour"

        # HUNT: a scared hunter we can catch before the power runs out
        prey = [hunter for hunter in game.hunters if hunter.is_scared and hunter.cell in self.territory]
        if prey:
            victim = min(prey, key=lambda hunter: reach[hunter.cell])
            if reach[victim.cell] <= game.power_time_left * self.speed * HUNT_REACH_FACTOR:
                return HUNT, victim.cell, f"HUNT - {victim.name} is scared, {steps(reach[victim.cell])} away"

        # ESCAPE: we are being boxed in (the territory is small). Once escaping, keep at it until
        # there is clearly more room again (a small "hysteresis", so the runner does not flip
        # between modes on every tile).
        boxed_in_limit = BOXED_IN + 10 if self.mode == ESCAPE else BOXED_IN
        if len(self.territory) < min(boxed_in_limit, len(self.maze.open_cells) // 4):
            return self._escape_goal(game, reach)

        # EAT: food the runner reaches at least SAFETY_MARGIN steps before any hunter
        safe_food = [tile for tile in self.territory if reach[tile] + SAFETY_MARGIN <= self.danger.get(tile, INFINITY)]
        safe_orbs = [tile for tile in safe_food if tile in game.power_orbs]
        safe_pellets = [tile for tile in safe_food if tile in game.pellets]
        nearest_hunter = self.danger.get(here, INFINITY)

        if nearest_hunter <= ALERT_DISTANCE and safe_orbs:          # a hunter is close: turn the tables
            goal = self._keep_or_closest(safe_orbs, reach)
            return EAT, goal, f"EAT - a hunter is {steps(nearest_hunter)} away: grab the power orb ({steps(reach[goal])})"
        if safe_pellets or safe_orbs:
            goal = self._keep_or_closest(safe_pellets or safe_orbs, reach)
            return EAT, goal, f"EAT - closest safe food is {steps(reach[goal])} away"

        # ESCAPE: no safe food
        return self._escape_goal(game, reach)

    def _keep_or_closest(self, candidates: list[Cell], reach: dict[Cell, int]) -> Cell:
        """Stay loyal to the current goal if it is still a candidate (no zig-zagging);
        otherwise take the closest one. Ties are broken by position, so it is repeatable."""
        if self.mode == EAT and self.goal in candidates:
            return self.goal
        return min(candidates, key=lambda tile: (reach[tile], tile))

    def _escape_goal(self, game: Game, reach: dict[Cell, int]) -> tuple[str, Cell, str]:
        """Where to run when the runner is boxed in or no food is safe.

        1. A power orb inside our territory turns the tables -> go for it.
        2. Otherwise try every possible first step. For each one, a BFS counts how many tiles
           the runner would still reach before the hunters if it went that way (its "room").
           Take the step with the most room and run to the tile in that room that is farthest
           from the hunters. A big room means many ways out; a small one is a trap.
           This is re-checked on every tile, because the hunters keep moving.
        """
        here = self.cell
        orbs = [tile for tile in self.territory if tile in game.power_orbs]
        if orbs:
            goal = min(orbs, key=lambda tile: (reach[tile], tile))
            return ESCAPE, goal, f"ESCAPE - run for the power orb ({steps(reach[goal])})"

        best_room: list[Cell] = []
        for step in self.maze.neighbors(here):
            if step not in self.territory:
                continue
            steps_from_there = bfs_distances(self.maze, [step], blocked={here})
            room = [tile for tile, steps in steps_from_there.items()
                    if steps + 1 < self.danger.get(tile, INFINITY)]
            if len(room) > len(best_room):
                best_room = room
        if not best_room:
            return TRAPPED, self._dodge(), "TRAPPED - no room left: dodge to the safest neighbour"

        if self.mode == ESCAPE and self.goal in best_room and self.goal != here:
            goal = self.goal                       # same direction as before: keep the old goal
        else:
            goal = max(best_room, key=lambda tile: (self.danger.get(tile, INFINITY), -reach[tile], tile))
        return ESCAPE, goal, f"ESCAPE - run to the roomiest area ({len(best_room)} tiles of room)"

    def _dodge(self) -> Cell:
        """No territory left: step to the neighbour the hunters need longest to reach."""
        return max(self.maze.neighbors(self.cell),
                   key=lambda tile: (self.danger.get(tile, INFINITY), len(self.maze.neighbors(tile)), tile))

    # ------------------------------------------------------------------------------------
    # 3. PLAN
    # ------------------------------------------------------------------------------------
    def _needs_new_plan(self, mode: str, goal: Cell) -> bool:
        return (not self.plan                         # finished the old plan (or never had one)
                or mode != self.mode                  # switched between EAT / HUNT / ESCAPE
                or goal != self.goal                  # want to go somewhere else
                or self.plan[0] not in self.territory)  # the next step has become dangerous

    def _plan_safe_route(self, game: Game, mode: str, goal: Cell) -> None:
        outside = {tile for tile in self.maze.open_cells if tile not in self.territory}
        avoid = set(outside)
        if mode == EAT and goal not in game.power_orbs:
            avoid |= game.power_orbs                  # keep power orbs for emergencies
        if mode == HUNT and self.prev_cell is not None:
            avoid.add(self.prev_cell)                 # no U-turns while chasing (stops wobbling)
        avoid.discard(self.cell)
        avoid.discard(goal)

        result = self.plan_route(goal, frozenset(avoid))
        if not result.found and avoid != outside:
            # the extra rules made the goal unreachable -> plan again with only the danger rule
            outside.discard(self.cell)
            self.plan_route(goal, frozenset(outside))
