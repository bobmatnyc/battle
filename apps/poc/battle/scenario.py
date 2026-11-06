"""Little Round Top: authored, uncalibrated POC terrain, detachments and missions.

The scenario is one ``ScenarioEntry`` (``LITTLE_ROUND_TOP``); ``create`` keeps
the original function API for every rules edition.
"""
import math
from .grid import COLS, ROWS, METRES_PER_HEX, center, key
from .scenario_entry import (
    RULES_VERSION, SIDES, MapEntry, ScenarioEntry, SideEntry, SupplyEntry,
    UnitEntry, VictoryEntry, build_state, unit,
)

__all__ = ['SIDES', 'RULES_VERSION', 'LITTLE_ROUND_TOP', 'terrain', 'unit', 'create']

def terrain():
    cells = {}
    for r in range(ROWS):
        for c in range(COLS):
            p=[c,r]; x,y=center(p)
            hill = 40*math.exp(-((x-530)**2/170**2+(y-600)**2/230**2))
            spur = 15*math.exp(-((x-540)**2/120**2+(y-390)**2/140**2))
            woods = y > 530 and 250 < x < 740
            rocks = 420 < x < 630 and 490 < y < 670
            kind = 'rocky' if rocks else 'woods' if woods else 'open'
            cells[key(p)]={'pos':p,'elevation':round(145+hill+spur), 'terrain':kind,
                           'move_cost':{'open':100,'woods':145,'rocky':170}[kind],
                           'cover':{'open':10,'woods':32,'rocky':46}[kind]}
    return cells

# Authored map features; not surveyed historical placements.
FEATURES = {
    'roads': ({'id':'north-lane','kind':'road','name':'North farm lane','points':[[3,2],[7,4],[11,6],[14,8],[18,9],[22,10]]},
              {'id':'south-track','kind':'road','name':'Southern track','points':[[1,19],[4,18],[7,17],[9,16]]}),
    'buildings': ({'id':'farmstead','kind':'building','name':'Farmstead','pos':[7,3],'cover':45,'height':8},
                  {'id':'barn','kind':'building','name':'Barn','pos':[17,8],'cover':40,'height':6}),
    'works': ({'id':'prepared-works','kind':'fortification','name':'Prepared breastwork','pos':[11,13],
               'cover':60,'progress':100,'effort':400,'required':400,'updated_turn':0},),
}

# Authored reconnaissance assignments; not claims about the historical regiments.
SCOUT = {'recon_role':'scout','recon_skill':80}

LITTLE_ROUND_TOP = ScenarioEntry(
    id='little-round-top',
    title='Little Round Top',
    variant=None,
    rules=RULES_VERSION,
    prompt_version='lrt-side-v2',
    prompt_setting='Little Round Top, 1863',
    labels={'poc-1':'little-round-top-v2','poc-2':'little-round-top-v2',
            'poc-3':'little-round-top-v3','poc-4':'little-round-top-v4',
            'poc-5':'little-round-top-v5','poc-6':'little-round-top-v6',
            'poc-7':'little-round-top-v7','poc-8':'little-round-top-v8'},
    location='Little Round Top · Gettysburg, Pennsylvania',
    date='1863-07-02',
    start_time='16:30:00',
    time_basis='Scenario local time; authored start time',
    seconds_per_turn=30,
    weather={'season':'summer','conditions':'dry, clear (fixed POC condition)'},
    sides={
        'union': SideEntry(
            name='Union', role='defender', command_unit='U2', headquarters=(14,8),
            mission='You command the Union defenders. Your mission: hold the marked summit objective until turn 60. The summit can be lost before then if the enemy holds it while none of your formations remains effective nearby.',
            charge="hold the marked summit until five o'clock",
            supply=SupplyEntry('Union ammunition point',(14,8),2400,'rifled muskets')),
        'confederate': SideEntry(
            name='Confederate', role='attacker', command_unit='C2', headquarters=(4,20),
            mission='You command the Confederate attackers. Your mission: occupy the marked summit objective, within one hex of it, for 3 consecutive turns with no effective Union formation nearby, before turn 60.',
            charge='take the marked summit before five o\'clock',
            supply=SupplyEntry('Confederate ammunition point',(4,20),2400,'rifled muskets')),
    },
    units=(UnitEntry('U1','union','20th Maine · A',(11,14)),
           UnitEntry('U2','union','20th Maine · B',(13,15)),
           UnitEntry('U3','union','20th Maine · C',(10,13),SCOUT),
           UnitEntry('C1','confederate','15th Alabama · A',(5,20)),
           UnitEntry('C2','confederate','15th Alabama · B',(9,20)),
           UnitEntry('C3','confederate','47th Alabama · A',(3,17),SCOUT)),
    victory=VictoryEntry(kind='hold-objective', objective=(11,15), defender='union',
                         attacker='confederate', deadline_turns=60),
    map=MapEntry(terrain=terrain, features=FEATURES, cols=COLS, rows=ROWS,
                 metres_per_hex=METRES_PER_HEX, width=1080, height=840,
                 source='Library of Congress, Gettysburg topographic map (1876). Authored POC terrain; approximate registration.',
                 source_url='https://www.loc.gov/item/99447491/'),
    order_catalog=('hold','move','rest','retreat','resupply','recon','dig_in'),
    communications='civil-war-courier-v1',
    voice_profile='civil-war-en-v1',
)

def create(rules=RULES_VERSION):
    """Little Round Top's initial snapshot in ``rules`` (compatibility API)."""
    return build_state(LITTLE_ROUND_TOP, rules)
