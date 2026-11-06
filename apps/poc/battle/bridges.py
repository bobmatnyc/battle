"""Bridge hexes with a state: intact, wired with charges, or destroyed.

Why: at Pegasus Bridge the question is whether the bridge stays passable
(docs/research/52, gap 5). What: pure functions of the snapshot that
``engine`` calls. The state lives on the bridge's ``map_features`` entry and,
for movement, on its cell (``bridge_state``; ``grid.passable`` refuses a
destroyed one). A battle without a declared bridge has neither, so it plays
exactly as before. Design and limits: docs/research/53.
"""
from copy import deepcopy
from . import grid

STATES=('intact','charges','destroyed')


def present(s):
    """The bridge features of ``s``; none in a battle without declared bridges."""
    return [f for f in s.get('map_features',[]) if f.get('kind')=='bridge']


def set_state(s,bridge_id,state,cause,emit):
    """Why: the demolition trigger is scripted for now (docs/research/53), but
    every change must be one recorded, replayable transition.
    What: sets bridge ``bridge_id`` to ``state`` on its feature and its cell
    and emits ``bridge_state_changed`` with the old and new state and
    ``cause``. A destroyed bridge stays destroyed; a no-op change emits nothing.
    Test: `test_scheduled_demolition_is_an_event_and_replays_identically`."""
    if state not in STATES:raise ValueError(f'Bridge state must be one of {STATES}.')
    f=next(f for f in present(s) if f['id']==bridge_id)
    if f['state']==state or f['state']=='destroyed':return
    old=f['state'];f.update(state=state,updated_turn=s['turn'])
    s['cells'][grid.key(f['pos'])]['bridge_state']=state
    emit(s,'bridge_state_changed',bridge_id=bridge_id,pos=list(f['pos']),from_state=old,to_state=state,cause=cause)


def progress(s,emit):
    """Applies the authored ``bridge_schedule`` entries due this interval, in
    entry order. Nothing happens without a schedule."""
    for change in s.get('bridge_schedule',()):
        if change['turn']==s['turn']:
            set_state(s,change['bridge_id'],change['state'],'scheduled',emit)


def known_cells(s,side,cells):
    """Why: headquarters' delivery estimates must not learn a demolition it has
    not been told of. What: ``cells`` (None: the live cells) with each bridge
    cell's ``bridge_state`` taken from ``side``'s feature reports. Returns
    ``cells`` unchanged in a battle without bridges.
    Every bridge has a briefed report (``setup``), so a missing one raises.
    Test: `test_delivery_estimate_uses_the_bridge_state_headquarters_knows`."""
    bridges=present(s)
    if not bridges:return cells
    known={k:dict(c) for k,c in (s['cells'] if cells is None else cells).items()}
    for f in bridges:
        known[grid.key(f['pos'])]['bridge_state']=s['feature_reports'][side][f['id']]['state']
    return known


def known_terrain(s,side):
    """Why: an order check that read the true cells would tell headquarters of a
    demolition before any report (docs/research/53). What: the cells as
    ``side`` knows them: bridge states from its reports over the gate walls it
    knows, else the live cells (identical in a battle without bridges).
    Test: `test_move_to_a_bridge_blown_unreported_is_accepted_and_fails_to_path`."""
    from . import gates
    known=known_cells(s,side,gates.known_cells(s,side))
    return s['cells'] if known is None else known


def setup(s,bridges):
    """Store authored ``bridges`` (``scenario_wwii.BridgeEntry``) in ``s``: a
    briefed ``map_features`` entry and feature report per side, the cell's
    ``bridge_state``, and ``bridge_schedule`` when any change is scheduled."""
    schedule=[]
    for b in bridges:
        f={'id':b.id,'kind':'bridge','name':b.name,'pos':list(b.pos),'state':b.state,
           'updated_turn':0,'provenance':'authored-poc','briefed':True}
        s['map_features'].append(f)
        for cells in (s['cells'],s['briefing_cells']):  # The briefing shows the authored state.
            cells[grid.key(f['pos'])]['bridge_state']=b.state
        for reports in s['feature_reports'].values():
            reports[b.id]=dict(deepcopy(f),observed_turn=0,received_turn=0)
        schedule.extend({'bridge_id':b.id,'turn':turn,'state':state} for turn,state in b.schedule)
    if schedule:
        s['bridge_schedule']=sorted(schedule,key=lambda c:c['turn'])
