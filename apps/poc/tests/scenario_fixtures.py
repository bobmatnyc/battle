"""Synthetic scenario entries for tests only; never in the player-facing catalog."""

import dataclasses

from battle.grid import COLS, METRES_PER_HEX, ROWS, key
from battle.scenario_entry import (
    GATE_ORDER_CATALOG,
    RULES_VERSION,
    GateEntry,
    GatewayPushEntry,
    MapEntry,
    ScenarioEntry,
    SideEntry,
    SupplyEntry,
    UnitEntry,
    VictoryEntry,
)


def flat_terrain():
    """Open, level ground on every hex of the grid."""
    return {
        key([c, r]): {
            "pos": [c, r],
            "elevation": 150,
            "terrain": "open",
            "move_cost": 100,
            "cover": 10,
        }
        for r in range(ROWS)
        for c in range(COLS)
    }


# Two 40-person detachments a few hexes apart; each is its side's command unit.
DUEL = ScenarioEntry(
    id="test-duel",
    title="Test duel",
    variant="flat",
    rules=RULES_VERSION,
    prompt_version="test-duel-v1",
    prompt_setting="Test Duel, 1863",
    labels={"poc-8": "test-duel-v1", "poc-9": "test-duel-v2", "poc-10": "test-duel-v3", "poc-11": "test-duel-v4"},
    location="Synthetic test ground",
    date="1863-07-01",
    start_time="09:00:00",
    time_basis="Synthetic fixture time",
    seconds_per_turn=30,
    weather={"season": "summer", "conditions": "fixture"},
    sides={
        "union": SideEntry(
            name="Blue",
            role="defender",
            command_unit="B1",
            headquarters=(6, 3),
            mission="Blue duel mission: keep the knoll until turn 12.",
            charge="keep the knoll",
        ),
        "confederate": SideEntry(
            name="Grey",
            role="attacker",
            command_unit="G1",
            headquarters=(1, 8),
            mission="Grey duel mission: take the knoll within 12 turns.",
            charge="take the knoll",
        ),
    },
    units=(
        UnitEntry("B1", "union", "Blue detachment", (5, 4)),
        UnitEntry("G1", "confederate", "Grey detachment", (2, 7), {"skill": 75}),
    ),
    victory=VictoryEntry(
        kind="hold-objective",
        objective=(4, 5),
        deadline_turns=12,
        objective_name="knoll",
    ),
    map=MapEntry(
        terrain=flat_terrain,
        features={"roads": (), "buildings": (), "works": ()},
        cols=COLS,
        rows=ROWS,
        metres_per_hex=METRES_PER_HEX,
        width=1080,
        height=840,
        source="Synthetic flat test ground",
        source_url=None,
    ),
    order_catalog=("hold", "move", "rest", "retreat", "resupply", "recon", "dig_in"),
    communications="civil-war-courier-v1",
    voice_profile="civil-war-en-v1",
)


def renamed_sides(entry, names, *, id, label):
    """``entry`` with its side ids replaced through ``names`` (old id -> new id)."""
    return dataclasses.replace(
        entry,
        id=id,
        labels={entry.rules: label},
        sides={names[side]: spec for side, spec in entry.sides.items()},
        units=tuple(dataclasses.replace(u, side=names[u.side]) for u in entry.units),
        player_side=names[entry.player],
    )


# The duel with side ids that are neither Union nor Confederate (poc-9 onward).
BLUE_GREY_DUEL = renamed_sides(
    DUEL, {"union": "blue", "confederate": "grey"}, id="test-duel-blue-grey", label="test-duel-blue-grey-v1"
)


# poc-10 gate fixture: a walled farm in a row of three hexes, back room 9,10,
# farm 10,10 and courtyard 11,10, with one gate from the courtyard to 12,10.
# The farm hex blocks sight between the back room and the courtyard.
GATE_COMPOUND = ([9, 10], [10, 10], [11, 10])
GATEWAY, GATE_OUTSIDE = [11, 10], [12, 10]
# Authored sensitivity values for tests only: closing takes 3 intervals at 20
# men, barring 2 more, forcing a closed gate 4.
TEST_GATE_LABOUR = GateEntry(close_labour=60, bar_labour=40, force_labour=80, work_cap=20)
# poc-11: a party of 20 or more carries a held gateway in 2 intervals.
TEST_GATEWAY_PUSH = GatewayPushEntry(push_labour=40, push_cap=20)


def gate_entry(state="open", positions=None, armed=(), id="test-gate", extra=()):
    """The gate fixture. ``state`` is the gate's briefed state, ``positions``
    moves units B1, G1 and G2, and only the ``armed`` unit ids keep their
    ammunition, so the others never fire. ``extra`` adds units given as
    (id, side, hex)."""
    positions = {"B1": (9, 10), "G1": (18, 4), "G2": (14, 10), **(positions or {})}
    ammo = {uid: {} if uid in armed else {"ammo": 0} for uid in positions}
    building = {
        "id": "walled-farm", "kind": "building", "name": "Walled farm", "pos": [10, 10],
        "cover": 45, "height": 8, "compound": [list(p) for p in GATE_COMPOUND],
        "openings": [{"id": "farm-gate", "name": "Farm gate", "inside": GATEWAY,
                      "outside": GATE_OUTSIDE, "state": state}],
    }
    blue, grey = DUEL.sides["union"], DUEL.sides["confederate"]
    return dataclasses.replace(
        DUEL,
        id=id,
        title="Test gate",
        labels={"poc-10": id + "-v1", "poc-11": id + "-v2"},
        sides={
            "blue": dataclasses.replace(blue, headquarters=(9, 10), mission="Blue gate mission: keep the walled farm."),
            "grey": dataclasses.replace(
                grey, headquarters=(18, 4), mission="Grey gate mission: take the walled farm.",
                supply=SupplyEntry("Grey ammunition point", (18, 3), 2400, "rifled muskets"),
            ),
        },
        units=(
            UnitEntry("B1", "blue", "Blue garrison", positions["B1"], ammo["B1"]),
            UnitEntry("G1", "grey", "Grey reserve", positions["G1"], ammo["G1"]),
            UnitEntry("G2", "grey", "Grey storming party", positions["G2"], ammo["G2"]),
            *(UnitEntry(uid, side, f"Extra {uid}", tuple(pos), {} if uid in armed else {"ammo": 0})
              for uid, side, pos in extra),
        ),
        victory=VictoryEntry(kind="hold-objective", objective=(10, 10), deadline_turns=20, objective_name="walled farm"),
        map=dataclasses.replace(DUEL.map, features={"roads": (), "buildings": (building,), "works": ()}),
        order_catalog=GATE_ORDER_CATALOG,
        gates=TEST_GATE_LABOUR,
        gateway_push=TEST_GATEWAY_PUSH,
    )
