"""
Tests for the maze graph and the four search algorithms.

Run all tests with:   python -m unittest discover -s tests -v
"""

from __future__ import annotations

import random
import unittest

from mazechase.algorithms import (ALGORITHM_NAMES, astar, bfs, bfs_distances, dfs, find_path, greedy_best_first,
                                  manhattan, parse_algorithm)
from mazechase.maze import MapError, Maze, load_maps

# A small maze with two routes from left to right and a tunnel in the middle row.
#   columns: 0123456789
TINY = [
    "##########",
    "#R......H#",
    "#.##.###.#",
    "..........",          # row 3 is a tunnel: open at both ends
    "#.##.###.#",
    "#........#",
    "##########",
]


def assert_valid_path(test: unittest.TestCase, maze: Maze, path: list, start, goal, blocked=frozenset()) -> None:
    """A path must start at start, end at goal, move between neighbours and avoid blocked tiles."""
    test.assertEqual(path[0], start)
    test.assertEqual(path[-1], goal)
    test.assertEqual(len(path), len(set(path)), "a tile appears twice in the path")
    for a, b in zip(path, path[1:]):
        test.assertIn(b, maze.neighbors(a), f"{a} -> {b} is not a single step")
    for tile in path[1:-1]:
        test.assertNotIn(tile, blocked)


class MazeGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.maze = Maze("Tiny", TINY)

    def test_vertices_and_edges(self) -> None:
        open_tiles = sum(line.count(".") + line.count("R") + line.count("H") for line in TINY)
        self.assertEqual(self.maze.vertex_count, open_tiles)
        # every edge is stored twice in the adjacency list (a -> b and b -> a)
        self.assertEqual(sum(len(n) for n in self.maze.adjacency.values()), 2 * self.maze.edge_count)

    def test_neighbours_are_symmetric(self) -> None:
        for cell, neighbours in self.maze.adjacency.items():
            for other in neighbours:
                self.assertIn(cell, self.maze.neighbors(other))

    def test_tunnel_wraps_around(self) -> None:
        self.assertTrue(self.maze.has_tunnels)
        self.assertIn((3, 9), self.maze.neighbors((3, 0)))
        self.assertEqual(self.maze.direction((3, 0), (3, 9)), (0, -1))     # left, through the tunnel
        self.assertEqual(self.maze.direction((3, 9), (3, 0)), (0, 1))      # right, through the tunnel

    def test_every_map_is_valid_and_connected(self) -> None:
        for maze in load_maps():
            with self.subTest(maze=maze.name):
                reachable = bfs_distances(maze, [maze.runner_start])
                self.assertEqual(len(reachable), maze.vertex_count, "some open tiles cannot be reached")
                self.assertTrue(maze.hunter_spawns)

    def test_broken_maps_are_rejected(self) -> None:
        with self.assertRaises(MapError):
            Maze("ragged", ["#####", "#R.H", "#####"])
        with self.assertRaises(MapError):
            Maze("unknown symbol", ["#####", "#RxH#", "#####"])
        with self.assertRaises(MapError):
            Maze("no runner", ["#####", "#..H#", "#####"])


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.maze = Maze("Tiny", TINY)
        self.start, self.goal = (1, 1), (1, 8)

    def test_bfs_finds_the_shortest_path(self) -> None:
        result = bfs(self.maze, self.start, self.goal)
        self.assertEqual(result.length, 7)
        assert_valid_path(self, self.maze, result.path, self.start, self.goal)

    def test_every_algorithm_returns_a_valid_path(self) -> None:
        for name in ALGORITHM_NAMES:
            with self.subTest(algorithm=name):
                result = find_path(name, self.maze, self.start, self.goal)
                self.assertTrue(result.found)
                assert_valid_path(self, self.maze, result.path, self.start, self.goal)
                self.assertIn(self.goal, result.expanded)
                self.assertGreaterEqual(result.max_frontier, 1)

    def test_start_equals_goal(self) -> None:
        for search in (bfs, dfs, astar, greedy_best_first):
            result = search(self.maze, self.start, self.start)
            self.assertEqual(result.path, [self.start])
            self.assertEqual(result.length, 0)

    def test_blocked_tiles_are_avoided_and_can_make_the_goal_unreachable(self) -> None:
        # Block the top corridor: the path must go around through the lower part of the maze.
        blocked = frozenset({(1, 4)})
        for search in (bfs, dfs, astar, greedy_best_first):
            result = search(self.maze, self.start, self.goal, blocked)
            self.assertTrue(result.found)
            assert_valid_path(self, self.maze, result.path, self.start, self.goal, blocked)
        # Wall the start in completely: no path at all.
        walled_in = frozenset({(1, 2), (2, 1)})
        for search in (bfs, dfs, astar, greedy_best_first):
            result = search(self.maze, self.start, self.goal, walled_in)
            self.assertFalse(result.found)
            self.assertEqual(result.path, [])
            self.assertEqual(result.length, -1)

    def test_optimality_on_every_map(self) -> None:
        """BFS and A* always find a shortest path; DFS and Greedy never find a shorter one."""
        rng = random.Random(42)
        for maze in load_maps():
            for _ in range(60):
                start, goal = rng.sample(maze.open_cells, 2)
                shortest = bfs(maze, start, goal).length
                with self.subTest(maze=maze.name, start=start, goal=goal):
                    self.assertEqual(astar(maze, start, goal).length, shortest)
                    self.assertGreaterEqual(dfs(maze, start, goal).length, shortest)
                    self.assertGreaterEqual(greedy_best_first(maze, start, goal).length, shortest)

    def test_astar_explores_no_more_than_bfs(self) -> None:
        rng = random.Random(7)
        for maze in load_maps():
            total_bfs = total_astar = 0
            for _ in range(60):
                start, goal = rng.sample(maze.open_cells, 2)
                total_bfs += len(bfs(maze, start, goal).expanded)
                total_astar += len(astar(maze, start, goal).expanded)
            self.assertLess(total_astar, total_bfs, maze.name)

    def test_parse_algorithm(self) -> None:
        self.assertEqual(parse_algorithm("astar"), "A*")
        self.assertEqual(parse_algorithm("A-star"), "A*")
        self.assertEqual(parse_algorithm("bfs"), "BFS")
        self.assertEqual(parse_algorithm("Greedy"), "Greedy")
        with self.assertRaises(ValueError):
            parse_algorithm("dijkstra")


