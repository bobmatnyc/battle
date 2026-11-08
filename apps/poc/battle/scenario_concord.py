"""Concord North Bridge, 19 April 1775: a catalog entry and its variants (poc-13).

Why: the second of the first five selections (docs/research/37) turns on who
fires first at the bridge; doc 43 specifies it and poc-13 supplies its rules.
What: ``concord_entry`` builds one ``ScenarioEntry`` from three readings of
doc 43's open questions (which bank, the bridge planks, two or three British
companies). ``CONCORD_NORTH_BRIDGE`` takes the reading best supported by
S47-S49; ``VARIANTS`` holds each alternative with its source locator. The map
is authored and illustrative, not surveyed. Every field's basis is in the
entry's ``provenance``; the comparison with the record is docs/research/48.
Test: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`,
`test_open_questions_are_labelled_and_each_alternative_is_a_variant`.
"""
from dataclasses import dataclass, replace

from .grid import COLS, METRES_PER_HEX, ROWS, key
from .scenario_command import COLONIAL_COMMUNICATIONS, WEAPONS_1775, CommandEntry
from .scenario_entry import (
    ORDER_CATALOG, RULES_VERSION, DeskBrief, FireEntry, MapEntry, ScenarioEntry, SideBrief, SideEntry, UnitEntry,
    VictoryEntry,
)
from .presentation import COLONIAL_VOICE_PROFILE

# Authored layout, not surveyed. North is row 0. The river is column 12; the
# provincial ridge rises to the west, the town lies east (doc 43 §2, map rows).
RIVER_COL = 12
BRIDGE = (12, 10)
# An even-row hex: the bridge has three west-bank neighbours and one east-bank
# neighbour (grid.neighbors). The asymmetry is a property of the grid, not a source fact.
WEST_END, EAST_END = (11, 10), (13, 10)
TOWN = (22, 10)  # The British fall-back point "toward the town" (doc 43 §2).
SMOOTHBORE = "smoothbore muskets"  # The only class; WEAPONS_1775 has one range.
# Where the scripted militia send each company first (doc 43 §5 S1: Acton
# leads to the bridge approach, the rest follow). The hexes are authored.
APPROACH = {"P1": WEST_END, "P2": (11, 9), "P3": (11, 11), "P4": (10, 10)}
BRIDGE_MOVE_COST = 100
LIFTED_PLANKS_MOVE_COST = 300  # Authored sensitivity value for the planks variant.


def _terrain(bridge_cost):
    def terrain():
        cells = {}
        for r in range(ROWS):
            for c in range(COLS):
                # Authored relief: the ridge rises west of the river; the east bank is level.
                elevation = 36 + 2 * max(0, RIVER_COL - 1 - c) if c < RIVER_COL else 36
                cell = {"pos": [c, r], "elevation": elevation, "terrain": "open",
                        "move_cost": 100, "cover": 10,
                        "area": "provincial-ridge" if c < RIVER_COL else "town-bank"}
                if c == RIVER_COL:
                    cell.update(elevation=34, terrain="water", water=True, cover=0, area="concord-river")
                    if (c, r) == BRIDGE:
                        cell.update(crossing="bridge", move_cost=bridge_cost, area="north-bridge")
                cells[key([c, r])] = cell
        return cells
    return terrain


# Roads stop at each end of the bridge, so the bridge hex keeps its own cost.
FEATURES = {
    "roads": (
        {"id": "muster-road", "kind": "road", "name": "Road from the muster field to the North Bridge",
         "points": [[2, 10], list(WEST_END)]},
        {"id": "town-road", "kind": "road", "name": "Road from the North Bridge to the town",
         "points": [list(EAST_END), [23, 10]]},
    ),
    "buildings": (),
    "works": (),
}


def _men(n, **extra):
    """Authored aggregate strength with 40 cartridges a man, as ``unit()``."""
    return {"initial": n, "strength": n, "ammo": n * 40, "weapon_class": SMOOTHBORE, **extra}


