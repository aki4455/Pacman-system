# Maze Chase AI

A self-playing maze chase game for the **Data Structures 2** course. Nobody plays by hand:
the hero (the **Runner**) and the enemies (the **Hunters**) choose every move by running
graph-search algorithms on the maze: **BFS, DFS, A\*** and **Greedy best-first search**.

> The full explanation of every part (algorithms, proofs, data structures, AI, results,
> presentation plan, likely questions) is in **[explanation.md](explanation.md)**.

## Start it

| How | What happens |
|---|---|
| Double-click **`run.bat`** | opens the menu (Windows) |
| `uv run main.py` | the same, with uv |
| `python main.py` | the same, with plain Python (needs `pip install pygame`) |

Useful options (they also work after `run.bat`, e.g. `run.bat --demo`):

```text
python main.py --demo                 self-running demo: plays every map one after another
python main.py --play --map arena     straight into a game (map by number, name or "random")
python main.py --play --runner bfs    choose the runner's algorithm: bfs, dfs, astar, greedy
python main.py --lab                  the Algorithm Lab: BFS, DFS, A*, Greedy side by side
python main.py --compare              algorithm comparison on every map      (no window)
python main.py --benchmark            hundreds of complete games, win rates   (no window)
python main.py --help                 every option
```

Requirements: Python 3.10 or newer and `pygame` (`uv sync` installs it). The experiments
(`--compare`, `--benchmark`) and the tests need nothing but Python.

## Keys

| Game | | Algorithm Lab | |
|---|---|---|---|
| `Space` | pause / continue | `Space` | play / pause the replay |
| `->` | one step (one decision) | `<-` `->` | one tile back / forward |
| `1` `2` `3` `4` | runner uses BFS / DFS / A* / Greedy | `Enter` | show the final result |
| `P` | planned routes | left / right click | new start / new goal |
| `V` | tiles explored by the last search | `C` / `F` / `X` | random / farthest / swapped pair |
| `D` | danger map (runner's territory) | `+` `-` | replay speed |
| `L` | name tags | `N` / `G` | next map / random labyrinth |
| `+` `-` | game speed | `M` | back to the menu |
| `R` / `S` | replay same seed / new seed | | |
| `N` / `G` | next map / random labyrinth | | |
| `A` | autoplay (next map after each round) | | |
| `M` / `Esc` | menu | `F11` | full screen (everywhere) |

## Project layout

```text
main.py                  start here: command-line options, opens the window
run.bat                  double-click launcher for Windows
mazechase/
    maze.py              the maze as a GRAPH (adjacency list), map loading
    algorithms/          bfs.py, dfs.py, astar.py, greedy.py, heuristics.py, result.py
    agents/              agent.py (movement), runner.py (hero AI), hunter.py (enemy AI)
    game.py              the rules: food, power orbs, lives, collisions, scoring
    generator.py         random mazes, carved by a randomized DFS
    benchmark.py         --compare and --benchmark (no window)
    config.py            every tunable number in one place
    maps/*.txt           the five maps (plain text, easy to edit)
    ui/                  pygame screens: menu, game, Algorithm Lab, drawing helpers
tests/                   24 unit tests:  python -m unittest discover -s tests -v
explanation.md           how everything works, for the presentation
```

## Measured results (from `--compare` and `--benchmark --games 20`)

| Algorithm | tiles explored per search | path length | shortest path found | runner clears the map |
|---|---:|---:|---:|---:|
| BFS | 110.6 | 14.7 | 100 % | 91 % |
| DFS | 108.3 | 73.2 | 9 % | 41 % |
| A* | **26.8** | 14.7 | 100 % | 90 % |
| Greedy | **21.3** | 16.5 | 69 % | **95 %** |

The first three columns are averages over 1000 random (start, goal) pairs (200 per map). The
last column is over 100 complete games per algorithm against 4 hunters (20 per map).
