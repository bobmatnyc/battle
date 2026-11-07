"""docs/research/65: replay as either side's commander view or as God, in every
player scenario, with each side shown only its own records and no write on read."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from battle import engine
from battle.adapters.http_api import HttpApi
from battle.adapters.rules import RulesSimulation
from battle.bootstrap import PLAYER_SCENARIOS, build_application, build_scenarios
from battle.command_policy import observation_for
from battle.config import Settings
from battle.scenario_entry import build_state
from battle.storage import Store

# Fields BattleService.state adds to the projection; a recorded snapshot has none.
LIVE_ONLY = ("clock", "game_id", "mode", "model", "inference_available", "messages",
             "last_commander_source", "last_fallback_reason")
# God-view fields no commander view may carry (engine.god_view).
GOD_ONLY = ("view_mode", "reports", "events", "decisions", "headquarters", "commands",
            "retired_units", "captives")


def digest(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()


def recorded(document):
    return {k: v for k, v in document.items() if k not in LIVE_ONLY}


def stored_records(path):
    """Every row of every table, as SQLite dumps it: the byte-level record."""
    db = sqlite3.connect(path)
    try:
        return "\n".join(db.iterdump())
    finally:
        db.close()


def brief_mission(entry, side):
    spec = entry.sides[side]
    return spec.brief.mission_text if spec.brief else spec.mission


def replay(api, revision, *, side=None, god=False, game_id=None):
    query = {"revision": [str(revision)], "game_id": [game_id or api.service.game_id]}
    if side:
        query["side"] = [side]
    if god:
        query["view"] = ["god"]
    return api.read("/api/replay", query)


def played(tmp, scenario_id, intervals=80):
    """A live offline game: one player order, then clock intervals until the
    battle ends (both player scenarios end before 80). Returns the app, the
    API and, per revision, what each side and God saw live at that revision."""
    app = build_application(Path(tmp) / "battle.sqlite", offline=True,
                            settings=Settings(), scenario_id=scenario_id)
    api = HttpApi(app)
    live = {}

    def capture():
        state = app.repository.load(app.game_id)  # The current game row, not a snapshot.
        sides = engine.sides(state)
        live[state["revision"]] = {
            "player": recorded(app.state()),
            "god": recorded(app.state(god=True)),
            "sides": {side: digest(app.queries.project(state, side=side)) for side in sides},
            "observed": {side: observation_for(state, side) for side in sides},
        }
        return state

    state = capture()
    own = next(u["id"] for u in app.state()["units"])
    app.execute("orders", {"orders": [{"unit_id": own, "stance": "hold", "destination": None}]},
                game_id=app.game_id, revision=state["revision"])
    for _ in range(intervals):
        state = capture()
        if state["status"] != "active":
            break
        app.execute("advance", {}, game_id=app.game_id, revision=state["revision"])
    capture()
    return app, api, live


class ReplayViewTests(unittest.TestCase):
    def test_each_side_replay_equals_its_live_view_at_every_revision(self):
        for entry in PLAYER_SCENARIOS:
            with self.subTest(scenario=entry.id), tempfile.TemporaryDirectory() as tmp:
                app, api, live = played(tmp, entry.id)
                state = app.repository.load(app.game_id)
                self.assertEqual(state["status"], "complete")  # The opponent's replay is unlocked.
                player, sides = engine.player_side(state), engine.sides(state)
                self.assertEqual(len(sides), 2)
                self.assertEqual([h["revision"] for h in app.queries.history(app.game_id)], sorted(live))
                for revision, seen in live.items():
                    default = replay(api, revision)
                    self.assertEqual(default, seen["player"], revision)
                    self.assertEqual(replay(api, revision, god=True), seen["god"], revision)
                    for side in sides:
                        view = replay(api, revision, side=side)
                        self.assertEqual(view["side"], side)
                        self.assertEqual(view["scenario_brief"]["side"]["id"], side)
                        self.assertEqual(digest(view), seen["sides"][side], (revision, side))
                        # The same units and contacts the side's commander decided from,
                        # less the order-acceptance marks the observation adds.
                        observed = seen["observed"][side]
                        units = [{k: v for k, v in u.items() if k not in ("accepts_orders", "order_refusal")}
                                 for u in observed["units"]]
                        self.assertEqual(view["units"], units, (revision, side))
                        self.assertEqual(view["contacts"], observed["contacts"], (revision, side))
                    self.assertEqual(replay(api, revision, side=player), default)
                app.close()

    def test_no_side_replay_shows_the_other_sides_unseen_units_or_works(self):
        catalog, simulation = build_scenarios(), RulesSimulation()
        for entry in PLAYER_SCENARIOS:
            for digger in engine.sides(build_state(entry)):
                with self.subTest(scenario=entry.id, digger=digger), tempfile.TemporaryDirectory() as tmp:
                    self._no_leak(catalog, simulation, entry, digger, Path(tmp) / "battle.sqlite")

    def _no_leak(self, catalog, simulation, entry, digger, db):
        app = build_application(db, offline=True, settings=Settings(), scenario_id=entry.id)
        api, repository = HttpApi(app), app.repository
        s = repository.load(app.game_id)
        viewer = next(x for x in engine.sides(s) if x != digger)
        missions = {side: brief_mission(catalog.resolve(entry.id), side) for side in engine.sides(s)}
        orders = [{"unit_id": u["id"], "stance": "dig_in", "destination": None}
                  for u in s["units"] if u["side"] == digger]
        action = ({"type": "orders", "orders": orders} if digger == engine.player_side(s) else
                  {"type": "advance", "decision": {"side": digger, "source": "scripted", "orders": orders}})
        while s["status"] == "active":  # Played to the end: the opponent's replay is locked before.
            updated = simulation.apply(s, action)
            repository.save(app.game_id, updated, s["revision"])
            s, action = updated, {"type": "advance"}
            self.assertLess(s["turn"], 80)
        unseen_units = unseen_works = 0
        for revision in range(1, s["revision"] + 1):
            s = repository.load(app.game_id, revision)
            god = replay(api, s["revision"], god=True)
            for side in engine.sides(s):
                other = next(x for x in engine.sides(s) if x != side)
                view = replay(api, s["revision"], side=side)
                text = json.dumps(view)
                self.assertFalse(set(GOD_ONLY) & set(view), side)
                self.assertTrue(all(u["side"] == side for u in view["units"]))
                self.assertTrue(all(o["side"] == side for o in view["orders"]))
                self.assertNotIn(missions[other], text)  # The other side's brief stays out.
                known = s["contacts"][side]
                self.assertLessEqual({c["id"] for c in view["contacts"]}, set(known))
                for u in s["units"]:
                    if u["side"] == other and u["id"] not in known:
                        unseen_units += 1
                        self.assertNotIn(u["id"], [x["id"] for x in view["units"] + view["contacts"]])
                        self.assertIn(u["id"], [x["id"] for x in god["units"]])
                reported = set(s["feature_reports"][side])
                self.assertLessEqual({f["id"] for f in view["map_features"]}, reported)
                for f in s["map_features"]:
                    if f["id"] not in reported:
                        unseen_works += side == viewer
                        self.assertNotIn(f["id"], text)
                        self.assertIn(f["id"], [x["id"] for x in god["map_features"]])
        # The checks above ran against something to hide.
        self.assertGreater(unseen_works, 0)
        self.assertGreater(unseen_units, 0)
        app.close()

    def test_switching_replay_views_leaves_stored_records_byte_identical(self):
        for entry in PLAYER_SCENARIOS:
            with self.subTest(scenario=entry.id), tempfile.TemporaryDirectory() as tmp:
                app, api, live = played(tmp, entry.id)
                path = Path(tmp) / "battle.sqlite"
                before, commander = stored_records(path), recorded(app.state())
                sides = engine.sides(app.repository.load(app.game_id))
                for revision in sorted(live):
                    replay(api, revision, god=True)
                    for side in (*sides, *reversed(sides)):
                        replay(api, revision, side=side)
                    replay(api, revision)
                    api.read("/api/state", {"view": ["god"]})
                self.assertEqual(stored_records(path), before)
                # Returning to the commander view merges nothing God showed.
                self.assertEqual(recorded(api.read("/api/state", {})), commander)
                app.close()

    def test_replay_refuses_an_unknown_side_and_side_with_god(self):
        with tempfile.TemporaryDirectory() as tmp:
            app, api, _ = played(tmp, "little-round-top")
            self.assertEqual(app.repository.load(app.game_id)["status"], "complete")
            for side, god in (("french", False), ("", False), ("union", True), ("confederate", True)):
                with self.subTest(side=side, god=god), self.assertRaises(ValueError):
                    # Straight to the query: HTTP parsing drops an empty ``side=``.
                    app.queries.replay(app.game_id, 0, side=side, god=god)
            app.close()

    def test_opponent_replay_is_locked_until_the_battle_is_complete(self):
        for entry in PLAYER_SCENARIOS:
            with self.subTest(scenario=entry.id), tempfile.TemporaryDirectory() as tmp:
                app = build_application(Path(tmp) / "battle.sqlite", offline=True,
                                        settings=Settings(), scenario_id=entry.id)
                api, gid = HttpApi(app), app.game_id
                state = app.repository.load(gid)
                player = engine.player_side(state)
                opponent = next(x for x in engine.sides(state) if x != player)
                while state["status"] == "active":
                    for revision in range(state["revision"] + 1):  # Every snapshot, while active.
                        with self.assertRaisesRegex(ValueError, "unlocks after battle completion"):
                            replay(api, revision, side=opponent)
                        self.assertEqual(replay(api, revision, side=player)["side"], player)
                    app.execute("advance", {}, game_id=gid, revision=state["revision"])
                    state = app.repository.load(gid)
                    self.assertLess(state["turn"], 80)
                for revision in range(state["revision"] + 1):
                    snapshot = app.repository.load(gid, revision)
                    view = replay(api, revision, side=opponent)
                    self.assertEqual(view, app.queries.project(snapshot, side=opponent))
                    commander = engine.view(snapshot, opponent)
                    for key in ("side", "units", "contacts", "orders", "map_features"):
                        self.assertEqual(view[key], commander[key], (revision, key))
                app.close()

    def test_no_endpoint_shows_the_opponent_mission_during_an_active_battle(self):
        catalog = build_scenarios()
        for entry in PLAYER_SCENARIOS:
            with self.subTest(scenario=entry.id), tempfile.TemporaryDirectory() as tmp:
                app = build_application(Path(tmp) / "battle.sqlite", offline=True,
                                        settings=Settings(), scenario_id=entry.id)
                api, gid = HttpApi(app), app.game_id
                state = app.repository.load(gid)
                player = engine.player_side(state)
                opponent = next(x for x in engine.sides(state) if x != player)
                mission = brief_mission(catalog.resolve(entry.id), opponent)
                for _ in range(6):
                    app.execute("advance", {}, game_id=gid, revision=state["revision"])
                    state = app.repository.load(gid)
                self.assertEqual(state["status"], "active")
                shown = [api.read("/api/state", {}), api.read("/api/state", {"view": ["god"]}),
                         api.read("/api/history", {"game_id": [gid]})]
                for revision in range(state["revision"] + 1):
                    shown += [replay(api, revision), replay(api, revision, god=True),
                              replay(api, revision, side=player)]
                    try:
                        shown.append(replay(api, revision, side=opponent))
                    except ValueError:
                        pass  # Locked: nothing returned.
                for document in shown:
                    self.assertNotIn(mission, json.dumps(document))
                app.close()


if __name__ == "__main__":
    unittest.main()
