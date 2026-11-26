# Maze Chase AI: how everything works

This document explains every part of the project: what it does, how it does it, and why it
was built that way. Read it top to bottom once. Before the presentation, re-read
**section 13 (presentation plan)** and **section 14 (questions the professor may ask)**.

---

## Contents

1. [The project in one minute](#1-the-project-in-one-minute)
2. [Running it](#2-running-it)
3. [The big picture](#3-the-big-picture)
4. [The maze is a graph](#4-the-maze-is-a-graph-mazepy)
5. [The search algorithms](#5-the-search-algorithms-algorithms)
6. [The agents: Runner and Hunters](#6-the-agents-runner-and-hunters-agents)
7. [The game rules and the game loop](#7-the-game-rules-and-the-game-loop-gamepy)
8. [Random mazes: DFS builds mazes too](#8-random-mazes-dfs-builds-mazes-too-generatorpy)
9. [What you see on the screen](#9-what-you-see-on-the-screen-ui)
10. [Experiments and results](#10-experiments-and-results-benchmarkpy)
11. [Tests](#11-tests)
12. [Complexity summary](#12-complexity-summary)
13. [Presentation plan](#13-presentation-plan-about-10-minutes)
14. [Questions the professor may ask](#14-questions-the-professor-may-ask)
15. [Glossary](#15-glossary)

---

## 1. The project in one minute

The assignment was a "PacMan system": a hero who eats all the food in a maze while enemies
(ghosts) chase it. We built our own game in that genre, **Maze Chase AI**. It has our own
names, maps and graphics, and the same roles:

| Role in the assignment | In this project | Controlled by |
|---|---|---|
| PacMan (the hero) | **Runner** (cyan circle) | BFS, DFS, A* or Greedy, chosen in the menu or live with keys 1-4 |
| Ghosts (the enemies) | **Hunters**: Stalker, Ambusher, Rusher, Wanderer | each hunter has its own algorithm: A*, BFS, Greedy, DFS |
| Pellets / power pellets | **pellets** / **power orbs** | eating an orb scares the hunters for 7 s, so the runner can eat them |

**Nobody plays by hand.** Every agent works the same way: on every tile it **searches the
maze graph** and walks along the route it found. The four algorithms from the course are
used in three places:

1. **To move.** Every agent plans its routes with its algorithm.
2. **To sense.** The runner builds *distance maps* with multi-source BFS to know how
   dangerous each tile is. The hunters use BFS distance maps to notice and cut off the runner.
3. **To build mazes.** The random maze generator is a randomized DFS.

Everything the AI thinks is shown on screen: its planned routes, the tiles each search
explored, the danger map, and a sentence explaining every decision. The **Algorithm Lab**
screen runs all four algorithms on the same problem side by side, and two experiment
commands measure them over thousands of searches and hundreds of games.

---

## 2. Running it

* **Double-click `run.bat`** (Windows). It uses the project's `.venv` if it exists, otherwise
  `uv run`, otherwise plain `python`.
* Or in a terminal, in the project folder: `uv run main.py` (or `python main.py`).

```text
python main.py                       menu
python main.py --demo                self-running demo, all maps one after another
python main.py --play --map vortex   straight into a game on Vortex
python main.py --play --runner dfs   the runner uses DFS
python main.py --lab                 Algorithm Lab
python main.py --compare             the algorithm comparison table      (no window)
python main.py --benchmark           complete games, win rate per algorithm (no window)
python -m unittest discover -s tests -v    the 24 tests
```

Keys in the game: `Space` pause, `->` one step (exactly one more decision), `1`-`4` switch
the runner to BFS / DFS / A* / Greedy, `P` routes, `V` explored tiles, `D` danger map,
`L` labels, `+`/`-` speed, `R` replay (same seed), `S` new seed, `N` next map,
`G` random labyrinth, `A` autoplay, `M` menu, `F11` full screen.

---

## 3. The big picture

```text
                      +---------------------+
                      |  maze.py            |   the maze as a GRAPH
                      |  (adjacency list)   |   vertices = open tiles, edges = neighbours
                      +----------+----------+
                                 |  neighbors(tile)
                      +----------v----------+
                      |  algorithms/        |   BFS  DFS  A*  Greedy
                      |  same signature     |   + multi-source BFS distance maps
                      +----------+----------+
                                 |  find_path(name, maze, start, goal, blocked)
                 +---------------v---------------+
                 |  agents/                       |
                 |  runner.py   hunter.py         |   decide WHERE to go,
                 |  (both extend agent.py)        |   then search HOW to get there
                 +---------------+---------------+
                                 |  advance(dt)
                      +----------v----------+
                      |  game.py            |   rules: food, orbs, lives, collisions
                      +----+-----------+----+
                           |           |
              +------------v--+   +----v-----------+
              |  ui/ (pygame) |   |  benchmark.py  |   the same game, without a window
              +---------------+   +----------------+
```

The arrows only point downward: `maze.py` knows nothing about algorithms, and the
algorithms know nothing about the game. **The game logic never imports pygame**, so the
tests and the benchmarks run thousands of games without a window. This separation of
*model* (game.py, agents) and *view* (ui/) is why the experiments in section 10 were
possible at all.

### One decision, from start to finish

Every agent decides only when it stands in the **middle of a tile**. The runner moves 6
tiles per second, so it decides about 6 times a second:

```text
  runner reaches the middle of a tile
     |
     |-- SENSE   multi-source BFS from all hunters -> danger map      (how soon can a hunter get to each tile?)
     |           BFS from the runner               -> reach map       (how soon can I get to each tile?)
     |           territory = tiles where reach < danger
     |-- DECIDE  TRAPPED? HUNT? boxed in -> ESCAPE? safe food -> EAT? otherwise ESCAPE
     |-- PLAN    run BFS / DFS / A* / Greedy to the goal, tiles outside the territory are walls
     '-- ACT     walk toward the first tile of the route (smoothly, over the next 1/6 s)
```

The files, in reading order:

| File | Lines | What it contains |
|---|---:|---|
| `mazechase/maze.py` | ~190 | `Maze`: walls, food, spawns, the adjacency list, map file loading and validation |
| `mazechase/algorithms/*.py` | ~370 | `bfs`, `bfs_distances`, `dfs`, `astar`, `greedy_best_first`, `manhattan`, `SearchResult` |
| `mazechase/agents/agent.py` | ~140 | movement between tiles, `plan_route()` |
| `mazechase/agents/runner.py` | ~185 | the hero's AI: sense, decide, plan, act |
| `mazechase/agents/hunter.py` | ~200 | the enemies' AI: four personalities, life cycle |
| `mazechase/game.py` | ~180 | rules, scoring, collisions, lives, end of round |
| `mazechase/generator.py` | ~115 | random mazes by randomized DFS |
| `mazechase/benchmark.py` | ~150 | `--compare` and `--benchmark` |
| `mazechase/config.py` | ~70 | every tunable number in one place |
| `mazechase/ui/*.py` | ~1650 | menu, game screen, Algorithm Lab, drawing |
| `main.py` | ~140 | command-line options, starts everything |
| `tests/*.py` | ~290 | 24 unit tests |

---

## 4. The maze is a graph (`maze.py`)

A map is a text file. Everything before the `---` line is information, and the grid follows it:

```text
name: Downtown
description: A city grid full of crossings. ...
theme: teal
---
#######################
#H.........o.........H#
#.###.#####.#####.###.#
...
```

`#` wall, `.` pellet, `o` power orb, space = empty floor, `R` runner start, `H` hunter spawn.

### From grid to graph

* **Vertex** = every open tile (anything that is not `#`), written as a tuple `(row, col)`.
* **Edge** = two open tiles that touch horizontally or vertically. Every edge has weight 1
  (one step), so the graph is **undirected and unweighted**.

### Stored as an adjacency list

```python
self.adjacency: dict[Cell, list[Cell]] = {
    cell: self._find_neighbors(cell) for cell in self.open_cells
}

def neighbors(self, cell: Cell) -> list[Cell]:
    return self.adjacency[cell]          # O(1): one dictionary lookup
```

The adjacency list is built **once** when the map loads (O(V)). After that, the only
question any algorithm ever asks, "where can I go from here?", is one O(1) dictionary
lookup.

**Why an adjacency list and not an adjacency matrix?** The maze graphs are *sparse*: about
200 vertices but only about 250 edges, because every tile has at most 4 neighbours. A matrix
would need V² = 40,000 cells, almost all zero, and listing the neighbours of a tile would
cost O(V) instead of O(1). The adjacency list needs O(V + E) memory.

| Map | Size | Vertices V | Edges E | Independent cycles (E - V + 1) | Tunnels |
|---|---|---:|---:|---:|---|
| Downtown | 23 x 17 | 175 | 206 | 32 | no |
| Arena | 23 x 15 | 205 | 291 | 87 | yes |
| Twin Islands | 27 x 17 | 217 | 263 | 47 | yes |
| Vortex | 21 x 21 | 212 | 223 | 12 | yes |
| Labyrinth | 25 x 19 | 243 | 269 | 27 | yes |

*Independent cycles* (E - V + 1 for a connected graph) counts the loops in the maze. Loops
are escape routes: a tree-shaped maze (0 cycles) would be a death trap. The open Arena has
87; the ringed Vortex has only 12.

### Details worth knowing

* **Tunnels.** In `_find_neighbors` the column is computed as `(col + d_col) % width`. In a
  row whose first and last tiles are open, walking off the left edge leads to the right edge.
  To the algorithms this is just one more edge.
* **Fixed neighbour order** (UP, RIGHT, DOWN, LEFT). Every search looks at the neighbours in
  the same order, so the same search always gives the same result. Together with the seeded
  random generator (section 7) this makes every game repeatable.
* **Validation.** `Maze` refuses broken maps with a clear message (`MapError`): rows of
  different length, unknown symbols, no `R`, no `H`. To add a map, put a new `.txt` file in
  `mazechase/maps/`. It appears in the menu automatically.

---

## 5. The search algorithms (`algorithms/`)

### 5.1 One interface for all four

```python
algorithm(maze, start, goal, blocked=frozenset()) -> SearchResult
```

* `blocked` is a set of extra tiles that count as walls. The runner blocks dangerous tiles;
  the hunters block the tile behind them (no U-turns).
* `SearchResult` (`result.py`) holds:
  * `path`: the route from start to goal, both included (`[]` if there is none).
  * `expanded`: every tile the algorithm took out of its frontier, **in order**. The
    "explored" overlay and the Algorithm Lab draw exactly this list.
  * `max_frontier`: the largest size the queue / stack / heap ever reached, which measures memory.
  * `time_ms`: measured by `find_path()`.

Because all four share one signature, an agent only stores the **name** of its algorithm,
and `find_path(name, ...)` looks the function up in a dictionary:

```python
ALGORITHMS = {"BFS": bfs, "DFS": dfs, "A*": astar, "Greedy": greedy_best_first}
```

That is how keys 1-4 can switch the runner's algorithm in the middle of a game.

**Parent pointers.** None of the algorithms stores whole paths while searching. Each one
remembers, for every tile, the tile it came from (`came_from[tile] = parent`).
`reconstruct_path` walks from the goal back through the parents to the start, then reverses
the list. That costs O(path length) time and O(V) memory in total, instead of one list per
tile.

### 5.2 Breadth-First Search (`bfs.py`)

**Idea.** Explore in rings: first every tile 1 step from the start, then every tile 2 steps
away, and so on. It spreads like a wave.

**Data structure: a FIFO queue** (`collections.deque`, where `append` and `popleft` are both O(1)).

```python
def bfs(maze, start, goal, blocked=frozenset()):
    frontier = deque([start])                 # tiles discovered but not expanded yet
    came_from = {start: None}                 # parent pointers, also the "visited" set
    expanded = []
    max_frontier = 1

    while frontier:
        current = frontier.popleft()          # FIFO: the oldest tile first
        expanded.append(current)
        if current == goal:
            break
        for neighbor in maze.neighbors(current):
            if neighbor in came_from or neighbor in blocked:
                continue                      # already discovered, or forbidden
            came_from[neighbor] = current     # remember how we got here
            frontier.append(neighbor)
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult("BFS", start, goal, reconstruct_path(came_from, goal), expanded, max_frontier)
```

**Why BFS finds a shortest path (unweighted graph).** The queue always holds tiles of at most
two consecutive distances, d and d+1, with all the d's in front. So tiles leave the queue in
order of distance from the start. When a tile v is first discovered from a tile u at distance
d, v cannot be at distance less than d+1 (it would have been discovered earlier), so its
distance is exactly d+1 and the parent pointer is on a shortest path. By induction, the path
read back from the goal is a shortest path.

**Note:** a tile is marked visited when it is **discovered** (put in the queue), not when it
is expanded. That guarantees each tile enters the queue at most once.

* Complete: yes. Optimal (unweighted): yes.
* Time O(V + E): every tile is queued once and every edge looked at at most twice.
* Memory O(V).

### 5.3 Multi-source BFS: distance maps (`bfs_distances`)

The most-used function of the whole project. It does not search for one goal. It labels
**every** tile with its distance from the **nearest of several sources**:

```python
def bfs_distances(maze, sources, blocked=frozenset(), limit=None) -> dict[Cell, int]:
    distance, frontier = {}, deque()
    for source in sources:
        if source not in distance:
            distance[source] = 0               # ALL sources start at distance 0
            frontier.append(source)
    while frontier:
        current = frontier.popleft()
        if limit is not None and distance[current] >= limit:
            continue
        for neighbor in maze.neighbors(current):
            if neighbor not in distance and neighbor not in blocked:
                distance[neighbor] = distance[current] + 1
                frontier.append(neighbor)
    return distance
```

**Why it is correct.** Imagine one invisible "super source" joined to every real source by
an edge. A normal BFS from the super source reaches all real sources at distance 1, and every
other tile at 1 + (distance to the nearest source). Putting all sources in the queue at
distance 0 is exactly that BFS, minus the invisible first step. One O(V + E) pass replaces
one BFS per source.

Who uses distance maps:

| User | Sources | Used for |
|---|---|---|
| Runner | all dangerous hunters | the **danger map**: how soon any hunter can reach each tile |
| Runner | itself | the **reach map**: how soon the runner can reach each tile |
| Runner | each neighbour tile | measuring the "room" in each direction when escaping |
| Each hunter | itself | "is the runner within my sense radius?" and the Ambusher's interception point |
| Scared hunter | the runner | running away: step to the neighbour farthest from the runner |

### 5.4 Depth-First Search (`dfs.py`)

**Idea.** Always continue from the tile discovered **most recently**: go as deep as possible
down one corridor, and only when stuck, back up to the last unexplored branch.

**Data structure: a LIFO stack.** A Python list, where `append` and `pop` at the end are O(1).

```python
def dfs(maze, start, goal, blocked=frozenset()):
    frontier = [(start, None)]                 # stack of (tile, its parent)
    came_from = {}                             # filled when a tile is EXPANDED
    expanded = []
    max_frontier = 1
    while frontier:
        current, parent = frontier.pop()       # LIFO: the newest tile first -> go deep
        if current in came_from:
            continue                           # already expanded through another branch
        came_from[current] = parent
        expanded.append(current)
        if current == goal:
            break
        for neighbor in reversed(maze.neighbors(current)):
            if neighbor not in came_from and neighbor not in blocked:
                frontier.append((neighbor, current))
        max_frontier = max(max_frontier, len(frontier))
    return SearchResult("DFS", start, goal, reconstruct_path(came_from, goal), expanded, max_frontier)
```

* **Explicit stack instead of recursion.** A recursive DFS on a long corridor could hit
  Python's recursion limit (about 1000 calls). The explicit stack has no such limit and does
  exactly what the call stack would do.
* **Visited when expanded, not when discovered.** A tile can be pushed more than once (once
  per neighbour that sees it). Copies of already expanded tiles are skipped when popped
  ("lazy deletion"). This gives the same visiting order as the textbook recursive DFS. It is
  also why DFS has the largest `max_frontier` in the tables: up to O(E) entries.
* `reversed(...)` makes the first neighbour (UP) end on top of the stack, so it is explored first.

**Why the DFS path is not the shortest.** The parent of each tile is the tile from which DFS
happened to reach it first while diving. The path is therefore a path in the DFS *tree*, which
can wind through half the maze. Measured over 1000 random pairs: on average 73 steps where
14.7 would do, and the shortest path only 9 % of the time.

* Complete (finite graph): yes. Optimal: **no**.
* Time O(V + E). Memory O(V + E) (the stack with duplicates).

### 5.5 A* search (`astar.py`)

**Idea.** Give every frontier tile a score and always expand the most promising one:

```text
f(n) = g(n) + h(n)
g(n) = steps already walked from the start to n        (exact)
h(n) = estimated steps still needed from n to the goal  (the heuristic)
```

f(n) estimates the length of the whole trip start -> n -> goal, so A* first expands the tiles
that lie on promising routes, instead of spreading in every direction like BFS.

**Data structure: a priority queue**, here a binary min-heap (`heapq`). Push and pop cost
O(log n), and pop always returns the smallest f.

```python
def astar(maze, start, goal, blocked=frozenset()):
    h_start = manhattan(maze, start, goal)
    frontier = [(h_start, h_start, start)]     # heap entries (f, h, tile)
    g_cost = {start: 0}                        # cheapest known number of steps from the start
    came_from = {start: None}
    closed = set()                             # tiles already expanded (their g is final)
    expanded = []
    max_frontier = 1
    while frontier:
        _, _, current = heapq.heappop(frontier)   # the most promising tile
        if current in closed:
            continue                              # outdated duplicate entry -> skip it
        closed.add(current)
        expanded.append(current)
        if current == goal:
            break
        for neighbor in maze.neighbors(current):
            if neighbor in blocked:
                continue
            new_g = g_cost[current] + 1           # every step costs 1
            if neighbor not in g_cost or new_g < g_cost[neighbor]:
                g_cost[neighbor] = new_g
                came_from[neighbor] = current
                h = manhattan(maze, neighbor, goal)
                heapq.heappush(frontier, (new_g + h, h, neighbor))
        max_frontier = max(max_frontier, len(frontier))
    return SearchResult("A*", start, goal, reconstruct_path(came_from, goal), expanded, max_frontier)
```

Details:

* **Tie-breaking.** Tuples compare item by item. With equal f, the entry with the smaller h
  (closer to the goal) comes out first. On open maps with many equally short routes, this
  makes A* run straight at the goal instead of exploring all of them.
* **Lazy deletion.** `heapq` cannot lower the priority of an entry already in the heap.
  When we find a shorter way to a tile, we simply push a new entry. The old one is
  recognised as outdated by the `closed` check when it is popped.
* **Relation to Dijkstra and BFS.** A* with h = 0 *is* Dijkstra's algorithm. With all edge
  weights equal to 1, Dijkstra expands tiles in the same distance order as BFS. A* is
  "Dijkstra plus a sense of direction".

**Why A* is optimal here.** Our heuristic is **consistent**: for neighbours n and n',
h(n) <= 1 + h(n'). Along any path, f = g + h therefore never decreases, so A* expands tiles
in non-decreasing order of f. When a tile is expanded, its g is final, and when the goal is
expanded, g(goal) is the length of a shortest path. Consistency also implies admissibility
(see the next section). A consistent heuristic also means a tile never has to be reopened,
which is why we can simply skip closed tiles.

* Complete: yes. Optimal: yes (with an admissible heuristic).
* Time O(E log V) in the worst case (every edge can push one heap entry). Memory O(V + E).

### 5.6 The heuristic: wrap-aware Manhattan distance (`heuristics.py`)

```python
def manhattan(maze, a, b):
    d_row = abs(a[0] - b[0])
    d_col = abs(a[1] - b[1])
    if maze.has_tunnels:
        d_col = min(d_col, maze.width - d_col)   # going "around" through a tunnel may be shorter
    return d_row + d_col
```

* **Admissible: it never overestimates.** One step changes the row by at most 1 or the
  (wrap-aware) column distance by at most 1, so h drops by at most 1 per step. Since
  h(goal) = 0, adding this up along the real shortest path gives h(n) <= true distance(n).
  Walls can only make the real route longer, never shorter.
* **Consistent.** "h drops by at most 1 per step" is exactly h(n) <= 1 + h(n').
* **Why the tunnel correction matters.** Without it, h between two tiles at opposite sides
  of a tunnel row would be about 20 while the real distance is 2 steps through the tunnel.
  The heuristic would overestimate, and A* could return a path that is not the shortest.
  The test `test_manhattan_is_admissible_and_consistent` checks both properties on every
  map, for every tile.

### 5.7 Greedy best-first search (`greedy.py`)

The same as A* but with **f(n) = h(n) only**: always expand the tile that *looks* closest to
the goal, ignoring how far it has already walked. Same min-heap. A tile is visited when it
is discovered, so it is never queued twice.

* Usually the fewest tiles explored of all four.
* **Not optimal.** "Looks close" is not "is close". A wall between the tile and the goal
  lures Greedy into a corridor that leads around it. Example from the Vortex map (rings
  inside rings): the longest trip is 34 steps, and Greedy returns 38 (table in section 10).
* Complete on a finite graph: yes. Time O(E log V), memory O(V).

Comparing Greedy with A* shows what g(n) is for: the walked distance keeps A* honest.

### 5.8 The four side by side

| | BFS | DFS | A* | Greedy |
|---|---|---|---|---|
| Frontier | FIFO queue (deque) | LIFO stack (list) | min-heap on g + h | min-heap on h |
| Expands next | oldest tile | newest tile | lowest g + h | lowest h |
| Shortest path guaranteed | yes | no | yes | no |
| Uses a heuristic | no | no | yes | yes |
| Visited marked when | discovered | expanded | expanded (closed set) | discovered |
| Time | O(V + E) | O(V + E) | O(E log V) | O(E log V) |
| Tiles explored (measured avg.) | 110.6 | 108.3 | 26.8 | 21.3 |
| Path length (measured avg.) | 14.7 | 73.2 | 14.7 | 16.5 |

### 5.9 Data structures used in the project

| Data structure | Python | Where | Why |
|---|---|---|---|
| Graph (adjacency list) | `dict[Cell, list[Cell]]` | `Maze.adjacency` | O(1) neighbours, O(V + E) memory |
| Queue (FIFO) | `collections.deque` | BFS, distance maps | O(1) at both ends (a list's `pop(0)` would be O(n)) |
| Stack (LIFO) | `list` | DFS, maze generator | O(1) `append` / `pop` |
| Priority queue | `heapq` binary min-heap | A*, Greedy | O(log n) push / pop of the minimum |
| Hash map | `dict` | parent pointers, g-costs, distance maps | O(1) average lookup |
| Hash set | `set` / `frozenset` | walls, food, territory, closed set, blocked tiles | O(1) average membership test |
| Tuple | `(row, col)` | tiles | immutable, so they can be dict keys / set members |
| Ring buffer | `deque(maxlen=6)` | the event log | old entries fall out automatically |
| Records | `@dataclass` | `SearchResult`, `HunterProfile`, `Settings` | readable named fields |

---

## 6. The agents: Runner and Hunters (`agents/`)

### 6.1 Movement (`agent.py`)

Agents glide smoothly between tile centres. `cell` is the tile being left, `target` is the
tile being entered, and `progress` goes from 0 to 1. **Decisions are only taken in the middle
of a tile** (`progress == 0`). There `advance()` calls `choose_next_cell()`, which each kind
of agent implements. The AI therefore thinks in whole tiles (graph vertices) while the screen
shows smooth motion.

`plan_route(goal, blocked)` runs the agent's algorithm with `find_path`, stores the route
(`plan`), the `goal`, and the whole `SearchResult` (drawn by the overlays), and updates the
statistics shown in the side panel.

### 6.2 The Runner (`runner.py`)

At every tile the runner runs **sense, decide, plan, act**.

#### Sense: the danger map, the reach map, the territory

```python
threats = []
for hunter in game.hunters:
    if hunter.is_threat:                              # not scared (respawning counts too)
        threats += [hunter.cell, hunter.next_cell]    # where it is and where it is going
self.danger = bfs_distances(self.maze, threats)       # multi-source BFS
reach = bfs_distances(self.maze, [self.cell])
self.territory = {tile for tile, steps in reach.items() if steps < self.danger.get(tile, INFINITY)}
```

* `danger[t]`: steps the **closest** dangerous hunter needs to reach tile t.
* `reach[t]`: steps the runner needs.
* **Territory**: every tile the runner reaches strictly before every hunter. This is the
  same idea as a Voronoi diagram (each tile belongs to whoever gets there first). Press `D`
  in the game to see it: green = the runner's territory, red = the hunters' side (darker =
  a hunter is closer).

A hunter between two tiles counts at **both** ends (cautious). A respawning hunter counts
too, because it will reappear at its spawn.

#### The territory lemma (why a safe route always exists)

> **Lemma.** If the runner reaches tile t before every hunter, then it also reaches every tile
> on a shortest path to t before every hunter.

**Proof.** Let r = v0, v1, ..., vk = t be a shortest path from the runner to t, so
reach(vi) = i and reach(t) = k. `danger` is a shortest-path distance (from the nearest
hunter), so it obeys the triangle inequality: danger(t) <= danger(vi) + (k - i), because
from vi the hunter can still walk the remaining k - i steps to t. Therefore

```text
danger(vi) >= danger(t) - (k - i)  >  reach(t) - (k - i)  =  k - (k - i)  =  i  =  reach(vi)
```

so vi is in the territory. ∎

**Consequence.** If we plan with every tile *outside* the territory treated as a wall, BFS and
A* still find a route to any territory tile, and it is just as short as without the
restriction. The test `test_territory_lemma` checks this on every map during real games.
DFS and Greedy also stay inside the territory (the blocked tiles see to that), but their
routes are longer, and the lemma only promises "first" along **shortest** paths. A long
detour can arrive after a hunter. That is exactly why the DFS runner dies more (section 10).

#### Decide: which goal, in order of priority

| Mode | When | Goal |
|---|---|---|
| **TRAPPED** | the territory has at most 1 tile | no search: step to the neighbour the hunters need longest to reach |
| **HUNT** | a scared hunter is in the territory and reachable in at most half of the remaining power time (`HUNT_REACH_FACTOR = 0.5`) | that hunter's tile |
| **ESCAPE** | the territory is small (< `BOXED_IN` = 25 tiles; 35 while already escaping) | see "escape" below |
| **EAT** | there is **safe** food: reach + `SAFETY_MARGIN` (2) <= danger | the closest safe food; a **power orb first** if a hunter is within `ALERT_DISTANCE` (6) steps |
| **ESCAPE** | no food is safe | see "escape" below |

Details that make it behave well:

* **Loyalty.** While eating, the runner keeps its current target as long as it is still safe
  (`_keep_or_closest`). Without this it would zig-zag between two equally close pellets.
* **Ties** are broken by position (`min(..., key=(steps, tile))`), so decisions are repeatable.
* **Orbs are saved for emergencies.** When planning a route to a pellet, power orbs count as
  walls, so the runner does not waste an orb by walking over it.
* **Hysteresis.** Entering ESCAPE needs a territory under 25 tiles, but leaving it needs more
  than 35. With a single threshold the runner would flip between modes on every tile.

**Escape by counting room** (`_escape_goal`):

1. A power orb inside the territory turns the tables, so go for it.
2. Otherwise, for each possible first step, a BFS (with the current tile blocked) counts how
   many tiles the runner would still reach before the hunters if it went that way. That is
   its "room". Take the step with the most room and run to the tile in that room that is
   **farthest from the hunters**. Big room = many ways out; small room = a trap.
3. This is checked again on every tile, because the hunters keep moving.

#### Plan: search with the chosen algorithm

```python
outside = {tile for tile in self.maze.open_cells if tile not in self.territory}
result = self.plan_route(goal, frozenset(avoid))        # avoid = outside (+ orbs / last tile)
```

The runner **re-plans only when needed** (`_needs_new_plan`): it has no plan, the mode
changed, the goal changed, or the next step of the plan has become dangerous. Otherwise it
keeps following its route. This saves work and stops it from changing its mind on every tile.

#### Act

Return the first tile of the plan. The movement code walks there.

### 6.3 The Hunters (`hunter.py`)

All four hunters share one class. Their differences are data: a `HunterProfile` in `config.py`.

| Hunter | Algorithm | Strategy | Speed (tiles/s) | Sense radius | Leaves spawn at |
|---|---|---|---:|---:|---:|
| **Stalker** | A* | **chase**: goal = the tile the runner is walking into | 5.1 | 12 | 0 s |
| **Ambusher** | BFS | **intercept**: goal = first tile of the runner's *planned route* it can reach no later than the runner | 4.9 | 6 | 2 s |
| **Rusher** | Greedy | **chase**, but Greedy's routes are easily fooled by walls | 5.3 | 6 | 4 s |
| **Wanderer** | DFS | **wander**: chases with long DFS routes and re-plans only every 12 steps | 4.6 | 6 | 6 s |

The runner moves at 6.0 tiles/s, so every hunter is slower. Four hunters at full speed could
always corner it. Scared hunters move at 55 % of their speed.

**Life cycle (a small state machine):**

```text
   WAITING --(release time)--> CHASING --(runner eats an orb)--> SCARED --(orb wears off)--> CHASING
      ^                           ^                                 |
      |                           |                          (eaten by the runner)
 (runner caught:                  |                                 v
  everybody resets)               +-------(3 s)--------------- RESPAWNING (at its spawn)
```

**Every tile, an active hunter:**

1. Runs one BFS distance map from itself: `my_steps = bfs_distances(maze, [self.cell])`.
2. If the runner is within its **sense radius** (in real steps, not straight-line
   distance), it hunts with its strategy. Otherwise it **PATROLS**: it walks to a random tile,
   planned with its own algorithm, and picks a new one when it arrives.
3. **Interception** (Ambusher) reads the runner's predicted route (`[runner.next_cell] + runner.plan`)
   and picks the first tile where `my_steps[tile] <= runner_steps`. One BFS distance map
   answers "can I be there in time?" for every tile at once.
4. **No U-turns.** While planning, the tile it just came from counts as a wall (unless it is
   the only way). This makes the movement look natural and stops wobbling.
5. **Scared**: step to the neighbour **farthest from the runner**, measured with a BFS
   distance map from the runner (random among equals).

The hunters cooperate without talking to each other. The Stalker comes from behind while the
Ambusher cuts off the route ahead. That pincer is the most common way the runner gets caught.

---

## 7. The game rules and the game loop (`game.py`)

`Game.update(dt)` advances the game by dt seconds:

1. Count down the timers: power orb, hunters waiting or respawning.
2. Move the runner (it decides at tile centres) and eat what it reached: pellet +10, power orb +50.
3. Move the hunters.
4. Collisions: runner and hunter closer than 0.75 tiles (centre to centre, measured around
   the tunnels too). A scared hunter is eaten (+200, back to its spawn); otherwise the runner
   loses a life. Everybody resets after a short pause.
5. End of round: all food eaten = **CLEARED**, no lives left = **GAME OVER**, longer than
   4 minutes = **TIME UP**.

**Fixed time step.** The game always advances in steps of exactly 1/60 s (`TICK`), whatever
the screen does. The speed keys only change *how many* steps run per frame. A game therefore
plays out identically at 0.25x, 1x or 8x speed, on any computer.

**Repeatable games.** All randomness (the hunters' patrol targets, tie-breaks while fleeing)
comes from one `random.Random(seed)`. Same seed, same map, same algorithm: the same game,
move for move (checked by `test_the_same_seed_gives_the_same_game`). In the game, `R`
replays the same seed and `S` tries the next one.

All numbers (speeds, timers, points, AI thresholds) are in `config.py`:

| Constant | Value | Meaning |
|---|---:|---|
| `RUNNER_SPEED` | 6.0 | tiles per second |
| `START_LIVES` | 3 | |
| `POWER_DURATION` | 7.0 s | hunters stay scared |
| `RESPAWN_DELAY` | 3.0 s | an eaten hunter returns |
| `RELEASE_INTERVAL` | 2.0 s | hunter i leaves its spawn at i x 2 s |
| `TIME_LIMIT` | 240 s | |
| `SAFETY_MARGIN` | 2 | food is safe if the runner arrives 2+ steps before any hunter |
| `BOXED_IN` | 25 | territory smaller than this = escape |
| `ALERT_DISTANCE` | 6 | a hunter this close makes power orbs the priority |
| `HUNT_REACH_FACTOR` | 0.5 | chase scared hunters only if reachable in half the remaining power time |
| `WANDER_COMMIT_STEPS` | 12 | the DFS hunter keeps each route this many steps |

---

## 8. Random mazes: DFS builds mazes too (`generator.py`)

The fifth map (Labyrinth) and the menu's "Random Labyrinth" (key `G`) are generated:

1. **Carve a perfect maze with a randomized DFS** (the "recursive backtracker"), with an
   explicit stack. Stand on a tile, pick a random unvisited neighbour two tiles away, knock
   down the wall between them and push the new tile. With no unvisited neighbour left, pop
   (backtrack). A *perfect* maze is a **spanning tree** of the lattice: exactly one route
   between any two tiles.
2. **Braid it.** A tree is full of dead ends, and a dead end is a death trap in a chase game.
   For every dead end, knock down one more wall, preferably into another dead end (that
   removes two at once). Then knock down a few random walls (`extra_loops`) so that long
   corridors get side exits. Each removed wall adds one cycle (E - V + 1 goes up by one).
3. **Mirror** the left half onto the right half (looks designed, fair to both sides), then
   add a tunnel, power orbs in the corners, the runner at the bottom and the hunters at the top.

The same seed always gives the same maze: `Labyrinth` is `generate_maze(7)`. The tests check
25 seeds: connected, no dead ends, symmetric.

The same algorithm, DFS, is used both to **build** mazes and, in the game, to **solve** them.

---

## 9. What you see on the screen (`ui/`)

* **Menu** (`menu.py`): choose the map (a live preview shows its graph size), the runner's
  algorithm, the number of hunters, autoplay. Mouse or keyboard.
* **Game** (`game_screen.py`):
  * Overlays: `P` every agent's planned route and goal (dotted, in its colour); `V` the tiles
    the runner's last search expanded (lighter = earlier); `D` the danger map / territory;
    `L` name tags.
  * Side panel: the runner's algorithm, its current **mode** and **the reason for its
    decision** in plain words, its last search (tiles explored, route length, frontier peak,
    time), and its territory size. Every hunter's mode and reasoning. Recent events, and
    the decision loop with the current mode lit.
  * `Space` pauses, `->` plays exactly one more decision. This is the best way to explain a
    decision step by step.
* **Algorithm Lab** (`lab.py`): one start, one goal, four panels. Each replays the order in
  which its algorithm expanded the tiles (all at the same speed, so the slow ones are still
  searching when the fast ones are done), then draws the path. Bars compare tiles explored
  and path length. Left click = new start, right click = new goal.
* **Colour code everywhere**: A* red, BFS violet, Greedy orange, DFS green, runner cyan. A
  hunter has the colour of its algorithm.
* `board.py` draws the maze once into an image (walls with rounded corners) and only copies
  it every frame. `theme.ui_scale()` scales every size with the window, so the layout works on
  a laptop, a large monitor or a projector. `F11` switches to full screen.

---

## 10. Experiments and results (`benchmark.py`)

### 10.1 The four algorithms on the same problems (`python main.py --compare`)

For every map: 200 random (start, goal) pairs, **the same pairs for every algorithm**.
"explored" = tiles expanded, "memory" = largest frontier, "optimal" = as short as BFS's path.

| Map | Algorithm | explored | path | memory | optimal | time |
|---|---|---:|---:|---:|---:|---:|
| Downtown | BFS | 93.0 | 12.9 | 12.3 | 100 % | 110 µs |
| | DFS | 86.5 | 63.4 | 24.1 | 14 % | 135 µs |
| | A* | 15.9 | 12.9 | 9.3 | 100 % | 57 µs |
| | Greedy | 15.2 | 13.5 | 9.2 | 80 % | 41 µs |
| Arena | BFS | 110.5 | 11.6 | 18.9 | 100 % | 109 µs |
| | DFS | 115.5 | 75.2 | 64.4 | 5 % | 154 µs |
| | A* | 17.7 | 11.6 | 14.7 | 100 % | 60 µs |
| | Greedy | 14.7 | 12.5 | 13.8 | 70 % | 39 µs |
| Twin Islands | BFS | 106.4 | 13.0 | 13.7 | 100 % | 121 µs |
| | DFS | 97.6 | 76.6 | 29.2 | 10 % | 151 µs |
| | A* | 21.0 | 13.0 | 10.1 | 100 % | 78 µs |
| | Greedy | 17.5 | 14.4 | 9.4 | 70 % | 48 µs |
| Vortex | BFS | 114.5 | 19.2 | 10.5 | 100 % | 98 µs |
| | DFS | 110.6 | 66.5 | 12.3 | 10 % | 121 µs |
| | A* | 45.6 | 19.2 | 7.4 | 100 % | 116 µs |
| | Greedy | 34.6 | 23.1 | 7.3 | 60 % | 72 µs |
| Labyrinth | BFS | 128.7 | 16.9 | 14.3 | 100 % | 138 µs |
| | DFS | 131.3 | 84.2 | 24.9 | 4 % | 190 µs |
| | A* | 33.7 | 16.9 | 9.7 | 100 % | 103 µs |
| | Greedy | 24.5 | 19.1 | 8.7 | 67 % | 59 µs |
| **All maps** | **BFS** | **110.6** | **14.7** | **13.9** | **100 %** | **115 µs** |
| | **DFS** | **108.3** | **73.2** | **31.0** | **9 %** | **150 µs** |
| | **A\*** | **26.8** | **14.7** | **10.2** | **100 %** | **83 µs** |
| | **Greedy** | **21.3** | **16.5** | **9.7** | **69 %** | **52 µs** |

The longest trip on every map (runner start -> the farthest tile), as explored / path:

| Map | BFS | DFS | A* | Greedy |
|---|---|---|---|---|
| Downtown | 174 / 17 | 32 / 31 | 18 / 17 | 18 / 17 |
| Arena | 202 / 16 | 91 / 77 | 17 / 16 | 17 / 16 |
| Twin Islands | 216 / 21 | 28 / 27 | 60 / 21 | 28 / 21 |
| Vortex | 211 / 34 | 39 / 38 | 91 / 34 | 53 / 38 |
| Labyrinth | 242 / 29 | 38 / 37 | 76 / 29 | 40 / 37 |

**What it shows:**

* **A\* explores about 4x fewer tiles than BFS** (26.8 vs 110.6) and still always finds the
  shortest path. On the open Arena it explores 17.7 tiles instead of 110.5.
* **Greedy explores the fewest tiles** but finds the shortest path only 69 % of the time. On
  Vortex (rings with few gaps) the heuristic is most misleading: 60 % optimal, paths 20 %
  longer.
* **DFS explores as much as BFS but its paths are 5x longer** (73.2 vs 14.7). It also uses
  the most memory, because its stack keeps duplicate entries (lazy deletion).
* **Where the heuristic misleads, A\* pays.** On Vortex, A* explores 45.6 tiles and takes
  slightly longer than BFS (116 vs 98 µs), because each heap operation costs more than a
  deque operation. A heuristic is only as good as its estimate.
* Every search takes far less than a millisecond, so the agents can afford to think on every tile.

(Times depend on the computer; the other columns are exact and repeatable.)

### 10.2 Complete games (`python main.py --benchmark --games 20`)

20 complete games per map and runner algorithm, 4 hunters, seeds 1-20:

| Map | Runner | Cleared | Food eaten | Deaths | Hunters eaten | Avg. time | Tiles explored per search |
|---|---|---:|---:|---:|---:|---:|---:|
| Downtown | BFS | 18/20 | 100 % | 1.1 | 5.5 | 89 s | 12.7 |
| | DFS | 8/20 | 96 % | 2.4 | 3.2 | 159 s | 22.8 |
| | A* | 19/20 | 100 % | 1.0 | 5.7 | 87 s | 5.5 |
| | Greedy | 18/20 | 100 % | 1.1 | 5.5 | 87 s | 5.6 |
| Arena | BFS | 16/20 | 99 % | 1.8 | 4.5 | 102 s | 16.2 |
| | DFS | 0/20 | 66 % | 3.0 | 1.2 | 89 s | 25.8 |
| | A* | 16/20 | 99 % | 1.8 | 4.8 | 108 s | 6.3 |
| | Greedy | 18/20 | 100 % | 1.3 | 5.0 | 105 s | 6.2 |
| Twin Islands | BFS | 20/20 | 100 % | 0.5 | 6.4 | 92 s | 12.2 |
| | DFS | 4/20 | 98 % | 1.6 | 2.4 | 223 s | 26.3 |
| | A* | 20/20 | 100 % | 0.2 | 6.5 | 88 s | 5.0 |
| | Greedy | 20/20 | 100 % | 0.5 | 6.0 | 87 s | 5.0 |
| Vortex | BFS | 17/20 | 100 % | 0.9 | 4.5 | 81 s | 17.7 |
| | DFS | 17/20 | 99 % | 1.2 | 1.8 | 114 s | 32.2 |
| | A* | 16/20 | 99 % | 1.1 | 4.5 | 82 s | 8.1 |
| | Greedy | 19/20 | 99 % | 0.7 | 4.0 | 81 s | 7.8 |
| Labyrinth | BFS | 20/20 | 100 % | 0.6 | 5.9 | 93 s | 12.2 |
| | DFS | 12/20 | 99 % | 1.8 | 3.0 | 174 s | 29.0 |
| | A* | 19/20 | 100 % | 0.7 | 6.0 | 95 s | 6.0 |
| | Greedy | 20/20 | 100 % | 0.5 | 5.8 | 94 s | 5.8 |

Totals: **BFS 91/100, A\* 90/100, Greedy 95/100, DFS 41/100** maps cleared.

**How to read it:**

* **BFS, A\* and Greedy are about equally good** (90-95 %). The runner's *safety* comes from
  the territory rules, not from the path algorithm. Most of its searches are short hops to
  nearby food, where all three find the same or almost the same route. The small differences
  (91 / 90 / 95) are within the noise of 100 games.
* **But A\* and Greedy do it with 2-3x less work**: 5-8 tiles explored per decision instead
  of 12-18 for BFS.
* **DFS is clearly worse** (41 %). Its routes are long detours: (1) it eats slowly, so it
  often runs out of time (Twin Islands: 223 s on average, close to the 240 s limit);
  (2) the territory guarantee holds only along *shortest* paths, so a long detour reaches
  tiles later than planned and walks into hunters (2.0 deaths per game on average, against
  about 1.0 for the others). On the open Arena it never clears the map.
* This is the most important lesson of the experiment: **an optimal path matters when time
  matters.**

### 10.3 How the game was balanced

Balancing used the same headless simulation, on all CPU cores (`ProcessPoolExecutor`):
hundreds of complete games per setting, about a thousand games in half a minute. What we found
and changed:

* At first the hunters were almost as fast as the runner (5.0-5.8 against 6.0 tiles per
  second), and on the old open Arena the runner lost every game, whatever we tuned. We made
  the hunters slower and gave them a **sense radius**: far away they patrol, nearby they hunt.
* We traced every lost game tile by tile. That led to the territory idea, the "room" rule for
  escaping, the "boxed in" rule and the hysteresis.
* The Arena was redesigned (hunters start in the corners, a tunnel through the middle row).
  Together, these changes took the Arena from 0 % to 80-90 % cleared.

---

## 11. Tests

`python -m unittest discover -s tests -v` runs 24 tests in about 6 seconds, without a window.

| Test file | What is checked |
|---|---|
| `test_algorithms.py` | the graph: vertex and edge counts, symmetric neighbours, tunnels; every map valid and connected; broken maps rejected |
| | every algorithm returns a valid path (starts at the start, ends at the goal, only single steps, avoids blocked tiles); start = goal; unreachable goal gives an empty path |
| | on 60 random pairs per map: **A\* is as short as BFS**, DFS and Greedy never shorter; A* explores fewer tiles than BFS |
| | multi-source BFS = minimum of single-source BFS; `limit` works; **the heuristic is admissible and consistent on every tile of every map** |
| `test_game.py` | generator: same seed same maze, connected, no dead ends, mirrored |
| | same seed gives the same game; score and lives add up; every algorithm can drive the runner; every game ends |
| | **the territory lemma** holds during real games on every map; the runner always has a mode and an explanation |

---

## 12. Complexity summary

V = vertices (open tiles, about 175-245), E = edges (about 205-290).

| Operation | Time | Memory |
|---|---|---|
| Build the graph (load a map) | O(V) (at most 4 neighbours per tile) | O(V + E) |
| `neighbors(tile)` | O(1) | |
| BFS, multi-source BFS | O(V + E) | O(V) |
| DFS | O(V + E) | O(V + E) (stack with duplicates) |
| A*, Greedy | O(E log V) | O(V + E) (heap entries) |
| Reconstruct a path | O(path length) | O(path length) |
| One runner decision | at most 8 passes of O(V + E): danger + reach + up to 4 "room" BFS + 1-2 searches | O(V) |
| One hunter decision | 1 BFS distance map + at most 2 searches | O(V) |

With about 200 tiles, a whole runner decision touches a few thousand tiles and takes well
under a millisecond.

---

## 13. Presentation plan (about 10 minutes)

**Before you start:** open the menu with `run.bat`, press `F11` for full screen. Select
Downtown, runner A*, 4 hunters.

1. **The idea (1 min).** "A maze chase where both sides are AI. The maze is a graph, and
   every move is the result of a graph search: BFS, DFS, A* and Greedy, the algorithms
   from our course." Point at the menu: the map preview shows the graph size (V, E); the
   four hunter cards show each enemy's algorithm.
2. **Watch it play (2 min).** `Enter`. Let it run. Point at the side panel: the runner's
   **mode** and **the reason for its decision** in words, and its last search (tiles
   explored). The dotted lines (`P`) are the routes each agent planned.
3. **Explain one decision (2 min).** `Space` to pause, `D` for the danger map: "Green
   tiles are the ones the runner reaches before any hunter. That is computed with two BFS
   distance maps, one of them a multi-source BFS from all hunters at once." Then `->`
   a few times: one decision per press. Show that the route never leaves the green area,
   and explain the lemma in one sentence.
4. **Switch algorithms live (1 min).** `2` (DFS): the routes start winding through the
   maze. `V` shows how many tiles each search explores. `3` back to A*.
5. **Algorithm Lab (2 min).** `M`, select Labyrinth, `L`. "Same start, same goal, four
   algorithms." Let the replay run: BFS spreads in rings (242 tiles), A* goes almost
   straight (76 tiles) and both find 29 steps. DFS and Greedy finish fast but their paths are
   8 steps longer. Right-click a new goal to repeat it live. Optional: `N` to Vortex, where
   Greedy is fooled by the rings.
6. **The numbers (1 min).** Show the tables in section 10 (or run
   `python main.py --benchmark --games 3` live, which takes a few seconds). "A* explores 4x
   fewer tiles than BFS for the same shortest path. A DFS runner clears only 41 % of the
   maps, against 90 %+ for the others, because long routes waste time and walk into danger."
7. **Code tour (1 min).** `maze.py` (adjacency list), `bfs.py`, `astar.py`: short and
   commented, with the same interface for all four.

If something goes wrong: `R` restarts the round, `M` goes back to the menu.
`python main.py --demo` runs everything by itself.

---

## 14. Questions the professor may ask

**Why does BFS find the shortest path?**
It expands tiles in order of distance: first all tiles 1 step away, then 2, and so on. The
queue never holds more than two consecutive distances. So the first time a tile is reached,
it is reached by a shortest route, and the parent pointers record that route. This holds
because every step costs the same (1).

**What would change if steps had different costs (for example mud tiles)?**
BFS would no longer be optimal. We would use Dijkstra's algorithm (a priority queue on g),
or A* with the heuristic scaled to the cheapest step cost.

**What is the difference between A\* and Dijkstra?**
Dijkstra orders the frontier by g (distance so far). A* orders it by g + h. A* with h = 0 is
Dijkstra, and with all weights equal to 1, Dijkstra explores in the same order as BFS. The
heuristic makes A* expand tiles in the direction of the goal first.

**Why is A\* optimal? What do admissible and consistent mean?**
Admissible: h never overestimates the real remaining distance. Consistent:
h(n) <= cost(n, n') + h(n') for every neighbour. With a consistent heuristic, f never
decreases along a path, so when A* expands a tile its g is final, and the first time it
expands the goal it has a shortest path. Manhattan distance is consistent on a grid, because
one step changes it by at most 1.

**Why do you take the minimum for the columns in the heuristic?**
Because of the tunnels. Going around through the side of the map can be shorter than going
straight across. Without the minimum, the heuristic could overestimate, and A* could miss the
shortest path. A unit test checks admissibility on every tile.

**Why is DFS so bad at paths? Why use it at all?**
DFS returns the first route it happens to dive down, not the shortest. It is still complete,
and its natural use is exploring and **building** mazes. Our generator is a randomized DFS.
In the game, the Wanderer uses it on purpose: its long, winding routes make it unpredictable.

**Why does your DFS use more memory than BFS in the table?**
Our DFS marks a tile visited when it is taken off the stack. A tile can therefore be on the
stack several times (once per neighbour that saw it), and the copies are skipped later. This
gives exactly the order of the recursive DFS. The stack can grow to O(E) entries. In these
narrow mazes the BFS "wave" stays small, so the BFS queue is short.

**Why didn't you use recursion for DFS?**
Python stops at about 1000 nested calls, and a long corridor could exceed that. An explicit
stack does the same thing without the limit.

**Why an adjacency list instead of a matrix?**
The graph is sparse: about 200 vertices but only about 250 edges (at most 4 per tile). A
matrix would need 40,000 entries, mostly zero, and listing a tile's neighbours would cost O(V).
The adjacency list needs O(V + E) memory and gives the neighbours in O(1).

**What is multi-source BFS and why is it correct?**
All sources start in the queue at distance 0. It is the same as a normal BFS from one
imaginary vertex connected to every source, minus that first step. Every tile gets the
distance to its *nearest* source in one O(V + E) pass, instead of one BFS per hunter.

**How does the runner avoid the hunters?**
It computes its territory: the tiles it reaches before every hunter (reach < danger, both BFS
distance maps). It only plans routes through its territory, treating every other tile as a
wall. We proved that every tile on a shortest path to a territory tile is also in the
territory (section 6.2), so a safe shortest route always exists while there is territory.
When the territory shrinks, it escapes toward the direction with the most room.

**Is the game random? Can you repeat a game?**
It is fully repeatable. The simulation runs in fixed 1/60-second steps, the neighbour order
is fixed, ties are broken by position, and the only randomness (hunter patrols) comes from a
seeded generator. Same seed = same game; there is a test for it. `R` replays a round.

**Why are the hunters slower than the runner? Isn't that cheating?**
It is game balance. Four coordinated hunters almost as fast as the runner corner it in an
open maze. We measured this: with hunters at 5.0-5.8 tiles per second against the runner's 6.0,
the runner lost every game on the old Arena. We tuned speeds, sense radius and maps with
hundreds of simulated games.

**Do the hunters cooperate?**
Not explicitly, but their strategies complement each other. The Stalker chases from
behind, while the Ambusher uses a BFS distance map to reach the runner's *planned* route
before the runner does. Together they form a pincer.

**Why does the Greedy runner win as often as the A\* runner (even slightly more)?**
The runner's searches are mostly short hops to nearby, safe food. Over such short distances
Greedy usually finds the same route as A*, with even fewer tiles explored. Safety comes from
the territory rules, not from the path algorithm. The difference (95 vs 90 of 100 games) is
within statistical noise. On long trips, Greedy's paths are clearly worse (section 10.1).

**Why does the DFS runner lose so often?**
Two reasons. Its long detours make it slow to eat (time runs out). And the territory
guarantee only holds along shortest paths: a detour reaches tiles later than the danger map
assumed, which walks it into hunters.

**What is the complexity of one decision?**
Each is O(V + E) or O(E log V) with a small constant: the runner runs at most 8 graph passes
per decision, a hunter 1-3. With about 200 tiles that is a few thousand operations, well under
a millisecond.

**How would you improve the AI?**
Look ahead several moves with minimax / expectimax (the hunters' possible replies). Give
tiles a danger *cost* instead of a yes/no and use Dijkstra or A* with weights. Let the hunters
coordinate explicitly (assign each one a different exit). Learn the parameters instead of
tuning them by hand.

---

## 15. Glossary

| Term | Meaning |
|---|---|
| Vertex / node | an open tile `(row, col)` |
| Edge | two neighbouring open tiles; weight 1 |
| Adjacency list | for every vertex, the list of its neighbours |
| Frontier | the tiles discovered but not yet expanded (queue, stack or heap) |
| Expand / explore | take a tile out of the frontier and look at its neighbours |
| Visited set | tiles already seen, so they are not processed twice (`came_from` keys, `closed`) |
| Parent pointer | `came_from[tile]`: the tile we came from; used to rebuild the path |
| Heuristic h(n) | an estimate of the remaining distance to the goal |
| Admissible | the heuristic never overestimates |
| Consistent | h(n) <= cost(n, n') + h(n'); implies admissible |
| Complete | always finds a path if one exists |
| Optimal | always finds a shortest path |
| Distance map | a dictionary {tile: steps from the nearest source}, built by (multi-source) BFS |
| Territory | tiles the runner reaches strictly before every hunter |
| Lazy deletion | leave outdated entries in the heap / stack and skip them when they come out |
| Seed | the start value of the random number generator; the same seed gives the same game |
| Tick | one fixed simulation step of 1/60 s |
