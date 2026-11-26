"""
game.py - the rules of the game. There is no drawing code here, so a game can also run
without a window (the tests and the benchmarks do exactly that).

One call to update(dt) advances the game by dt seconds:

    1. count down timers (power orb, hunters waiting at their spawn / respawning)
    2. move the runner      - it decides at every tile with its search algorithm
    3. eat what it reached  - pellet +10, power orb +50 (hunters get scared)
    4. move the hunters     - each decides at every tile with its own algorithm
    5. collisions           - scared hunter: eaten (+200); otherwise the runner loses a life
    6. end of round?        - all food eaten (CLEARED), no lives left (GAME OVER), too slow (TIME UP)
"""

from __future__ import annotations

import math
import random
from collections import deque

from .agents import Hunter, Runner
from .config import (CAUGHT_PAUSE, COLLISION_DISTANCE, HUNTER_POINTS, HUNTERS, PELLET_POINTS,
                     POWER_DURATION, POWER_ORB_POINTS, RELEASE_INTERVAL, START_LIVES, TIME_LIMIT)
from .maze import Cell, Maze

PLAYING, CAUGHT, CLEARED, GAME_OVER, TIME_UP = "PLAYING", "CAUGHT", "CLEARED", "GAME OVER", "TIME UP"
FINISHED = (CLEARED, GAME_OVER, TIME_UP)


class Game:
    def __init__(self, maze: Maze, runner_algorithm: str = "A*", hunter_count: int = 4, seed: int = 0) -> None:
        self.maze = maze
        self.rng = random.Random(seed)            # all randomness comes from here -> repeatable
        self.pellets: set[Cell] = set(maze.pellets)
        self.power_orbs: set[Cell] = set(maze.power_orbs)
        self.food_total = len(self.pellets) + len(self.power_orbs)

        self.score = 0
        self.lives = START_LIVES
        self.time = 0.0
        self.status = PLAYING
        self.pause_left = 0.0                     # freeze timer after the runner is caught
        self.power_time_left = 0.0                # > 0 while the hunters are scared
        self.hunters_eaten = 0
        self.deaths = 0
        self.log: deque[str] = deque(maxlen=6)    # recent events for the side panel
        self.last_message = ""

        self.runner = Runner(maze, runner_algorithm)
        self.hunters: list[Hunter] = []
        for index in range(hunter_count):
            profile = HUNTERS[index % len(HUNTERS)]
            spawn = maze.hunter_spawns[index % len(maze.hunter_spawns)]
            self.hunters.append(Hunter(maze, profile, spawn, index * RELEASE_INTERVAL, self.rng))
        self._say(f"Round started on {maze.name}")

    # ------------------------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------------------------
    @property
    def food_left(self) -> int:
        return len(self.pellets) + len(self.power_orbs)

    @property
    def is_over(self) -> bool:
        return self.status in FINISHED

    def agents(self) -> list:
        return [self.runner, *self.hunters]

    # ------------------------------------------------------------------------------------
    # The game loop step
    # ------------------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.status == CAUGHT:
            self.pause_left -= dt
            if self.pause_left <= 0:
                self._start_new_life()
            return
        if self.status != PLAYING:
            return

        self.time += dt
        self._tick_power(dt)
        for hunter in self.hunters:
            hunter.tick_timer(dt)

        for tile in self.runner.advance(dt, self):
            self._eat(tile)
        for hunter in self.hunters:
            if hunter.can_move:
                hunter.advance(dt, self)

        self._check_collisions()
        if self.status == PLAYING:
            if self.food_left == 0:
                self._finish(CLEARED, "Map cleared - every pellet eaten!")
            elif self.time >= TIME_LIMIT:
                self._finish(TIME_UP, "Time is up")

    def set_runner_algorithm(self, algorithm: str) -> None:
        """Switch the runner's algorithm in the middle of the game (keys 1-4)."""
        self.runner.algorithm = algorithm
        self.runner.forget_plan()
        self._say(f"Runner now uses {algorithm}")

    # ------------------------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------------------------
    def _eat(self, tile: Cell) -> None:
        if tile in self.pellets:
            self.pellets.remove(tile)
            self.score += PELLET_POINTS
        elif tile in self.power_orbs:
            self.power_orbs.remove(tile)
            self.score += POWER_ORB_POINTS
            self.power_time_left = POWER_DURATION
            for hunter in self.hunters:
                hunter.frighten()
            self._say("Power orb! The hunters are scared")

    def _tick_power(self, dt: float) -> None:
        if self.power_time_left > 0:
            self.power_time_left = max(0.0, self.power_time_left - dt)
            if self.power_time_left == 0:
                for hunter in self.hunters:
                    hunter.calm_down()

    def _check_collisions(self) -> None:
        for hunter in self.hunters:
            if not hunter.is_visible:
                continue
            if self._distance(self.runner.position, hunter.position) >= COLLISION_DISTANCE:
                continue
            if hunter.is_scared:
                hunter.get_eaten()
                self.score += HUNTER_POINTS
                self.hunters_eaten += 1
                self._say(f"Runner ate the {hunter.name} (+{HUNTER_POINTS})")
            else:
                self._runner_caught(hunter)
                return

    def _runner_caught(self, hunter: Hunter) -> None:
        self.lives -= 1
        self.deaths += 1
        if self.lives <= 0:
            self._finish(GAME_OVER, f"The {hunter.name} ({hunter.algorithm}) caught the runner - game over")
        else:
            self.status = CAUGHT
            self.pause_left = CAUGHT_PAUSE
            self._say(f"The {hunter.name} ({hunter.algorithm}) caught the runner!")

    def _start_new_life(self) -> None:
        self.status = PLAYING
        self.power_time_left = 0.0
        self.runner.place_at(self.maze.runner_start)
        self.runner.forget_plan()
        for hunter in self.hunters:
            hunter.reset()

    def _finish(self, status: str, message: str) -> None:
        self.status = status
        self._say(message)

    def _distance(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        d_row = abs(a[0] - b[0])
        d_col = abs(a[1] - b[1])
        if self.maze.has_tunnels:
            d_col = min(d_col, self.maze.width - d_col)     # closer "around" through a tunnel?
        return math.hypot(d_row, d_col)

    def _say(self, message: str) -> None:
        self.last_message = message
        self.log.appendleft(f"{self.time:5.1f}s  {message}")
