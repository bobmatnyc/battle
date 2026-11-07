"""Roads, buildings and works of every catalog scenario, through the engine's own
pathfinder, sight and observer views (docs/research/64).

The hexes below are each entry's own road ends and building hexes; no entry is
changed. The rendering half is scripts/check_map_features.mjs.
"""

import copy
import unittest

from battle import analysis, engine, grid, recon
from battle.adapters.rules import RulesSimulation
from battle.bootstrap import build_headless_scenarios
from battle.command_policy import observation_for
from battle.presentation import present_view
from battle.scenario_entry import build_state
from battle.services.queries import BattleQueries
from battle.services.replay import ReplayService
from test_services import MemoryRepository

CATALOG = build_headless_scenarios()

# Scenario id -> (road id, first routed hex, last routed hex), from MapEntry.features.
ROADS = {
    "little-round-top": (("north-lane", [3, 2], [22, 10]), ("south-track", [1, 19], [9, 16])),
    "hougoumont-north-gate": (("north-lane", [11, 8], [12, 1]), ("west-lane", [7, 18], [11, 8]),
                              ("wood-ride", [11, 20], [11, 13])),
    "concord-north-bridge": (("muster-road", [2, 10], [11, 10]), ("town-road", [13, 10], [23, 10])),
    "concord-north-bridge-v1": (("muster-road", [2, 10], [11, 10]), ("town-road", [13, 10], [23, 10])),
    "pegasus-bridge": (("benouville-road", [0, 10], [8, 10]), ("bridges-road", [10, 10], [18, 10]),
                       ("ranville-road", [20, 10], [23, 10])),
}

# Scenario id -> (building id, observer hex, target hex): a line through the building hex.
SIGHT = {
    "little-round-top": (("farmstead", [6, 3], [8, 3]),  # across the Farmstead
                         ("barn", [16, 8], [18, 9])),  # along the North farm lane past the Barn
    # From the lane outside the north gate to the end of the ride through the wood.
    "hougoumont-north-gate": (("hougoumont", [11, 8], [11, 13]),),
}

# Scenario id -> fortification ids briefed in the entry.
WORKS = {
    "little-round-top": ("prepared-works",),
    "pegasus-bridge": ("west-mg-posts", "west-trenches", "east-mg-post", "orne-pillbox"),
    "hill-223-patrol": ("old-trench",),
}


def route_cost(cells, start, route):
    return sum(grid.cost(cells, a, b) for a, b in zip([start] + route, route))


def without_roads(cells):
    cells = copy.deepcopy(cells)
    for c in cells.values():
        c.pop("road_neighbors", None)
    return cells


class CatalogFeatureCoverageTests(unittest.TestCase):
    def test_every_scenario_with_roads_buildings_or_works_is_listed(self):
        for sid in CATALOG.ids():
            features = CATALOG.resolve(sid).map.features
            with self.subTest(sid):
                self.assertEqual(tuple(r["id"] for r in features.get("roads", ())),
                                 tuple(r[0] for r in ROADS.get(sid, ())))
                self.assertEqual({b["id"] for b in features.get("buildings", ())},
                                 {s[0] for s in SIGHT.get(sid, ())})
                self.assertEqual(tuple(w["id"] for w in features.get("works", ())), WORKS.get(sid, ()))


class RoadRouteTests(unittest.TestCase):
    def test_each_named_road_is_cheaper_than_the_off_road_route(self):
        for sid, roads in ROADS.items():
            s = build_state(CATALOG.resolve(sid))
            off_road = without_roads(s["cells"])
            built = {f["id"]: f for f in s["map_features"] if f["kind"] == "road"}
            for rid, start, end in roads:
                with self.subTest(scenario=sid, road=rid):
                    road = built[rid]
                    self.assertEqual((road["hexes"][0], road["hexes"][-1]), (start, end))
                    on = grid.path(s["cells"], start, end)
                    off = grid.path(off_road, start, end)
                    self.assertTrue(on and off)
                    # The pathfinder keeps to the named road, every hex of it.
                    self.assertEqual([start] + on, road["hexes"])
                    self.assertLess(route_cost(s["cells"], start, on), route_cost(off_road, start, off))