PROVINCIAL_MISSION = (
    "You command the provincial column on the ridge west of the North Bridge over the Concord "
    "River. Your mission: advance to the bridge. Do not fire unless first fired upon; return fire "
    "when the command is given. Hold the bridge and the ground within one hex of it for 2 "
    "consecutive turns with no effective British formation there, before turn 20."
)
BRITISH_MISSION = (
    "You command the British light companies guarding the North Bridge over the Concord River. "
    "Your mission: guard the crossing until turn 20; fall back toward the town if it gives way."
)

PROVINCIALS = (
    UnitEntry("P1", "provincial", "Acton minute company · Davis", (7, 10), _men(40)),
    UnitEntry("P2", "provincial", "Provincial column · first detachment", (6, 10), _men(120)),
    UnitEntry("P3", "provincial", "Provincial column · second detachment", (5, 10), _men(120)),
    UnitEntry("P4", "provincial", "Provincial column · third detachment", (4, 10), _men(120)),
)
# Laurie's guard on the town (east) bank; B2 carries his command.
BRITISH_THREE = (
    UnitEntry("B1", "british", "Light company · bridge end", EAST_END, _men(32)),
    UnitEntry("B2", "british", "Light company · Laurie", (14, 10), _men(32)),
    UnitEntry("B3", "british", "Light company · north of the road", (13, 9), _men(32)),
)
BRITISH_TWO = (  # S49: two companies, about 90 men.
    UnitEntry("B1", "british", "Light company · bridge end", EAST_END, _men(45)),
    UnitEntry("B2", "british", "Light company · Laurie", (14, 10), _men(45)),
)
BRITISH_WEST = (  # The guard still on the provincial bank, the river at its back.
    UnitEntry("B1", "british", "Light company · bridge end", WEST_END, _men(32)),
    UnitEntry("B2", "british", "Light company · Laurie", BRIDGE, _men(32)),
    UnitEntry("B3", "british", "Light company · north of the road", (11, 9), _men(32)),
)

