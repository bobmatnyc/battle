"""Evaluator fixture: route closure on a synthetic hex board, not an ancient combat model.

From apps/poc run: python3 -m unittest discover -s experiments/cannae -v
"""
import unittest
from battle import grid


class CannaeEscapeRoutes(unittest.TestCase):
    def setUp(self):
        self.center = [12, 10]
        self.cells = {}
        self.sectors = {name: set() for name in ('front', 'left', 'right', 'rear')}
        self.exits = [[4, 19], [12, 19], [20, 19]]
        for row in range(grid.ROWS):
            for col in range(grid.COLS):
                pos = [col, row]
                key = grid.key(pos)
                self.cells[key] = {'move_cost': 100, 'elevation': 0}
                if grid.distance(self.center, pos) == 4:
                    if row <= 7:
                        sector = 'front'
                    elif row >= 13:
                        sector = 'rear'
                    else:
                        sector = 'left' if col < 12 else 'right'
                    self.sectors[sector].add(key)

    def can_escape(self, sectors):
        blocked = set().union(*(self.sectors[name] for name in sectors))
        return any(grid.path(self.cells, self.center, exit_hex, blocked)
                   for exit_hex in self.exits)

    def test_center_engaged_withdrawal_open(self):
        self.assertTrue(self.can_escape(['front']))

    def test_two_wings_leave_a_rear_exit(self):
        self.assertTrue(self.can_escape(['front', 'left', 'right']))

    def test_both_wings_and_rear_close_all_exits(self):
        self.assertFalse(self.can_escape(['front', 'left', 'right', 'rear']))

    def test_each_missing_sector_reopens_a_route(self):
        for name in self.sectors:
            with self.subTest(missing_sector=name):
                self.assertTrue(self.can_escape(set(self.sectors) - {name}))
