"""Run a batch of model games under a spend cap (docs/research/69 §9).

Why: the headless runner has no spend limit, and a provider failure turns a
decision into a scripted fallback while the run goes on (doc 69 §5, §8 gaps 1,
3 and 4). A paid batch needs a driver that stops on spend and on any fallback,
keeps the evidence of a failed game, and pins what it ran.
What: ``--plan ENTRY[/VARIANT]`` (repeatable) names the games; each plan item
plays ``--games N`` model games, in plan order, one model side (the entry's
player) against the entry's scripted control, each in its own ``BatchStore``
database under ``--dir``. Guards, all fail-closed:

- source: a dirty git tree is refused; the manifest pins the commit;
- budget: before every model call the cap must cover the batch's spend plus
  one worst-case call (``battle.spend.RESERVE_BASIS``), so an overrun is
  bounded by one call; the game stops before the call (``*.stopped.sqlite``,
  exit 3), and no game starts once the spend reaches the cap (exit 3);
- fallback: the runner aborts at the first player decision that fell back,
  before it is stored, and a finished game is checked again; the game is
  failed (``*.failed.sqlite``, exit 4);
- cost: a player decision with no readable ``usage.cost`` fails the game
  (exit 4); it is never counted as $0;
- replay: a game whose replay is not ``identical`` fails (exit 4).

``--dir`` must hold no earlier batch; nothing is deleted or overwritten.
``manifest.json`` (written before the first game) pins the commit, rules
editions, each side's prompt version and prompt hash, the scripted controls,
the action-set label (doc 69 §10), model, prices, cap and plan. Every game is
a line of ``runs.jsonl`` carrying the same pins, its cost, and for a stopped
or failed game the turn, decision index, reason, database path and sha256.
``batch-summary.json`` closes the batch and lists those records. Exit 0 means
every planned game finished as a model game within the cap.
Usage, from apps/poc: ``python3 scripts/model_runs.py --plan pegasus-bridge
--plan gergovia-recall/recall-audible --model anthropic/claude-sonnet-5.5
--effort high --games 2 --cap-usd 4 --dir artifacts/<batch>``. It reads the
OpenRouter key through ``Settings``, as ``python3 -m battle --headless`` does.
Test: `tests/test_model_runs.py`.
"""

import argparse
import hashlib
import json
import re
import signal
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

POC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(POC))

from battle.adapters.openrouter import request_body  # noqa: E402
from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless  # noqa: E402
from battle.command_policy import (  # noqa: E402
    ASSAULT_STANDING, GATE_ATTACKER_POLICY, GATE_DEFENDER_POLICY, GATE_STANDING, scripted_policy, system_prompt,
)
from battle.config import EFFORTS, Settings  # noqa: E402
from battle.scenario import LITTLE_ROUND_TOP  # noqa: E402
from battle.scenario_concord import CONCORD_NORTH_BRIDGE, VARIANTS as CONCORD_VARIANTS  # noqa: E402
from battle.scenario_gergovia import GERGOVIA_RECALL, VARIANTS as GERGOVIA_VARIANTS  # noqa: E402
from battle.scenario_hill223 import HILL_223_PATROL, VARIANTS as HILL_VARIANTS  # noqa: E402
from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE  # noqa: E402
from battle.scenario_pegasus import (  # noqa: E402
    CROSSED_SENSITIVITY, PEGASUS_BRIDGE, RANGE_SENSITIVITY, VARIANTS as PEGASUS_VARIANTS,
)
from battle.services.headless import ModelFallback  # noqa: E402
from battle.spend import (  # noqa: E402
    PRICES, RESERVE_BASIS, BudgetExhausted, CostUnreadable, Price, SpendGuard, decision_cost,
)

EXIT_DONE, EXIT_CAP, EXIT_FAILED = 0, 3, 4
# Files a batch writes; a directory holding any of them already holds a batch.
BATCH_FILES = ("manifest.json", "runs.jsonl", "batch-summary.json")


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
# Doc 69 §10: actions a scripted control issues that the model reply (orders
# only) cannot. Only the gate controls issue standing instructions.
CONTROL_ONLY_ACTIONS = {
    GATE_DEFENDER_POLICY: (f"standing instruction {GATE_STANDING}",),
    GATE_ATTACKER_POLICY: (f"standing instruction {ASSAULT_STANDING}",),
}


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