PROVENANCE = {
    "location": "sourced: North Bridge over the Concord River, Concord, Massachusetts (S47, S49)",
    "date": "sourced: 19 April 1775 (S47)",
    "start_time": "reconstruction: 09:25, five minutes before NPS's 09:30 fighting (S47); the minute is not sourced",
    "weather": "authored: no weather source read",
    "sides": "sourced: provincial militia under Barrett, Buttrick and Robinson against Laurie's guard (S47, S48)",
    "player_side": "authored: the fire decision is the provincial commander's (doc 43 §1)",
    "provincial.mission": "sourced: the fire instruction, Barrett's 'Do not fire unless first fired upon' "
                          "(S47); the objective clause is reconstruction (doc 43 §2)",
    "british.mission": "reconstruction: inferred from Laurie's post (doc 37 register); no order to him was read (doc 43 §1)",
    "provincial.command_unit": "reconstruction: Buttrick and Davis marched at the head (S47, S48); "
                               "that the command rides with Acton is inferred",
    "british.command_unit": "reconstruction: Laurie commanded the guard (S47); his company is authored",
    "units.provincial": "sourced: Acton about 40 (S48), about 400 in all (S47); the split into three "
                        "detachments of 120 and their names are authored",
    "units.british": "reconstruction: three companies, about 96 men (S47); S49 gives two companies, about 90 "
                     "(variant two-companies); the split into three of 32 is authored",
    "units.skill": "authored: default skill, morale and 40 cartridges a man of the POC detachment",
    "reinforcements": "authored: the two grenadier companies and the 11:00 return are left out; both arrive "
                      "after the exchange (S47) and poc-13 has no arrival schedule",
    "map": "authored: illustrative layout, not surveyed",
    "map.banks": "reconstruction: British on the town (east) bank, militia on the ridge west of it; S47, "
                 "S48 and S49 do not say which bank; S47's ridge above the bridge and warning shots into "
                 "the river put the forces on opposite banks (variant british-west-bank)",
    "map.bridge": "reconstruction: planks intact; S47 says an officer suggested lifting them and does not "
                  "confirm it (variant planks-lifted)",
    "fire": "sourced: provincials hold fire (Barrett, S47); the British fire without an order (S47). "
            "Warning shots release no one: authored, S47's three shots splashed into the river (doc 43 §6 question 5)",
    "command": "authored: two officers a company, successors in column order; S48 names no successor to Davis",
    "weapons": "authored: WEAPONS_1775, one range for every unit (assumption, docs/research/47)",
    "victory": "authored: hold the bridge, radius 1, 2 turns, deadline 20 turns (doc 43 §2); the historical "
               "outcome, the British withdrew and the militia held the bridge, is sourced (S47)",
    "communications": "authored: 1775 voice reach of 2 hexes, else runner (docs/research/47)",
    "voice_profile": "authored: 1775 prose voice; no historical order is quoted as text",
    "scripted": "reconstruction: scripted historical-order policies (battle/concord_policy.py, doc 43 §5 S1)",
    # docs/research/74: the command-desk text (``PROVINCIAL_BRIEF``, ``DESK``). Display only.
    "desk.campaign": "sourced: Concord, 19 April 1775 (S47)",
    "desk.place": "sourced: the North Bridge over the Concord River (S47, S49)",
    "desk.conditions": "authored: no weather source read; the entry's fixed April condition",
    "brief.provincial.headings": "authored: kicker, tagline and mission title are desk headings, not quotations",
    "brief.provincial.subhead": "sourced: the provincial column against the British light infantry guarding the "
                                "bridge (S47, S48); that the computer commands the British is authored (doc 43 §1)",
    "brief.provincial.mission_text": "sourced: Barrett's order not to fire unless first fired upon (S47, read through "
                                     "a summarising fetch, so the wording may be paraphrased); reconstruction: the "
                                     "command's word to fire once fired upon stands for Buttrick's order (S47, "
                                     "docs/research/50); authored: the ring, the 60 seconds and 09:35 restate the "
                                     "entry's victory (doc 43 §2)",
    "brief.provincial.win": "sourced: the British withdrew and the militia held the bridge (S47); the wording is authored",
    "brief.provincial.loss": "authored: the outcome the record does not show; no source",
}
# docs/research/74: the provincial player's desk text, in the entry's 1775 register. The
# British side has no brief: the desk shows a side's brief only to that side's player.
PROVINCIAL_BRIEF = SideBrief(
    kicker="THE NORTH BRIDGE", tagline="Advance to the bridge.",
    subhead="You command the provincial companies. The computer commands the British light companies "
            "guarding the bridge.",
    mission_title="Clear the bridge",
    mission_text=("March the column down from the ridge to the North Bridge. Colonel Barrett's order stands: "
                  "do not fire unless first fired upon. Your companies hold their fire until the regulars fire on "
                  "them; then the command may give the word to fire. Hold the bridge and the ground around it "
                  "(the dashed ring) for 60 seconds with no effective British company there, before **09:35**."),
    win="The bridge is carried.", loss="The regulars hold the bridge.")
DESK = DeskBrief(campaign="CONCORD · 19 APRIL 1775", place="North Bridge", objective_label="BRIDGE OBJECTIVE",
                 objective_key="BRIDGE", conditions="SPRING · APRIL · FIXED POC CONDITION",
                 draw="The battle ends in a draw.")
