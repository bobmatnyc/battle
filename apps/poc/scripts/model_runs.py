"""Run a batch of model games under a spend cap (docs/research/69 §9).

Why: the headless runner has no spend limit, and a provider failure turns a
decision into a scripted fallback while the run goes on (doc 69 §5, §8 gaps 1,
3 and 4). A paid batch needs a driver that stops on spend and on any fallback.
What: ``--plan ENTRY[/VARIANT]`` (repeatable) names the games; each plan item
plays ``--games N`` model games, in plan order, one model side (the entry's
player) against the entry's scripted control, each in its own ``BatchStore``
database under ``--dir``. After each game the recorded ``usage.cost`` of every
player decision is added to a running total. Guards, all fail-closed:

- cap: no game starts once the total reaches ``--cap-usd``; exit 3;
- fallback: the runner aborts at the first player decision that fell back
  (``abort_on_fallback``), and a finished game is checked again for any
  fallback or non-model decision; the game is failed, its database is renamed
  ``*.failed.sqlite``, and the batch stops with exit 4;
- cost: a player decision with no readable cost fails the game (exit 4); it is
  never counted as $0;
- replay: a game whose replay is not ``identical`` fails (exit 4).

One JSON line is printed per game, then a final summary, also written to
``batch-summary.json`` in ``--dir``. Exit 0 means every planned game finished
as a model game below the cap. A game in flight is not stopped by the cap, so
one game can overshoot it by that game's cost (doc 69 §5).
Usage, from apps/poc: ``python3 scripts/model_runs.py --plan pegasus-bridge
--plan gergovia-recall/recall-audible --model anthropic/claude-sonnet-5.5
--effort high --games 2 --cap-usd 4 --dir artifacts/<batch>``. It reads the
OpenRouter key through ``Settings``, as ``python3 -m battle --headless`` does.
Test: `tests/test_model_runs.py`.
"""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless  # noqa: E402
from battle.config import EFFORTS  # noqa: E402
from battle.scenario import LITTLE_ROUND_TOP  # noqa: E402
from battle.scenario_concord import CONCORD_NORTH_BRIDGE, VARIANTS as CONCORD_VARIANTS  # noqa: E402
from battle.scenario_gergovia import GERGOVIA_RECALL, VARIANTS as GERGOVIA_VARIANTS  # noqa: E402
from battle.scenario_hill223 import HILL_223_PATROL, VARIANTS as HILL_VARIANTS  # noqa: E402
from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE  # noqa: E402
from battle.scenario_pegasus import (  # noqa: E402
    CROSSED_SENSITIVITY, PEGASUS_BRIDGE, RANGE_SENSITIVITY, VARIANTS as PEGASUS_VARIANTS,
)
from battle.services.headless import ModelFallback  # noqa: E402

EXIT_DONE, EXIT_CAP, EXIT_FAILED = 0, 3, 4


def _named(*tables):
    return {name: v.entry for table in tables for name, v in table.items()}


# The six entries of doc 69 and their named variants. Cannae waits on D34.
CATALOG = {
    LITTLE_ROUND_TOP.id: (LITTLE_ROUND_TOP, {}),
    HOUGOUMONT_NORTH_GATE.id: (HOUGOUMONT_NORTH_GATE, {}),
    CONCORD_NORTH_BRIDGE.id: (CONCORD_NORTH_BRIDGE, _named(CONCORD_VARIANTS)),
    PEGASUS_BRIDGE.id: (PEGASUS_BRIDGE, _named(PEGASUS_VARIANTS, RANGE_SENSITIVITY, CROSSED_SENSITIVITY)),
    HILL_223_PATROL.id: (HILL_223_PATROL, _named(HILL_VARIANTS)),
    GERGOVIA_RECALL.id: (GERGOVIA_RECALL, _named(GERGOVIA_VARIANTS)),
}


class GameFailed(Exception):
    """A game that is not a usable, fully costed model game."""


def resolve(item):
    """The scenario entry for plan item ``ENTRY`` or ``ENTRY/VARIANT``; an
    unknown name raises ValueError before any game starts."""
    name, _, variant = item.partition("/")
    if name not in CATALOG:
        raise ValueError(f"Unknown entry {name!r}; known: {', '.join(CATALOG)}")
    entry, variants = CATALOG[name]
    if not variant:
        return entry
    if variant not in variants:
        raise ValueError(f"Unknown variant {variant!r} of {name}; known: {', '.join(variants) or 'none'}")
    return variants[variant]


def decision_cost(decision):
    """Why: the cap is only real if every paid call is counted.
    What: the decision's ``usage.cost`` in USD. A missing, non-numeric,
    negative or non-finite cost raises ``GameFailed``; it is never read as 0.
    Test: `test_missing_cost_fails_closed_and_stops_the_batch`.
    """
    usage = decision.get("usage")
    cost = usage.get("cost") if isinstance(usage, dict) else None
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        raise GameFailed(f"cost unreadable for the player decision at turn {decision.get('turn')}")
    return float(cost)


def model_game_failure(summary):
    """Why: a finished run can still be no model result.
    What: the reason ``summary`` (``HeadlessRunner.run``'s) is not a usable
    model game: replay not ``identical``, any fallback, or any player decision
    the model did not make. None when it is one.
    Test: `test_finished_game_with_a_fallback_is_not_a_model_game`.
    """
    if summary["replay"].get("status") != "identical":
        return f"replay {summary['replay'].get('status')}"
    counts = summary["player_decisions"]
    if counts["fallback"]:
        return f"{counts['fallback']} fallback decision(s)"
    if counts["model"] != counts["total"]:
        return f"{counts['total'] - counts['model']} non-model decision(s)"
    return None


