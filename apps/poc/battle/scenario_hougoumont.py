"""Hougoumont north gate, 18 June 1815: a catalog entry (poc-10, poc-11).

Why: the third of the first five selections (docs/research/37 §2) turns on
whether the north gate is shut. What: one ``ScenarioEntry``,
``HOUGOUMONT_NORTH_GATE``, with an authored, illustrative map (not
surveyed), aggregate detachments, reconstructed missions, authored gate
labour and the ``hold-compound`` victory kind. Every field's basis is in the
entry's ``provenance`` and in docs/research/42-hougoumont-scenario.md.
"""
from .grid import COLS, METRES_PER_HEX, ROWS, key, neighbors
from .scenario_entry import (
    GATE_ORDER_CATALOG, RULES_VERSION, DeskBrief, GateEntry, GatewayPushEntry, MapEntry, ScenarioEntry,
    SideBrief, SideEntry, SupplyEntry, UnitEntry, VictoryEntry,
)

# Authored layout, not surveyed. North is row 0, toward the Allied ridge;
# the wood lies south, toward the French. The walled compound is the
# chateau hex and its six neighbours (about 150 m across at 50 m a hex).
CHATEAU = [11, 10]
COMPOUND = [CHATEAU] + neighbors(CHATEAU)
NORTH_GATE_INSIDE, NORTH_GATE_OUTSIDE = [11, 9], [11, 8]

# Authored terrain classes: (terrain kind, area label, move cost, cover).
# The orchard uses the woods kind, which the sight rule and browser know.
AREAS = {
    'farm-courtyard': ('open', 100, 35),
    'walled-garden': ('open', 110, 30),
    'orchard': ('woods', 120, 22),
    'great-wood': ('woods', 145, 32),
    'open-ground': ('open', 100, 10),
}


def _area(c, r):
    if [c, r] in COMPOUND:
        return 'farm-courtyard'
    if 12 <= c <= 13 and 9 <= r <= 11:
        return 'walled-garden'
    if 14 <= c <= 16 and 8 <= r <= 12:
        return 'orchard'
    if r >= 13 and 6 <= c <= 15:
        return 'great-wood'
    return 'open-ground'


def terrain():
    """Authored, illustrative cells: a gentle rise to the Allied ridge in the
    north and to the wood in the south; elevations are not surveyed."""
    cells = {}
    for r in range(ROWS):
        for c in range(COLS):
            area = _area(c, r)
            kind, move, cover = AREAS[area]
            elevation = round(118 + 1.2 * max(0, 8 - r) + 0.6 * max(0, r - 14))
            cells[key([c, r])] = {'pos': [c, r], 'elevation': elevation, 'terrain': kind,
                                  'move_cost': move, 'cover': cover, 'area': area}
    return cells


FEATURES = {
    'roads': (
        {'id': 'north-lane', 'kind': 'road', 'name': 'Lane from the north gate to the ridge',
         'points': [[11, 8], [11, 5], [12, 1]]},
        {'id': 'west-lane', 'kind': 'road', 'name': 'Western lane round the farm',
         'points': [[7, 18], [7, 13], [8, 10], [10, 8], [11, 8]]},
        {'id': 'wood-ride', 'kind': 'road', 'name': 'Ride through the wood',
         'points': [[11, 20], [11, 13]]},
    ),
    'buildings': (
        {'id': 'hougoumont', 'kind': 'building', 'name': 'Hougoumont chateau and farm',
         'pos': CHATEAU, 'cover': 45, 'height': 8, 'compound': COMPOUND,
         # Sourced: the north gate was open for friendly traffic (doc 37 §2).
         'openings': [{'id': 'north-gate', 'name': 'North gate', 'inside': NORTH_GATE_INSIDE,
                       'outside': NORTH_GATE_OUTSIDE, 'state': 'open'}]},
    ),
    'works': (),
}

SMOOTHBORE = 'smoothbore muskets'


def _men(n, **extra):
    """Authored aggregate strength with 40 cartridges a man, as ``unit()``."""
    return {'initial': n, 'strength': n, 'ammo': n * 40, 'weapon_class': SMOOTHBORE, **extra}


ALLIED_MISSION = (
    "You command the Allied garrison of Hougoumont farm, a detachment of the Guards with the "
    "gate party of the 2nd Coldstream Guards at the north gate. Your mission: hold the walled "
    "farm until turn 60. Keep the north gate open for supply and friendly traffic, and close it "
    "if the enemy breaks in. The farm is lost if French troops hold the inside of the walls for "
    "6 consecutive turns while none of your formations remains effective inside."
)
FRENCH_MISSION = (
    "You command the French assault group west of Hougoumont farm. Your mission: pass men "
    "through the north gate before it is shut, and hold the inside of the walls for 6 "
    "consecutive turns with no effective Allied formation inside, before turn 60."
)