class DistanceMapAndHeuristicTests(unittest.TestCase):
    def test_multi_source_bfs_equals_the_minimum_of_single_source_bfs(self) -> None:
        maze = load_maps()[0]
        sources = maze.hunter_spawns
        combined = bfs_distances(maze, sources)
        singles = [bfs_distances(maze, [source]) for source in sources]
        for tile in maze.open_cells:
            self.assertEqual(combined[tile], min(single[tile] for single in singles))

    def test_distance_map_matches_bfs_path_lengths(self) -> None:
        maze = Maze("Tiny", TINY)
        distances = bfs_distances(maze, [(1, 1)])
        for tile in maze.open_cells:
            self.assertEqual(distances[tile], bfs(maze, (1, 1), tile).length)

    def test_limit_stops_the_wave(self) -> None:
        maze = load_maps()[1]
        limited = bfs_distances(maze, [maze.runner_start], limit=5)
        full = bfs_distances(maze, [maze.runner_start])
        self.assertTrue(limited)
        self.assertLessEqual(max(limited.values()), 5)
        self.assertEqual(set(limited), {tile for tile, d in full.items() if d <= 5})

    def test_manhattan_is_admissible_and_consistent(self) -> None:
        for maze in load_maps():
            rng = random.Random(maze.name)
            for goal in rng.sample(maze.open_cells, 8):
                true_distance = bfs_distances(maze, [goal])
                for tile in maze.open_cells:
                    h = manhattan(maze, tile, goal)
                    self.assertLessEqual(h, true_distance[tile], f"{maze.name}: overestimates at {tile}")
                    for neighbour in maze.neighbors(tile):              # consistent: h(n) <= 1 + h(n')
                        self.assertLessEqual(h, 1 + manhattan(maze, neighbour, goal))


if __name__ == "__main__":
    unittest.main()
