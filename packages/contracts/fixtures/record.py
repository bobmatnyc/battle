"""Record the contract fixtures from the Python reference app (docs/research/67).

Usage, from the repository root:  python3 -I packages/contracts/fixtures/record.py
Plays one offline (scripted) Little Round Top game in a temporary SQLite file:
one hold order, one staff chat message, then INTERVALS clock intervals, about
a second of CPU. Each response is written as ``HttpApi`` returns it to the
HTTP handler (no server is started). ``game_id`` is random per run.
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "apps" / "poc"))

from battle.adapters.http_api import HttpApi  # noqa: E402
from battle.bootstrap import build_application  # noqa: E402
from battle.config import Settings  # noqa: E402

SCENARIO = "little-round-top"
INTERVALS = int(sys.argv[1]) if len(sys.argv) > 1 else 12


def write(name, document):
    (HERE / name).write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")


def cursor(api):
    state = api.read("/api/state", {})
    return {"game_id": state["game_id"], "revision": state["revision"]}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        app = build_application(Path(tmp) / "battle.sqlite", offline=True,
                                settings=Settings(), scenario_id=SCENARIO)
        api = HttpApi(app)
        own = api.read("/api/state", {})["units"][0]["id"]
        body = {"orders": [{"unit_id": own, "stance": "hold", "destination": None}], **cursor(api)}
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
        app.close()


if __name__ == "__main__":
    main()
