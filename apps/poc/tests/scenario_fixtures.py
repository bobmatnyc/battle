"""Synthetic scenario entries for tests only; never in the player-facing catalog."""

from battle.grid import COLS, METRES_PER_HEX, ROWS, key
from battle.scenario_entry import (
    RULES_VERSION,
    MapEntry,
    ScenarioEntry,
    SideEntry,
    UnitEntry,
    VictoryEntry,
)


def flat_terrain():
    """Open, level ground on every hex of the poc-8 grid."""
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
    labels={"poc-8": "test-duel-v1"},
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
        defender="union",
        attacker="confederate",
        deadline_turns=12,
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
