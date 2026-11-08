"""Record the contract fixtures from the Python reference app (docs/research/67).

Usage, from the repository root:  python3 -I packages/contracts/fixtures/record.py
Plays one offline (scripted) Little Round Top game in a temporary SQLite file:
one order body (a hold with ``destination: null`` and a hold with no
destination key), one staff chat message, then INTERVALS clock intervals,
under a second of CPU. Each response is written as ``HttpApi`` returns it to
the HTTP handler (no server is started). The game id is pinned (``GAME_ID``)
so a refresh rewrites only what the Python app changed.
"""
import json
import sys
import tempfile
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "apps" / "poc"))

from battle import storage  # noqa: E402
from battle.adapters.http_api import HttpApi  # noqa: E402
from battle.bootstrap import build_application  # noqa: E402
from battle.config import Settings  # noqa: E402

SCENARIO = "little-round-top"
INTERVALS = int(sys.argv[1]) if len(sys.argv) > 1 else 12
# Store.create uses uuid4().hex[:16]; this UUID gives the id "f1c7f1c7f1c7f1c7".
GAME_ID_UUID = uuid.UUID("f1c7f1c7f1c7f1c7f1c7f1c7f1c7f1c7")


def write(name, document):
    (HERE / name).write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")


def cursor(api):
    state = api.read("/api/state", {})
    return {"game_id": state["game_id"], "revision": state["revision"]}


def record(api):
    units = api.read("/api/state", {})["units"]
    body = {"orders": [{"unit_id": units[0]["id"], "stance": "hold", "destination": None},
                       {"unit_id": units[2]["id"], "stance": "hold"}], **cursor(api)}
    write("orders-request.json", body)
    api.mutate("/api/orders", body)
    api.mutate("/api/chat", {"text": "Report the state of the command.", **cursor(api)})
    for _ in range(INTERVALS):
        api.mutate("/api/advance", cursor(api))
    state = api.read("/api/state", {})
    write("state-commander.json", state)
    write("state-god.json", api.read("/api/state", {"view": ["god"]}))
    write("history.json", api.read("/api/history", {}))
    revision = [str(state["revision"])]
    write("replay-commander.json", api.read("/api/replay", {"revision": revision}))
    write("replay-side.json", api.read("/api/replay", {"revision": revision, "side": [state["side"]]}))
    write("replay-god.json", api.read("/api/replay", {"revision": revision, "view": ["god"]}))
    write("map.json", api.read("/api/map", {}))
    write("scenarios.json", api.read("/api/scenarios", {}))
    write("map-features.json", catalog_features())


def catalog_features():
    """docs/research/73: each catalog entry's opening commander ``map_features``
    (the projection /api/state serves: ``present_view`` of ``RulesSimulation.view``,
    as apps/poc/scripts/check_map_features.mjs reads it), with the map's
    ``metres_per_hex`` and its bridge crossing cells from ``map_document``."""
    from battle.adapters.rules import RulesSimulation
    from battle.bootstrap import build_headless_scenarios
    from battle.presentation import present_view
    from battle.scenario_entry import build_state, map_document

    catalog = build_headless_scenarios()
    sim = RulesSimulation()
    out = {}
    for sid in catalog.ids():
        entry = catalog.resolve(sid)
        doc = map_document(entry)
        out[sid] = {
            "map_features": present_view(sim.view(build_state(entry)), entry)["map_features"],
            "metres_per_hex": doc["metres_per_hex"],
            "bridge_cells": [c for c in doc["cells"] if c.get("crossing") == "bridge"],
        }
    return out


def main():
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(storage.uuid, "uuid4", return_value=GAME_ID_UUID):
            app = build_application(Path(tmp) / "battle.sqlite", offline=True,
                                    settings=Settings(), scenario_id=SCENARIO)
        try:
            record(HttpApi(app))
        finally:
            app.close()


if __name__ == "__main__":
    main()