# docs/research/50: the assumptions of the command fire release (``release_by``
# ``command``), each with its source. v2 entries carry them; ``before`` drops them.
# The release is scenario-delegated, conditional commander intent acting on
# headquarters' knowledge, not an automatic historical attribution.
RELEASE_PROVENANCE = {
    "fire.release_by": "reconstruction: the scenario delegates to the provincial command the conditional intent "
                       "'open fire once fired upon', standing for Buttrick's order, 'Fire, for god's sake fire!', "
                       "given after the British volley in which Davis and Hosmer fell (S47); the command acts only "
                       "on what headquarters knows, and the mechanism is the model's, not the record's",
    "fire.release_by.commander": "reconstruction: the command rides with P1, the Acton company (S47, S48), as "
                                 "provincial.command_unit",
    "fire.release_by.timing": "authored: the order is spoken and delivered in the interval of the losses that "
                              "trigger it, below the 3-interval decision cadence; no source gives the delay",
    "fire.release_by.knowledge": "authored: recipients are chosen by headquarters' known position and reports, "
                                 "with a normal order's refusals (command.spoken, engine.validate_order); a newer "
                                 "hold_fire, pending or delivered after the losses, wins",
    "fire.release_by.reach": "authored: the order carries the 1775 voice reach of 2 hexes, the docs/research/47 "
                             "assumption; no new number",
    "fire.release_by.trigger": "authored: the release condition is unchanged: casualties in a hold-fire unit "
                               "(warning shots release no one, as 'fire')",
    "fire.release_by.out_of_reach": "sourced: a company out of earshot keeps Barrett's own rule, 'Do not fire "
                                    "unless first fired upon' (S47)",
    "fire.release_scope": "reconstruction: the order opens only the company that met the release condition, the "
                          "one Buttrick stood in; S47 does not say which other companies heard it (the earshot "
                          "reading is the unsourced sensitivity-earshot-release)",
}
FIRE_BEFORE = FireEntry(default_posture="hold_fire")  # v1: each company releases itself (doc 48).
FIRE = FireEntry(default_posture="hold_fire", release_by="command")  # v2: docs/research/50.


def concord_entry(variant=None, british=BRITISH_THREE, bridge_cost=BRIDGE_MOVE_COST):
    """One Concord entry (v2, command fire release); ``variant`` None is the
    catalog reading. ``before`` gives its v1 form."""
    suffix = "" if variant is None else f"-{variant}"
    succession = tuple(u.id for u in british if u.id != "B2")
    return ScenarioEntry(
        id="concord-north-bridge" + suffix,
        title="Concord North Bridge" + ("" if variant is None else f" ({variant})"),
        variant=variant,
        rules=RULES_VERSION,
        prompt_version="concord-side-v1",
        prompt_setting="Concord's North Bridge, 1775",
        labels={"poc-13": f"concord-north-bridge{suffix}-v2"},
        location="North Bridge · Concord, Massachusetts",
        date="1775-04-19",
        start_time="09:25:00",
        time_basis=("Scenario local time; reconstruction: five minutes before NPS's 09:30 (S47); "
                    "NPS clock times as written, the minute is not sourced"),
        seconds_per_turn=30,
        weather={"season": "spring", "conditions": "April, fixed POC condition (authored, not sourced)"},
        sides={
            "provincial": SideEntry(
                name="Provincials", role="attacker", command_unit="P1", headquarters=(3, 10),
                mission=PROVINCIAL_MISSION,
                charge="advance to the bridge, hold fire unless fired upon, and clear the crossing",
                brief=PROVINCIAL_BRIEF),
            "british": SideEntry(
                name="British", role="defender", command_unit="B2", headquarters=(21, 10),
                mission=BRITISH_MISSION,
                charge="guard the North Bridge and fall back toward the town if it gives way"),
        },
        player_side="provincial",
        units=PROVINCIALS + british,
        victory=VictoryEntry(kind="hold-objective", objective=BRIDGE, deadline_turns=20, radius=1,
                             hold_turns=2, objective_name="bridge"),
        map=MapEntry(terrain=_terrain(bridge_cost), features=FEATURES, cols=COLS, rows=ROWS,
                     metres_per_hex=METRES_PER_HEX, width=1080, height=840,
                     source=("Authored, not surveyed: an illustrative Concord River, North Bridge, "
                             "provincial ridge and town road (docs/research/43, 48)."),
                     source_url=None),
        order_catalog=ORDER_CATALOG,
        communications=COLONIAL_COMMUNICATIONS,
        voice_profile=COLONIAL_VOICE_PROFILE,
        tools_per_unit=0,
        # Barrett's order: provincials hold fire; the British fired without one (S47).
        # The command may release it on losses it knows of (docs/research/50).
        fire=FIRE,
        command=CommandEntry(succession={"provincial": ("P2", "P3", "P4"), "british": succession}),
        weapons=WEAPONS_1775,
        scripted={"provincial": "scripted-concord-militia-v1", "british": "scripted-concord-regulars-v1"},
        desk=DESK,
        provenance={**PROVENANCE, **RELEASE_PROVENANCE},
    )


