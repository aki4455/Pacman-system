"""
maze.py - the game board, seen as a GRAPH.

    vertex (node) = an open tile (anything that is not a wall), written as a (row, col) tuple
    edge          = two open tiles that touch horizontally or vertically

The graph is stored as an ADJACENCY LIST: a dictionary that maps every vertex to the list of
its neighbours. It is built once when the map is loaded (O(V) time) and afterwards the question
"which tiles can I step to from here?" is a single O(1) dictionary lookup - the only question
BFS, DFS, A* and Greedy ever ask about the maze.

A Maze describes a map exactly as it was designed and never changes during a game. Things that
do change (eaten pellets, positions, score) live in game.py.

Map files (mazechase/maps/*.txt) start with a few "key: value" lines, then a line "---",
then the grid:

    name: Tiny
    description: A very small example.
    theme: teal
    ---
    #########
    #o..R..H#
    #########

    #  wall          .  pellet        o  power orb       (space)  empty floor
    R  runner start  H  hunter spawn

A row whose first AND last tiles are open is a TUNNEL: walking off one side of the map brings
you back on the other side.
"""

from __future__ import annotations

from pathlib import Path

Cell = tuple[int, int]          # (row, col)
Direction = tuple[int, int]     # (row step, col step)

UP: Direction = (-1, 0)
RIGHT: Direction = (0, 1)
DOWN: Direction = (1, 0)
LEFT: Direction = (0, -1)

# Every search looks at the neighbours in this fixed (clockwise) order,
# so running the same search twice always gives the same result.
DIRECTIONS: tuple[Direction, ...] = (UP, RIGHT, DOWN, LEFT)

WALL, PELLET, POWER_ORB, EMPTY, RUNNER_START, HUNTER_SPAWN = "#", ".", "o", " ", "R", "H"
SYMBOLS = {WALL, PELLET, POWER_ORB, EMPTY, RUNNER_START, HUNTER_SPAWN}

MAPS_DIR = Path(__file__).parent / "maps"


class MapError(ValueError):
    """A map is broken. The message says what is wrong and where, to help when designing maps."""


class Maze:
    """A static maze: its walls, its starting items and the graph of its open tiles."""

    def __init__(self, name: str, grid: list[str], description: str = "", theme: str = "teal") -> None:
        _check_grid(name, grid)
        self.name = name
        self.description = description
        self.theme = theme                       # colour theme used by the renderer
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0])

        self.walls: set[Cell] = set()
        self.pellets: set[Cell] = set()          # starting pellets (game.py keeps its own copy)
        self.power_orbs: set[Cell] = set()
        self.hunter_spawns: list[Cell] = []
        runner_starts: list[Cell] = []

        for row, line in enumerate(grid):
            for col, symbol in enumerate(line):
                cell = (row, col)
                if symbol == WALL:
                    self.walls.add(cell)
                elif symbol == PELLET:
                    self.pellets.add(cell)
                elif symbol == POWER_ORB:
                    self.power_orbs.add(cell)
                elif symbol == RUNNER_START:
                    runner_starts.append(cell)
                elif symbol == HUNTER_SPAWN:
                    self.hunter_spawns.append(cell)

        if len(runner_starts) != 1:
            raise MapError(f"{name}: needs exactly one 'R' (runner start), found {len(runner_starts)}")
        if not self.hunter_spawns:
            raise MapError(f"{name}: needs at least one 'H' (hunter spawn)")
        self.runner_start: Cell = runner_starts[0]

        # ---- build the graph: an adjacency list -------------------------------------------
        self.open_cells: list[Cell] = [
            (row, col) for row in range(self.height) for col in range(self.width)
            if (row, col) not in self.walls
        ]
        self.adjacency: dict[Cell, list[Cell]] = {
            cell: self._find_neighbors(cell) for cell in self.open_cells
        }
        self.has_tunnels = any(
            self.is_open((row, 0)) and self.is_open((row, self.width - 1)) for row in range(self.height)
        )

    # ------------------------------------------------------------------------------------
    # Graph queries (used by every algorithm)
    # ------------------------------------------------------------------------------------
    def neighbors(self, cell: Cell) -> list[Cell]:
        """The tiles you can step to from `cell` - an O(1) lookup in the adjacency list."""
        return self.adjacency[cell]

    def is_open(self, cell: Cell) -> bool:
        return cell in self.adjacency

    def direction(self, a: Cell, b: Cell) -> Direction:
        """The direction of the single step a -> b (a and b are neighbours). Understands tunnels."""
        d_row, d_col = b[0] - a[0], b[1] - a[1]
        if d_col > 1:        # went LEFT through a tunnel: column 0 -> last column
            d_col = -1
        elif d_col < -1:     # went RIGHT through a tunnel: last column -> column 0
            d_col = 1
        return d_row, d_col

    @property
    def vertex_count(self) -> int:
        return len(self.adjacency)

    @property
    def edge_count(self) -> int:
        # every edge appears twice in the adjacency list (a -> b and b -> a)
        return sum(len(neighbors) for neighbors in self.adjacency.values()) // 2

    def _find_neighbors(self, cell: Cell) -> list[Cell]:
        row, col = cell
        found = []
        for d_row, d_col in DIRECTIONS:
            r = row + d_row
            c = (col + d_col) % self.width       # "% width" wraps around the sides -> tunnels
            if 0 <= r < self.height and (r, c) not in self.walls:
                found.append((r, c))
        return found

    # ------------------------------------------------------------------------------------
    # Loading maps
    # ------------------------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: Path | str) -> Maze:
        path = Path(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        if "---" not in lines:
            raise MapError(f"{path.name}: missing the '---' line between the header and the grid")
        split = lines.index("---")

        info = {}
        for line in lines[:split]:
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower()] = value.strip()

        grid = lines[split + 1:]
        while grid and not grid[-1].strip():     # ignore empty lines at the end of the file
            grid.pop()
        return cls(info.get("name", path.stem), grid, info.get("description", ""), info.get("theme", "teal"))

    def __repr__(self) -> str:
        return f"Maze({self.name!r}, {self.width}x{self.height}, V={self.vertex_count}, E={self.edge_count})"


def load_maps(folder: Path = MAPS_DIR) -> list[Maze]:
    """Load every map file in the folder, sorted by file name (01_..., 02_..., ...)."""
    return [Maze.from_file(path) for path in sorted(folder.glob("*.txt"))]


def _check_grid(name: str, grid: list[str]) -> None:
    if not grid:
        raise MapError(f"{name}: the grid is empty")
    width = len(grid[0])
    for row, line in enumerate(grid):
        if len(line) != width:
            raise MapError(f"{name}: row {row} has {len(line)} tiles, expected {width} (all rows must be equally long)")
        for col, symbol in enumerate(line):
            if symbol not in SYMBOLS:
                raise MapError(f"{name}: unknown symbol {symbol!r} at row {row}, column {col}")
