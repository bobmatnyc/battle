"""Battle command service: session ownership, ordering, inference cadence and commit.

The repository owns the transaction. All changes are computed before a single
compare-and-swap save; this service never writes events or units independently.
"""

import threading
from ..command_policy import scripted_policy
from ..contracts import (
    BattleRepository,
    ClockFactory,
    Commander,
    Conflict,
    ScenarioCatalog,
    Simulation,
    UnknownScenario,
)
from .queries import BattleQueries


class BattleService:
    def __init__(
        self,
        repository: BattleRepository,
        simulation: Simulation,
        commander: Commander,
        scenarios: ScenarioCatalog,
        queries: BattleQueries,
        clock_factory: ClockFactory,
        *,
        mode="scripted",
        scenario_id=None,
    ):
        self.repository = repository
        self.simulation = simulation
        self.commander = commander
        self.scenarios = scenarios
        self.queries = queries
        self.mode = mode
        # Scenario for new games unless a request names one; unknown ids fail here.
        self.scenario_id = scenarios.resolve(scenario_id).id
        self.lock = threading.Lock()
        self.game_id = repository.latest() or repository.create(
            scenarios.create(self.scenario_id)
        )
        self.clock = clock_factory(self.clock_step, audit=self._audit_clock)

    def _audit_clock(self, command, speed):
        self.repository.clock_event(self.game_id, command, speed)

    def _advance(self, state):
        if state["status"] != "active":
            raise ValueError("Battle complete. Start a new battle.")
        # The computer commands the stored opponent of the player's side.
        decision = None
        if state["turn"] % 3 == 0:
            side = self.simulation.computer_side(state)
            mode, policy = self._opponent_control(state, side)
            if policy is None:
                decision = self.commander.decide(state, side, mode=mode)
            else:
                decision = self.commander.decide(state, side, mode=mode, policy=policy)
        return self._commit(state, {"type": "advance", "decision": decision})

    def _opponent_control(self, state, side):
        """Why: an entry's scripted control is its playable opponent; the desk's
        plain fallback control does not play Concord's guard (docs/research/74).
        What: ``(mode, policy)`` for the computer side's decision. An entry with
        ``desk_scripted_opponent`` gets ``("scripted", its scripted policy)``,
        the call the headless runner makes, in either commander mode, so no
        provider is asked. Any other entry, or a label this catalog does not
        know, gets ``(self.mode, None)``: the call made before this change.
        Default ruling bt-D08 (pending the owner): only newly player-facing
        entries opt in; Little Round Top and Hougoumont do not.
        Test: `test_concord_desk_opponent_plays_the_regulars_policy_as_headless_does`,
        `test_concord_desk_opponent_stays_scripted_in_openrouter_mode_without_a_provider_call`,
        `test_little_round_top_and_hougoumont_keep_the_plain_desk_opponent`.
        """
        try:
            entry = self.scenarios.for_state(state)
        except UnknownScenario:
            return self.mode, None
        if not entry.desk_scripted_opponent:
            return self.mode, None
        return "scripted", scripted_policy(entry, side)

    def _commit(self, state, action):
        updated = self.simulation.apply(state, action)
        self.repository.save(self.game_id, updated, state["revision"])
        return updated

    def clock_step(self):
        with self.lock:
            state = self.repository.load(self.game_id)
            if state["status"] != "active":
                return False
            return self._advance(state)["status"] == "active"

    def clock_control(self, game_id, command, speed=None):
        if game_id != self.game_id:
            raise Conflict("Battle changed. Refresh the command map.")
        # Pause bypasses the simulation lock even while a provider call is in flight.
        if command in ("pause", "speed"):
            self.clock.control(command, speed)
        elif command == "start":
            with self.lock:
                if game_id != self.game_id:
                    raise Conflict("Battle changed.")
                if self.repository.load(self.game_id)["status"] != "active":
                    raise ValueError(
                        "Battle complete. Use replay or start a new battle."
                    )
                self.clock.control(command)
        else:
            raise ValueError("Unknown clock command.")
        return self.state()

    def state(self, god=False):
        # Capture identity once so a concurrent reset cannot mix two games' data.
        game_id = self.game_id
        state = self.repository.load(game_id)
        result = self.queries.project(state, god=god)
        result.update(
            clock=self.clock.status(),
            game_id=game_id,
            mode=self.mode,
            model=self.commander.model,
            inference_available=self.commander.available,
            messages=self.repository.messages(game_id),
        )
        last = [d for d in state["decisions"] if d.get("role") != "staff"]
        result["last_commander_source"] = last[-1]["source"] if last else None
        result["last_fallback_reason"] = (
            last[-1].get("fallback_reason") if last else None
        )
        return result

    def map(self):
        """Why: the command desk must draw the current game's own terrain.
        What: the map of the catalog entry owning the current game's snapshot
        label. A label this catalog does not know (a save from another catalog)
        gets the default scenario's map, as before scenarios were entries,
        rather than an error. Display only; no rule or prompt reads it.
        Test: `test_scripted_paths_and_map_survive_an_unmapped_label`.
        """
        state = self.repository.load(self.game_id)
        try:
            scenario_id = self.scenarios.for_state(state).id
        except UnknownScenario:
            scenario_id = None
        return self.scenarios.map(scenario_id)

    def scenario_list(self):
        """Why: the command desk offers a scenario choice for a new game.
        What: the catalog's scenarios (id, title, location, date) and the id
        new games use when a request names none. Read-only; no battle state.
        Test: `test_scenario_list_names_the_catalog_and_default`.
        """
        entries = [self.scenarios.resolve(i) for i in self.scenarios.ids()]
        return {
            "default": self.scenario_id,
            "scenarios": [
                {"id": e.id, "title": e.title, "location": e.location, "date": e.date}
                for e in entries
            ],
        }

    def _ensure_paused(self):
        clock = self.clock.status()
        if clock["running"] or clock["inflight"]:
            raise Conflict(
                "Pause the clock and let the current interval finish before issuing commands."
            )

    def execute(self, command, payload, *, game_id, revision):
        """Why: application commands have no URL, HTTP request, database or
        provider schema.
        What: runs ``command`` against the current game at ``revision``.
        ``new`` uses the service's scenario only when ``scenario`` is absent
        or None; any other value must be a known id, else ``UnknownScenario``
        (HTTP 400) and the current game is kept.
        Test: `test_new_game_refuses_falsy_scenario_ids`.
        """
        self._ensure_paused()  # Reject promptly during an outstanding provider call.
        with self.lock:
            self._ensure_paused()  # Recheck after acquiring the serialization lock.
            state = self.repository.load(self.game_id)
            if game_id != self.game_id or revision != state["revision"]:
                raise Conflict("Battle changed. Refresh before issuing another order.")
            if command == "new":
                # Only an absent or null id means the default; "", 0, [] and {}
                # are unknown ids. Resolve before creating, so they change nothing.
                scenario_id = payload.get("scenario")
                scenario = self.scenarios.create(
                    self.scenario_id if scenario_id is None else scenario_id
                )
                self.game_id = self.repository.create(scenario)
                self.clock.control("reset")
            elif command == "mode":
                if payload.get("mode") not in ("scripted", "openrouter"):
                    raise ValueError("Unknown commander mode.")
                self.mode = payload["mode"]
            elif command == "advance":
                self._advance(state)
            else:
                self._commit(state, self._action(state, command, payload))
            return self.state()

    def _action(self, state, command, payload):
        if command == "orders":
            orders = payload.get("orders")
            if not isinstance(orders, list) or not 1 <= len(orders) <= 3:
                raise ValueError("Issue one to three orders.")
            self.simulation.validate_orders(state, self.simulation.player_side(state), orders)
            return {"type": "orders", "orders": orders}
        if command in ("standing", "formation"):
            return {"type": command, "instruction": payload.get("instruction")}
        if command == "recommendation":
            return {
                "type": command,
                "recommendation_id": payload.get("recommendation_id"),
                "response": payload.get("response"),
            }
        if command == "chat":
            text = payload.get("text", "")
            if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                raise ValueError("Enter a message of 1–2000 characters.")
            decision = self.commander.chat(state, text, mode=self.mode)
            decision.update(
                role="staff",
                turn=state["turn"],
                request=text,
                observation=self.simulation.observation(
                    state, self.simulation.player_side(state)
                ),
            )
            return {"type": "chat", "decision": decision}
        raise ValueError("Unknown action.")

    def start(self):
        self.clock.start_worker()

    def close(self):
        self.clock.close()