def source_pin(repo):
    """Why: a paid result must name the exact code that produced it.
    What: ``{"commit", "clean": True}`` for the git checkout at ``repo``. A
    dirty tree (any tracked change or untracked, unignored file) or a failed
    git call raises ValueError.
    Test: `test_dirty_tree_is_refused_and_pins_appear`.
    """
    def git(*args):
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
        if done.returncode:
            raise ValueError(f"git {args[0]} failed in {repo}: {done.stderr.strip()[:200]}")
        return done.stdout.strip()

    commit = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise ValueError(f"source tree {repo} is dirty; commit first, so the batch can name its code")
    return {"commit": commit, "clean": True}


def _version(policy):
    found = re.search(r"-(v\d+)$", policy)
    return found.group(1) if found else None


def action_set(entry, side):
    """Why: a model-vs-control comparison is unequal where the control has
    actions the model reply lacks (doc 69 §8 gap 5, §10).
    What: the scripted control of ``side``, ``symmetric``, and the actions
    only the control can issue.
    Test: `test_hougoumont_is_labelled_asymmetric_and_pegasus_symmetric`.
    """
    control = scripted_policy(entry, side)
    only = list(CONTROL_ONLY_ACTIONS.get(control, ()))
    return {"control": control, "symmetric": not only, "control_only": only}


def entry_pins(entry):
    """The pins of one entry: rules edition, each side's prompt version,
    prompt sha256 and scripted control with its version, and the model side's
    action-set label."""
    sides = {
        side: {
            "prompt_version": entry.prompt_version,
            "prompt_sha256": hashlib.sha256(system_prompt(side, entry).encode()).hexdigest(),
            "control": scripted_policy(entry, side),
            "control_version": _version(scripted_policy(entry, side)),
        }
        for side in entry.sides
    }
    return {"entry": entry.id, "variant": entry.variant, "rules": entry.rules, "player_side": entry.player,
            "sides": sides, "action_set": action_set(entry, entry.player)}


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


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def play(entry, stem, guard, *, provider, settings):
    """Why: a game must never sit under a model-game name unless it is one.
    What: plays one model game of ``entry`` in ``<stem>.partial.sqlite``,
    charged to ``guard``, and returns ``(record, interrupt)``. Only a
    ``model_game`` is renamed ``<stem>.sqlite``; a ``stopped`` (budget) or
    ``failed`` game becomes ``<stem>.stopped.sqlite`` or ``.failed.sqlite``.
    A BaseException (KeyboardInterrupt, SystemExit from SIGTERM) fails the
    game and is returned as ``interrupt`` for the caller to record and
    re-raise. A process killed outright leaves only ``.partial.sqlite``.
    Test: `test_interrupt_mid_game_records_the_game_and_propagates`.
    """
    db = stem.with_name(stem.name + ".partial.sqlite")
    runner = build_headless(
        db, player_provider="openrouter", provider=provider, settings=settings,
        scenario_id=entry.id, scenarios=ScenarioRegistry([entry]), keyframe_every=0,
        abort_on_fallback=True, spend_guard=guard,
    )
    record = {"entry": entry.id, "variant": entry.variant, "model": runner.commander.model, "status": "failed"}
    before, cost_complete, aborted, summary, interrupt = guard.spent_usd, True, None, None, None
    try:
        summary = runner.run()
    except ModelFallback as exc:
        aborted = exc.decision
        record["reason"] = f"fallback: {aborted.get('fallback_stage')} {aborted.get('fallback_reason')}"
        try:
            guard.charge(decision_cost(aborted))  # A paid failure still counts.
        except CostUnreadable:
            cost_complete = False
    except BudgetExhausted as exc:
        record.update(status="stopped", reason=f"budget: {exc}")
    except CostUnreadable as exc:
        cost_complete, record["reason"] = False, str(exc)
    except Exception as exc:  # noqa: BLE001 - any error fails the game and stops the batch.
        record["reason"] = f"error: {type(exc).__name__}: {str(exc)[:200]}"
    except BaseException as exc:  # Recorded, renamed, then re-raised by the caller.
        interrupt, record["reason"] = exc, f"interrupted: {type(exc).__name__}"
        cost_complete = False  # An interrupted call may be billed without being charged.
    game_id = summary["game_id"] if summary else runner.repository.latest()
    state = runner.repository.load(game_id) if game_id else {"decisions": [], "turn": None}
    committed = sum(1 for d in state["decisions"] if d.get("side") == runner.player_side)
    record.update(decisions=committed + (1 if aborted else 0), cost_usd=round(guard.spent_usd - before, 6),
                  cost_complete=cost_complete)
    if summary is not None:
        record.update(winner=summary["winner"], turns=summary["turns"], replay=summary["replay"]["status"],
                      player_decisions=summary["player_decisions"])
        failure = model_game_failure(summary)
        if failure:
            record["reason"] = failure
    if "reason" not in record:
        record["status"] = "model_game"
        final = db.rename(stem.with_name(stem.name + ".sqlite"))
        record.update(db=str(final), db_sha256=_sha256(final))
        return record, None
    # Where it stopped: the turn and the 0-based index of the player decision.
    record.update(turn=aborted["turn"] if aborted else state.get("turn"), decision_index=committed)
    if db.exists():
        # Kept for audit, under a name no comparison reads as a model game.
        db = db.rename(stem.with_name(f"{stem.name}.{record['status']}.sqlite"))
        record.update(db=str(db), db_sha256=_sha256(db))
    else:
        record.update(db=None, db_sha256=None)
    return record, interrupt


