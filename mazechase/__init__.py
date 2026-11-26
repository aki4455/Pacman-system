"""
Maze Chase AI - a self-playing maze chase game driven by search algorithms.

Package layout (read it in this order):

    config.py        every tunable number (speeds, timers, AI thresholds)
    maze.py          the board as a GRAPH (adjacency list)
    algorithms/      BFS, DFS, A*, Greedy best-first  (the Data Structures part)
    agents/          the Runner and the Hunters: they USE the algorithms to make decisions
    game.py          the rules: eating, scoring, lives, power orbs, collisions
    generator.py     random mazes, built with a randomized DFS
    ui/              everything you see on the screen (pygame)
    benchmark.py     experiments without a window (algorithm comparison, win rates)
"""

__version__ = "1.0.0"
