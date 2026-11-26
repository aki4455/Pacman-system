"""
config.py - every tunable number of the game, in one place.

Change a value (for example make the hunters faster), start the game again and watch
the difference. No other file needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Simulation --------------------------------------------------------------------------
TICKS_PER_SECOND = 60            # the game logic always advances in fixed steps of 1/60 s,
TICK = 1.0 / TICKS_PER_SECOND    # so a game plays out the same on every computer

# --- Rules -------------------------------------------------------------------------------
START_LIVES = 3
PELLET_POINTS = 10
POWER_ORB_POINTS = 50
HUNTER_POINTS = 200
TIME_LIMIT = 240.0               # seconds; a round that lasts longer ends as "time up"

# --- Timers (seconds) --------------------------------------------------------------------
POWER_DURATION = 7.0             # hunters stay scared this long after the runner eats a power orb
RESPAWN_DELAY = 3.0              # an eaten hunter comes back to its spawn after this delay
RELEASE_INTERVAL = 2.0           # hunter number i leaves its spawn i * RELEASE_INTERVAL seconds in
CAUGHT_PAUSE = 1.5               # the game freezes this long after the runner is caught

# --- Movement (tiles per second) ---------------------------------------------------------
RUNNER_SPEED = 6.0
SCARED_SPEED_FACTOR = 0.55       # scared hunters move at 55 % of their normal speed
COLLISION_DISTANCE = 0.75        # runner and hunter touch when their centres are closer than this

# --- Runner AI ---------------------------------------------------------------------------
SAFETY_MARGIN = 2                # food is safe if the runner gets there >= 2 steps before any hunter
BOXED_IN = 25                    # territory smaller than this many tiles = being boxed in -> escape
ALERT_DISTANCE = 6               # a hunter this close (in steps) makes power orbs the first priority
HUNT_REACH_FACTOR = 0.5          # chase a scared hunter only if it is reachable well before power ends

# --- Hunter AI ---------------------------------------------------------------------------
WANDER_COMMIT_STEPS = 12         # the DFS hunter follows each route this many steps before re-planning

RUNNER_COLOR = (64, 224, 255)


@dataclass(frozen=True)
class HunterProfile:
    """Who a hunter is: its search algorithm, its personality (strategy) and its looks."""

    name: str
    algorithm: str                     # "BFS", "DFS", "A*" or "Greedy"
    strategy: str                      # "chase", "intercept" or "wander" (see agents/hunter.py)
    speed: float                       # tiles per second
    sense_radius: int                  # notices the runner when it is at most this many steps away
    color: tuple[int, int, int]
    summary: str                       # one line for the menu and the side panel


# Hunters join the game in this order (the menu lets you choose how many).
HUNTERS = (
    HunterProfile("Stalker", "A*", "chase", 5.1, 12, (255, 84, 104),
                  "A* straight to the runner - optimal and focused"),
    HunterProfile("Ambusher", "BFS", "intercept", 4.9, 6, (176, 132, 255),
                  "BFS distance map - cuts off the runner's planned route"),
    HunterProfile("Rusher", "Greedy", "chase", 5.3, 6, (255, 170, 64),
                  "Greedy best-first - fast, but easily fooled by walls"),
    HunterProfile("Wanderer", "DFS", "wander", 4.6, 6, (116, 226, 132),
                  "DFS routes - long, winding patrols through the maze"),
)