class BuildingSightTests(unittest.TestCase):
    def test_each_building_blocks_a_named_sight_line_and_adds_cover(self):
        for sid, lines in SIGHT.items():
            s = build_state(CATALOG.resolve(sid))
            for bid, a, b in lines:
                with self.subTest(scenario=sid, building=bid):
                    f = next(f for f in s["map_features"] if f["id"] == bid)
                    self.assertIn(f["pos"], grid.line(a, b)[1:-1])
                    bare = copy.deepcopy(s)
                    bare["cells"][grid.key(f["pos"])]["obstacle_height"] = 0
                    observer = {"pos": a}
                    self.assertTrue(recon.sees(bare, observer, b))  # Clear without the building...
                    self.assertFalse(recon.sees(s, observer, b))  # ...blocked by it.
                    cell = s["cells"][grid.key(f["pos"])]
                    self.assertEqual((cell["building"], cell["obstacle_height"]), (bid, f["height"]))
                    self.assertGreaterEqual(cell["cover"], f["cover"])

    def test_briefed_works_raise_their_cell_cover(self):
        for sid, ids in WORKS.items():
            s = build_state(CATALOG.resolve(sid))
            for wid in ids:
                with self.subTest(scenario=sid, works=wid):
                    f = next(f for f in s["map_features"] if f["id"] == wid)
                    self.assertGreaterEqual(s["cells"][grid.key(f["pos"])]["cover"], f["cover"])


class ObserverTerrainTests(unittest.TestCase):
    """docs/research/24: a side sees briefed features and works it has a report of,
    never unseen live works. Little Round Top: `test_remote_construction_requires_reports_and_does_not_leak_to_inference`."""

    def test_hill_223_commander_and_replay_show_only_reported_works(self):
        entry = CATALOG.resolve("hill-223-patrol")
        repository, sim = MemoryRepository(), RulesSimulation()
        queries = BattleQueries(repository, sim, ReplayService(repository, sim),
                                assess=analysis.assess, present=present_view, scenarios=CATALOG)
        s = build_state(entry)
        game_id = repository.create(s)
        briefed = sorted(f["id"] for f in s["map_features"])
        self.assertEqual(sorted(f["id"] for f in queries.replay(game_id, 0)["map_features"]), briefed)

        def step(action):
            nonlocal s
            updated = sim.apply(s, action)
            repository.save(game_id, updated, s["revision"])
            s = updated

        # A2 digs at (15, 3), six hexes from the Company G post and beyond its 3-hex sight.
        step({"type": "orders", "orders": [{"unit_id": "A2", "stance": "dig_in", "destination": None}]})
        while not any(f["id"] == "works-15,3" for f in s["map_features"]):
            step({"type": "advance"})
            self.assertLess(s["turn"], 20)
        unseen = s["revision"]
        self.assertGreater(s["cells"]["15,3"]["cover"], s["briefing_cells"]["15,3"]["cover"])
        for shown in (engine.view(s), queries.replay(game_id, unseen)):
            self.assertEqual(sorted(f["id"] for f in shown["map_features"]), briefed)
        known = observation_for(s, "american")["known_terrain"]
        self.assertEqual(next(c["cover"] for c in known if c["pos"] == [15, 3]), s["briefing_cells"]["15,3"]["cover"])
        self.assertIn("works-15,3", [f["id"] for f in queries.replay(game_id, unseen, god=True)["map_features"]])

        while not any(f["id"] == "works-15,3" for f in engine.view(s)["map_features"]):
            step({"type": "advance"})
            self.assertLess(s["turn"], 30)
        reported = next(f for f in queries.replay(game_id, s["revision"])["map_features"] if f["id"] == "works-15,3")
        # The report is older than the ground: it carries the progress at observation.
        self.assertLess(reported["progress"], next(f for f in s["map_features"] if f["id"] == "works-15,3")["progress"])
        self.assertLessEqual(reported["observed_turn"], s["turn"])
        # The earlier revision still shows nothing the side had not been told.
        self.assertNotIn("works-15,3", [f["id"] for f in queries.replay(game_id, unseen)["map_features"]])


if __name__ == "__main__":
    unittest.main()