def request_size(settings):
    """The byte length of the body the OpenRouter adapter sends for a request
    under ``settings`` (``request_body``), as ``SpendGuard`` needs it.
    Test: `test_reserve_covers_the_full_request_body_the_adapter_sends`."""
    return lambda instruction, payload: len(request_body(settings, instruction, payload))


def run_batch(plan, games, cap_usd, directory, *, price, source, settings=None, provider_for=None, out=print):
    """Why: a paid batch must stop on its cap and on the first unusable game.
    What: plays each plan item ``games`` times in order under one
    ``SpendGuard`` and returns ``(exit_code, summary)``. ``source`` is the
    ``source_pin``, ``price`` the ``battle.spend.Price`` and ``settings`` the
    one resolved ``Settings`` (``resolve_settings``) that sizes the reserve,
    builds the provider and fills the pins; its output limit must equal the
    price's. A budget stop or a spend at the cap gives ``EXIT_CAP``; a failed
    game ``EXIT_FAILED``; an interrupt is recorded and re-raised.
    ``provider_for(entry)`` gives the provider (None: the OpenRouter adapter
    from ``settings``, which is then required).
    Test: `test_batch_stops_at_the_cost_cap`,
    `test_budget_stops_mid_game_before_the_call_that_would_cross_the_cap`,
    `test_missing_cost_fails_closed_and_stops_the_batch`,
    `test_provider_error_or_junk_reply_fails_the_game_and_stops_the_batch`,
    `test_fallback_keeps_the_partial_run_and_its_record`,
    `test_interrupt_mid_game_records_the_game_and_propagates`,
    `test_model_runs_on_four_entries_replay_with_no_fallbacks`.
    """
    if games < 1:
        raise ValueError("games must be 1 or more")
    if settings is None:
        if provider_for is None:
            raise ValueError("a batch on the OpenRouter adapter needs the resolved Settings")
        settings = Settings(max_tokens=price.max_output_tokens)  # Fake providers only.
    if price.max_output_tokens != settings.request_max_tokens:
        raise ValueError("the price's output limit is not the request's max_tokens")
    guard = SpendGuard(cap_usd, price, request_size(settings))
    entries = [(item, resolve(item)) for item in plan]  # Every name is checked before any spend.
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.glob("*.sqlite")) or any((directory / name).exists() for name in BATCH_FILES):
        raise ValueError(f"{directory} already holds a batch; use a new directory")
    pins = {"source": source, "model": settings.model, "effort": settings.effort or None,
            "request_max_tokens": settings.request_max_tokens, "request_timeout": settings.request_timeout,
            "cap_usd": cap_usd,
            "prices": {"input_per_mtok": price.input_per_mtok, "output_per_mtok": price.output_per_mtok,
                       "max_output_tokens": price.max_output_tokens, "reserve_basis": RESERVE_BASIS}}
    manifest = {**pins, "plan": list(plan), "games_per_item": games,
                "entries": {item: entry_pins(entry) for item, entry in entries}}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    played, status, code, interrupt = [], "complete", EXIT_DONE, None
    queue = [(item, entry, n) for item, entry in entries for n in range(1, games + 1)]
    for item, entry, n in queue:
        if guard.spent_usd >= cap_usd:
            status, code = "cap_reached", EXIT_CAP
            break
        stem = directory / f"{item.replace('/', '--')}-{n}"
        provider = provider_for(entry) if provider_for else None
        record, interrupt = play(entry, stem, guard, provider=provider, settings=settings)
        record.update(plan_item=item, game=n, pins={**pins, **manifest["entries"][item]})
        played.append(record)
        with open(directory / "runs.jsonl", "a") as runs:
            runs.write(json.dumps(record, sort_keys=True) + "\n")
        out(json.dumps(record, sort_keys=True), flush=True)
        if interrupt is not None:
            status, code = "interrupted", EXIT_FAILED
            break
        if record["status"] == "stopped":
            status, code = "cap_reached", EXIT_CAP
            break
        if record["status"] != "model_game":
            status, code = "failed", EXIT_FAILED
            break
    if status == "complete" and guard.spent_usd >= cap_usd:
        status, code = "cap_reached", EXIT_CAP  # The last game reached the cap.
    summary = {
        "status": status, "exit": code, "cap_usd": cap_usd, "source": source,
        # Spend is a floor when a failed game has a call with no readable cost.
        "spent_usd": round(guard.spent_usd, 6), "spend_complete": all(r["cost_complete"] for r in played),
        "planned": len(queue), "played": len(played),
        "model_games": sum(1 for r in played if r["status"] == "model_game"),
        "not_started": len(queue) - len(played),
        "stopped_or_failed": [{k: v for k, v in r.items() if k != "pins"}
                              for r in played if r["status"] != "model_game"],
    }
    (directory / "batch-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    out(json.dumps({"summary": summary}, sort_keys=True), flush=True)
    if interrupt is not None:
        raise interrupt
    return code, summary


def resolve_settings(model=None, effort=None, max_tokens=None, timeout=None, env_file=None):
    """Why: the reserve, the request and the pins must use the same limits.
    What: ``Settings.load`` (environment, then ``env_file``, default
    ``apps/poc/.env.local``) with the given CLI overrides applied once, as
    ``build_headless`` would. The key it may hold is never printed or pinned.
    Test: `test_reserve_and_pins_use_the_environment_settings`.
    """
    loaded = Settings.load() if env_file is None else Settings.load(Path(env_file))
    overrides = {"model": model, "effort": effort, "max_tokens": max_tokens, "timeout": timeout}
    return replace(loaded, **{k: v for k, v in overrides.items() if v is not None})


def price_for(settings, input_price=None, output_price=None):
    """The ``Price`` of ``settings.model``: ``PRICES`` unless both rates are
    given; an unpriced model raises ValueError. The output limit is the
    request's ``settings.request_max_tokens``."""
    if (input_price is None) != (output_price is None):
        raise ValueError("give both --input-price and --output-price, or neither")
    if input_price is None:
        if settings.model not in PRICES:
            raise ValueError(f"No price for {settings.model!r}; give --input-price and --output-price")
        input_price, output_price = PRICES[settings.model]
    return Price(input_price, output_price, settings.request_max_tokens)


def _terminate(signum, frame):
    raise SystemExit(128 + signum)  # SIGTERM becomes an interrupt that play records.


def main(argv=None, provider_for=None, repo=POC, env_file=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--plan", action="append", required=True, metavar="ENTRY[/VARIANT]")
    parser.add_argument("--model", required=True, help="OpenRouter model id")
    parser.add_argument("--effort", choices=EFFORTS[1:], help="reasoning effort (default: Settings)")
    parser.add_argument("--max-tokens", type=int, help="completion token limit (default: Settings)")
    parser.add_argument("--timeout", type=float, help="provider timeout, seconds (default: Settings)")
    parser.add_argument("--input-price", type=float, help="USD per million input tokens (default: PRICES)")
    parser.add_argument("--output-price", type=float, help="USD per million output tokens (default: PRICES)")
    parser.add_argument("--games", type=int, required=True, help="model games per plan item")
    parser.add_argument("--cap-usd", type=float, required=True, help="the batch's spend limit")
    parser.add_argument("--dir", required=True, help="a new directory for this batch's databases")
    args = parser.parse_args(argv)
    try:
        source = source_pin(repo)
        settings = resolve_settings(args.model, args.effort, args.max_tokens, args.timeout, env_file)
        price = price_for(settings, args.input_price, args.output_price)
    except ValueError as exc:
        parser.error(str(exc))
    previous = signal.signal(signal.SIGTERM, _terminate)
    try:
        code, _ = run_batch(args.plan, args.games, args.cap_usd, args.dir, price=price, source=source,
                            settings=settings, provider_for=provider_for)
    except ValueError as exc:
        parser.error(str(exc))
    finally:
        signal.signal(signal.SIGTERM, previous)
    return code


if __name__ == "__main__":
    sys.exit(main())