HOUGOUMONT_NORTH_GATE = ScenarioEntry(
    id='hougoumont-north-gate',
    title='Hougoumont: the north gate',
    variant=None,
    rules=RULES_VERSION,
    prompt_version='hougoumont-side-v1',
    prompt_setting='Hougoumont, Waterloo, 1815',
    labels={'poc-10': 'hougoumont-north-gate-v1', 'poc-11': 'hougoumont-north-gate-v2'},
    location='Hougoumont · Waterloo, Belgium',
    date='1815-06-18',
    start_time='11:20:00',
    time_basis=('Scenario local time; reconstruction: ten minutes before the closing at about '
                '11:30 given by one secondary page; the exact time is uncertain'),
    seconds_per_turn=30,
    weather={'season': 'summer', 'conditions': 'fixed POC condition (authored, not sourced)'},
    sides={
        'allied': SideEntry(
            name='Allied', role='defender', command_unit='A2', headquarters=(11, 10),
            mission=ALLIED_MISSION,
            charge='hold the farm, keeping the north gate open for supply until it must be shut',
            supply=SupplyEntry('Allied cartridge reserve on the ridge', (12, 2), 2400, SMOOTHBORE),
            brief=SideBrief(
                kicker='THE NORTH GATE', tagline='Hold the farm.',
                subhead='You command the Allied garrison. The computer commands the French assault.',
                mission_title='Hold the farm',
                mission_text=('Keep an effective formation inside the walls of Hougoumont until **11:50**. '
                              'Keep the north gate open for supply and friendly traffic, and close it if '
                              'the French break in. If French troops hold the inside of the walls for '
                              '180 seconds with no effective Allied formation inside, the battle ends at '
                              'once in their favor, even before 11:50.'),
                win='Hougoumont holds.', loss='The farm is lost.')),
        'french': SideEntry(
            name='French', role='attacker', command_unit='F2', headquarters=(7, 16),
            mission=FRENCH_MISSION,
            charge='pass men through the north gate before it is shut and hold the farm',
            supply=SupplyEntry('French cartridge reserve in the wood', (6, 18), 2400, SMOOTHBORE)),
    },
    player_side='allied',
    units=(
        UnitEntry('A1', 'allied', 'Gate party · 2nd Coldstream Guards', tuple(NORTH_GATE_INSIDE), _men(15)),
        UnitEntry('A2', 'allied', 'Coldstream companies · farm courtyard', (10, 9), _men(60)),
        UnitEntry('A3', 'allied', 'Guards companies · chateau court', (11, 11), _men(60)),
        UnitEntry('F1', 'french', "Legros's party", (8, 10), _men(30)),
        UnitEntry('F2', 'french', 'Assault group · follow-on companies', (7, 12), _men(80)),
        UnitEntry('F3', 'french', 'Skirmishers · wood edge', (10, 13),
                  _men(40, recon_role='scout', recon_skill=80)),
    ),
    victory=VictoryEntry(kind='hold-compound', objective=tuple(CHATEAU), deadline_turns=60,
                         hold_turns=6, objective_name='farm'),
    map=MapEntry(terrain=terrain, features=FEATURES, cols=COLS, rows=ROWS,
                 metres_per_hex=METRES_PER_HEX, width=1080, height=840,
                 source=('Authored, not surveyed: an illustrative layout of the Hougoumont farm '
                         'compound, north gate, walled garden, orchard, wood and lanes '
                         '(docs/research/42).'),
                 source_url=None),
    order_catalog=GATE_ORDER_CATALOG,
    communications='napoleonic-courier-v1',
    voice_profile='napoleonic-en-v1',
    desk=DeskBrief(campaign='WATERLOO · 18 JUNE 1815', place='Hougoumont farm',
                   objective_label='COMPOUND OBJECTIVE', objective_key='FARM',
                   conditions='SUMMER · FIXED POC CONDITION', draw='The battle ends in a draw.'),
    # Sensitivity parameters, not estimates: the gate party of 15 shuts the
    # gate in 3 intervals and bars it in 2 more; two parties of 20 or more
    # force a closed gate in 3.
    gates=GateEntry(close_labour=45, bar_labour=30, force_labour=120, work_cap=20),
    # poc-11, authored sensitivity parameter: a party of 20 or more on the
    # outside hex carries a held gateway in 3 intervals (docs/research/44).
    gateway_push=GatewayPushEntry(push_labour=60, push_cap=20),
    provenance={
        'location': 'sourced: Hougoumont, held by a Guards detachment (S44)',
        'date': 'sourced: 18 June 1815 (S44)',
        'start_time': 'reconstruction: 11:20, before the about 11:30 closing in Age of Revolution, '
                      'Closing the Gates (secondary, uncited); S44 dates the first attacks from about ten',
        'weather': 'authored: no source read gives it',
        'sides': 'sourced: Allied garrison of the Guards (S44, S45) against a French party (S45, NAM)',
        'player_side': 'authored: the Allied garrison, whose gate decision the fixture asks about',
        'allied.mission': 'reconstruction: "keep the supply entrance open, close on a breach" (doc 37 '
                          'register); holding the farm follows S44 and the fire note in S45',
        'french.mission': 'reconstruction: "pass men through before it shuts", inferred from outcome '
                          'pages; no French order was found',
        'map': 'authored: illustrative layout, not surveyed; the open north gate is sourced '
               '(Closing the Gates, NAM)',
        'units': 'authored: aggregate detachments; names follow S44 and S45',
        'units.strength': "authored: except Legros's party at 30, set from the about 30 who got in "
                          '(Closing the Gates; secondary, uncited)',
        'units.skill': 'authored: default skill, morale and cartridges of the POC detachment',
        'gates': 'authored: sensitivity parameters (doc 37 open question 6); no source gives them',
        'gateway_push': 'authored: sensitivity parameter (doc 44); no source gives the effort to carry the gateway',
        'victory': 'authored: courtyard possession for 6 turns, deadline 60 turns',
        'voice_profile': 'authored: minimal 1815 dispatch voice',
        'desk': 'authored: command-desk text; the 11:50 deadline and 180 seconds follow from '
                'the 60-turn deadline and the 6-turn hold at 30 seconds a turn',
        'communications': 'authored: 1863 transport rates under an 1815 label',
    },
)