def play(entry, db, *, provider, model, effort):
    """One model game of ``entry`` in ``db``. Returns ``(record, cost)``;
    ``cost`` is None when some paid call has no readable cost."""
    runner = build_headless(
        db, player_provider="openrouter", provider=provider, model=model, effort=effort,
        scenario_id=entry.id, scenarios=ScenarioRegistry([entry]), keyframe_every=0,
        abort_on_fallback=True,
    )
    record = {"entry": entry.id, "variant": entry.variant, "db": str(db), "status": "failed"}
    aborted, summary = None, None
    try:
        summary = runner.run()
    except ModelFallback as exc:
        aborted = exc.decision
        record["reason"] = f"fallback: {aborted.get('fallback_stage')} {aborted.get('fallback_reason')}"
    except Exception as exc:  # noqa: BLE001 - any error fails the game and stops the batch.
        record["reason"] = f"error: {type(exc).__name__}: {str(exc)[:200]}"
    game_id = summary["game_id"] if summary else runner.repository.latest()
    state = runner.repository.load(game_id) if game_id else {"decisions": []}
    paid = [d for d in state["decisions"] if d.get("side") == runner.player_side]
    paid += [aborted] if aborted else []
    cost = 0.0
    try:
        for decision in paid:
            cost += decision_cost(decision)
    except GameFailed as exc:
        cost = None
        record.setdefault("reason", str(exc))
    record.update(decisions=len(paid), cost_usd=cost)
    if summary is not None:
        record.update(winner=summary["winner"], turns=summary["turns"], replay=summary["replay"]["status"],
                      player_decisions=summary["player_decisions"])
        failure = model_game_failure(summary)
        if failure:
            record.setdefault("reason", failure)
    if "reason" not in record:
        record["status"] = "model_game"
    return record, cost


def run_batch(plan, games, cap_usd, directory, *, model=None, effort=None, provider_for=None, out=print):
    """Why: a paid batch must stop on its cap and on the first unusable game.
    What: plays each plan item ``games`` times in order, adding each game's
    cost to a running total, and returns ``(exit_code, summary)``. It starts
    no game once the total reaches ``cap_usd`` (``EXIT_CAP``); a failed game
    stops it (``EXIT_FAILED``). ``provider_for(entry)`` gives the provider
    (None: the OpenRouter adapter from ``Settings``).
    Test: `test_batch_stops_at_the_cost_cap`,
    `test_missing_cost_fails_closed_and_stops_the_batch`,
    `test_provider_error_or_junk_reply_fails_the_game_and_stops_the_batch`,
    `test_model_runs_on_four_entries_replay_with_no_fallbacks`.
    """
    if games < 1 or not (cap_usd > 0 and math.isfinite(cap_usd)):
        raise ValueError("games must be 1 or more and the cap a positive amount")
    entries = [(item, resolve(item)) for item in plan]  # Every name is checked before any spend.
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.glob("*.sqlite")):
        raise ValueError(f"{directory} already holds games; use a new directory per batch")
    total, played, status, code = 0.0, [], "complete", EXIT_DONE
    queue = [(item, entry, n) for item, entry in entries for n in range(1, games + 1)]
    for item, entry, n in queue:
        if total >= cap_usd:
            status, code = "cap_reached", EXIT_CAP
            break
        db = directory / f"{item.replace('/', '--')}-{n}.sqlite"
        provider = provider_for(entry) if provider_for else None
        record, cost = play(entry, db, provider=provider, model=model, effort=effort)
        record.update(plan_item=item, game=n)
        if record["status"] != "model_game" and db.exists():
            # Kept for audit, under a name no comparison reads as a model game.
            record["db"] = str(db.rename(db.with_suffix(".failed.sqlite")))
        played.append(record)
        out(json.dumps(record, sort_keys=True), flush=True)
        if cost is None:
            status, code = "failed", EXIT_FAILED
            break
        total += cost
        if record["status"] != "model_game":
            status, code = "failed", EXIT_FAILED
            break
    if status == "complete" and total >= cap_usd:
        status, code = "cap_reached", EXIT_CAP  # The last game reached the cap.
    summary = {
        "status": status, "exit": code, "cap_usd": cap_usd,
        # Spend is a floor when a failed game has a call with no readable cost.
        "spent_usd": round(total, 6), "spend_complete": all(r["cost_usd"] is not None for r in played),
        "planned": len(queue), "played": len(played),
        "model_games": sum(1 for r in played if r["status"] == "model_game"),
        "not_started": len(queue) - len(played),
        "failed": [{k: r[k] for k in ("plan_item", "game", "reason", "db")}
                   for r in played if r["status"] != "model_game"],
    }
    (directory / "batch-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    out(json.dumps({"summary": summary}, sort_keys=True), flush=True)
    return code, summary


def main(argv=None, provider_for=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--plan", action="append", required=True, metavar="ENTRY[/VARIANT]")
    parser.add_argument("--model", required=True, help="OpenRouter model id")
    parser.add_argument("--effort", choices=EFFORTS[1:])
    parser.add_argument("--games", type=int, required=True, help="model games per plan item")
    parser.add_argument("--cap-usd", type=float, required=True, help="stop starting games at this spend")
    parser.add_argument("--dir", required=True, help="a new directory for this batch's databases")
    args = parser.parse_args(argv)
    try:
        code, _ = run_batch(args.plan, args.games, args.cap_usd, args.dir, model=args.model,
                            effort=args.effort, provider_for=provider_for)
    except ValueError as exc:
        parser.error(str(exc))
    return code


if __name__ == "__main__":
    sys.exit(main())
