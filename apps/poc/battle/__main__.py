import argparse
from pathlib import Path
from .bootstrap import PLAYER_SCENARIOS, build_application, build_headless, build_replay
from .command_policy import GATE_ATTACKER_POLICY, GATE_DEFENDER_POLICY, SCRIPTED_POLICIES
from .config import EFFORTS
from .contracts import UnknownScenario


def main():
    parser = argparse.ArgumentParser(description="battle: Little Round Top POC")
    parser.add_argument("--port", type=int, default=8874)
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent.parent / "data/battle.sqlite"),
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use deterministic local commanders; no inference calls",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run a complete battle (scripted by default) and verify replay",
    )
    parser.add_argument(
        "--replay",
        metavar="GAME_ID",
        help="Verify all recorded transitions without inference",
    )
    parser.add_argument(
        "--scenario",
        metavar="ID",
        help=f"Scenario for new games and headless runs (default: {PLAYER_SCENARIOS[0].id}; "
        f"known: {', '.join(e.id for e in PLAYER_SCENARIOS)})",
    )
    headless = parser.add_argument_group(
        "headless player run", "Used with --headless; defaults reproduce the scripted run"
    )
    headless.add_argument(
        "--player-side",
        metavar="SIDE",
        help="Side id the player provider commands (default: the scenario's player side, "
        "union for Little Round Top)",
    )
    headless.add_argument(
        "--player-provider",
        choices=["scripted", "openrouter"],
        default="scripted",
        help="Who commands the player side; the other side is the scripted control",
    )
    headless.add_argument(
        "--opponent",
        choices=list(SCRIPTED_POLICIES),
        default=None,
        help="Scripted control for the opposing side (default: the scenario's choice; "
        "recorded in run metadata)",
    )
    headless.add_argument(
        "--player-policy",
        choices=list(SCRIPTED_POLICIES),
        help="Scripted control for a scripted player side (default: the scenario's choice, "
        f"{GATE_DEFENDER_POLICY} for the defender and {GATE_ATTACKER_POLICY} for the "
        "attacker of a gated scenario)",
    )
    headless.add_argument("--model", help="OpenRouter model id (default: Settings)")
    headless.add_argument(
        "--effort",
        choices=[e for e in EFFORTS if e],
        help="Reasoning effort sent in the request body (default: none)",
    )
    headless.add_argument("--max-tokens", type=int, help="Completion token limit")
    headless.add_argument("--timeout", type=float, help="Provider timeout, seconds")
    args = parser.parse_args()
    provider_flags = (args.model, args.effort, args.max_tokens, args.timeout)
    if args.player_provider == "scripted" and any(
        flag is not None for flag in provider_flags
    ):
        parser.error("--model/--effort/--max-tokens/--timeout need --player-provider openrouter")
    if args.replay:
        print(build_replay(args.db).verify(args.replay))
    elif args.headless:
        try:
            runner = build_headless(
                args.db,
                player_side=args.player_side,
                player_provider=args.player_provider,
                opponent=args.opponent,
                model=args.model,
                effort=args.effort,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
                scenario_id=args.scenario,
                player_policy=args.player_policy,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(runner.run())
    else:
        from .server import serve_application

        try:
            service = build_application(
                args.db, offline=args.offline, scenario_id=args.scenario
            )
        except UnknownScenario as exc:
            parser.error(str(exc))
        serve_application(service, args.port)


if __name__ == "__main__":
    main()