def before(entry):
    """Why: the change must keep its before run (build-handoff step 3).
    What: ``entry`` as it was before docs/research/50: ``FIRE_BEFORE`` (each
    company releases itself), its ``-v1`` label and no release provenance.
    Test: `test_before_entry_keeps_its_pinned_digest`."""
    label = entry.labels[RULES_VERSION].removesuffix("-v2") + "-v1"
    return replace(entry, labels={RULES_VERSION: label}, fire=FIRE_BEFORE,
                   provenance={k: v for k, v in entry.provenance.items() if k not in RELEASE_PROVENANCE})


def _open_fire(units):
    return tuple(UnitEntry(u.id, u.side, u.name, u.pos, {**u.overrides, "fire_posture": "open_fire"})
                 for u in units)


# docs/research/74 (default ruling bt-D08): on the command desk the British play the
# regulars' scripted control, as in headless runs. Variants and v1 are not on the desk.
CONCORD_NORTH_BRIDGE = replace(concord_entry(british=_open_fire(BRITISH_THREE)), desk_scripted_opponent=True)
# Before docs/research/50: the v1 entry, each company releasing itself. Kept
# buildable and pinned to its old digests; in no catalog.
CONCORD_NORTH_BRIDGE_BEFORE = before(CONCORD_NORTH_BRIDGE)
# The same v1 entry under its own id, so saved concord-north-bridge-v1 games
# (the 2026-11-06 baseline archive, made at d6f1748) resolve through
# ``for_state``. Headless catalog only, never a player scenario.
CONCORD_NORTH_BRIDGE_V1 = replace(CONCORD_NORTH_BRIDGE_BEFORE, id="concord-north-bridge-v1",
                                  title="Concord North Bridge (v1, before docs/research/50)")


@dataclass(frozen=True)
class Variant:
    """An alternative reading of one doc 43 open question, kept as data.

    ``question`` locates the question, ``reading`` states the alternative and
    ``source`` where it comes from. Variants validate and build; the
    scripted policies are written for the catalog geometry, so only
    ``two-companies`` and ``planks-lifted`` keep it."""

    question: str
    reading: str
    source: str
    entry: ScenarioEntry


VARIANTS = {
    "british-west-bank": Variant(
        question="doc 43 §6 question 1 (which bank held which force)",
        reading="the guard stands at the west end of the bridge, on the militia's bank, the river behind it",
        source="S47, S48 and S49 are silent on the banks; web snippets not read put the British on the "
               "town (east) bank when they fired (doc 43 §6, unverified)",
        entry=concord_entry("british-west-bank", british=_open_fire(BRITISH_WEST))),
    "planks-lifted": Variant(
        question="doc 43 §6 question 2 (was the plank removal done)",
        reading=f"planks partly lifted: the bridge hex costs {LIFTED_PLANKS_MOVE_COST} to enter, not "
                f"{BRIDGE_MOVE_COST}; a fully lifted bridge would put the objective on impassable water, "
                "which validate refuses",
        source="S47: an officer suggested removing the planks; the page does not confirm it was done",
        entry=concord_entry("planks-lifted", british=_open_fire(BRITISH_THREE),
                            bridge_cost=LIFTED_PLANKS_MOVE_COST)),
    "two-companies": Variant(
        question="doc 43 §6 question 3 (two or three British companies)",
        reading="two companies of 45, about 90 men",
        source="S49: two companies guarded the bridge, about 90 men; S47 gives three, about 96",
        entry=concord_entry("two-companies", british=_open_fire(BRITISH_TWO))),
}
