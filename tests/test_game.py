"""
Tests for the maze generator, the game rules and the runner's reasoning.

Run all tests with:   python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from mazechase.algorithms import bfs, bfs_distances
from mazechase.config import PELLET_POINTS, START_LIVES, TICK
from mazechase.game import FINISHED, Game
from mazechase.generator import generate_maze
from mazechase.maze import load_maps


class GeneratorTests(unittest.TestCase):
    def test_same_seed_same_maze(self) -> None:
        self.assertEqual(generate_maze(3).grid, generate_maze(3).grid)
        self.assertNotEqual(generate_maze(3).grid, generate_maze(4).grid)

    def test_generated_mazes_are_playable(self) -> None:
        for seed in range(25):
            maze = generate_maze(seed)
            with self.subTest(seed=seed):
                # connected: every open tile can be reached
                self.assertEqual(len(bfs_distances(maze, [maze.runner_start])), maze.vertex_count)
                # braided: no dead ends (every tile has at least two exits)
                for cell in maze.open_cells:
                    self.assertGreaterEqual(len(maze.neighbors(cell)), 2, f"dead end at {cell}")
                # mirrored: the right half is the left half reversed
                for line in maze.grid:
                    plain = line.replace("R", ".").replace("H", ".").replace("o", ".")
                    self.assertEqual(plain, plain[::-1])


class GameRuleTests(unittest.TestCase):
    def play(self, game: Game, seconds: float) -> None:
        for _ in range(int(seconds / TICK)):
            game.update(TICK)
            if game.is_over:
                break

    def test_the_same_seed_gives_the_same_game(self) -> None:
        maze = load_maps()[0]
        first, second = Game(maze, "A*", 4, seed=5), Game(maze, "A*", 4, seed=5)
        self.play(first, 25)
        self.play(second, 25)
        self.assertEqual((first.score, first.lives, first.runner.cell, [h.cell for h in first.hunters]),
                         (second.score, second.lives, second.runner.cell, [h.cell for h in second.hunters]))

    def test_score_and_food_add_up(self) -> None:
        game = Game(load_maps()[2], "BFS", 4, seed=1)
        self.play(game, 30)
        eaten = game.food_total - game.food_left
        self.assertGreater(eaten, 0)
        self.assertGreaterEqual(game.score, eaten * PELLET_POINTS)
        self.assertEqual(game.lives, START_LIVES - game.deaths)

    def test_every_algorithm_can_drive_the_runner(self) -> None:
        for algorithm in ("BFS", "DFS", "A*", "Greedy"):
            with self.subTest(algorithm=algorithm):
                game = Game(load_maps()[3], algorithm, 4, seed=2)
                self.play(game, 15)
                self.assertGreater(game.runner.searches, 0)
                self.assertLess(game.food_left, game.food_total)

    def test_a_game_always_ends(self) -> None:
        game = Game(load_maps()[1], "A*", 4, seed=3)
        self.play(game, 400)
        self.assertIn(game.status, FINISHED)


class RunnerReasoningTests(unittest.TestCase):
    def test_territory_lemma(self) -> None:
        """If the runner reaches tile t before every hunter, it also reaches every tile on a
        shortest path to t before every hunter. This is why a safe route always exists."""
        for maze in load_maps():
            game = Game(maze, "A*", 4, seed=4)
            checks = 0
            for tick in range(int(40 / TICK)):
                game.update(TICK)
                if game.is_over:
                    break
                if tick % 30:
                    continue
                threats = [tile for hunter in game.hunters if hunter.is_threat
                           for tile in (hunter.cell, hunter.next_cell)]
                danger = bfs_distances(maze, threats)
                reach = bfs_distances(maze, [game.runner.cell])
                territory = {t for t, d in reach.items() if d < danger.get(t, float("inf"))}
                for tile in territory:
                    path = bfs(maze, game.runner.cell, tile).path
                    self.assertTrue(set(path) <= territory, f"{maze.name}: shortest path to {tile} leaves the territory")
                checks += 1
            self.assertGreater(checks, 0)

    def test_runner_explains_every_decision(self) -> None:
        game = Game(load_maps()[0], "A*", 4, seed=1)
        for _ in range(int(10 / TICK)):
            game.update(TICK)
        self.assertIn(game.runner.mode, ("EAT", "ESCAPE", "HUNT", "TRAPPED"))
        self.assertTrue(game.runner.thought)


if __name__ == "__main__":
    unittest.main()
