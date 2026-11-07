"""Broadcast signals with audibility (docs/research/60 §1).

Why: a trumpet recall is not an addressed order. It reaches the units that
hear it, at once, and no others; at Gergovia a valley kept it from the
legions that went on (docs/research/57, VII.47). What: pure functions of the
snapshot that ``engine`` and ``runtime`` call. ``s['broadcasts']`` is
written only for an entry that declares signals
(``scenario_broadcast.setup``), so a battle without it plays as before.
"""
from copy import deepcopy
from . import comms,grid
from .engine_v2 import InvalidOrder


def hears(signal,source,pos):
    """Why: a unit acts on a signal only if the sound reaches it.
    What: ``(heard, reason)`` for a listener at ``pos`` when ``signal`` is
    sounded at ``source``: not heard beyond ``reach`` hexes
    (``out_of_reach``), nor when a declared block hex lies strictly between
    the two on ``grid.line`` (``blocked``). Reads geometry only.
    Test: `test_units_in_reach_hear_and_units_beyond_do_not`,
    `test_a_declared_block_on_the_line_stops_the_sound`."""
    if grid.distance(source,pos)>signal['reach']:return False,'out_of_reach'
    block={grid.key(p) for p in signal['block_hexes']}
    if any(grid.key(p) in block for p in grid.line(source,pos)[1:-1]):return False,'blocked'
    return True,'heard'


def order(s,side,signal_id):
    """Why: a signal declared without a turn is the commander's to sound.
    What: marks ``side``'s signal ``signal_id`` ordered at this turn; it is
    sounded at the start of the next interval (``progress``). Raises
    InvalidOrder for an unknown, scheduled, already ordered or sounded
    signal, or while the command detachment is disrupted.
    Test: `test_ordered_signal_sounds_at_the_next_interval`,
    `test_orders_the_rules_cannot_follow_are_refused`."""
    from . import engine
    signal=next((b for b in s.get('broadcasts',()) if b['id']==signal_id and b['side']==side),None)
    if signal is None or signal['turn'] is not None:raise InvalidOrder('No such signal is held for your order.')
    if signal['ordered_turn'] is not None:raise InvalidOrder('That signal has already been ordered.')
    if not comms.operational(s,side):raise InvalidOrder('Command detachment is disrupted; no signal can be sounded.')
    signal['ordered_turn']=s['turn']
    engine.emit(s,'signal_ordered',signal_id=signal_id,side=side)


def _due(s,signal):
    if signal['sounded_turn'] is not None:return False
    if signal['turn'] is not None:return s['turn']>=signal['turn']
    return signal['ordered_turn'] is not None and s['turn']>signal['ordered_turn']


def _obey(s,u,signal):
    """The hearing unit takes up the signal's mission as a delivered order would."""
    from . import orders
    version=max([o['version'] for o in s['orders'] if o['unit_id']==u['id']]+[u['order_version']])+1
    u.update(order_version=version,target=deepcopy(signal['destination']),stance=signal['stance'])
    orders.start(s,u,{'id':signal['id'],'stance':signal['stance'],'version':version})


def progress(s,emit,message):
    """Why: every unit in earshot must hear a signal at once, and only those.
    What: at the start of an interval, sounds each due signal (its ``turn``
    reached, or ordered last interval) from the side's command detachment
    when it is operational; a disrupted command sounds nothing and the
    signal waits. Each live unit of the side other than the sounder gets a
    receipt (``heard``, ``reason``, ``turn``, ``obeyed``) and an event
    ``signal_heard`` or ``signal_not_heard``. A hearing unit that is not
    routed or leaderless takes up the signal's mission and records it in
    ``heard_signals``; any other unit keeps its mission and learns nothing.
    Test: `test_a_unit_that_hears_takes_up_the_signal_and_one_that_does_not_keeps_its_mission`,
    `test_an_unheard_signal_does_not_change_the_units_decision`,
    `test_a_disrupted_command_does_not_sound_the_signal`."""
    for signal in s.get('broadcasts',()):
        if not _due(s,signal) or not comms.operational(s,signal['side']):continue
        sounder=comms.command_unit(s,signal['side'])
        signal.update(sounded_turn=s['turn'],sounder_id=sounder['id'])
        emit(s,'signal_sounded',signal_id=signal['id'],side=signal['side'],sounder_id=sounder['id'],pos=list(sounder['pos']))
        message(s,signal['side'],f'{sounder["id"]}: signal {signal["id"]} sounded. {signal["meaning"]}',kind='broadcast')
        for u in sorted(s['units'],key=lambda x:x['id']):
            if u['side']!=signal['side'] or u['id']==sounder['id'] or u['strength']<=0 or u['status'] in ('lost','merged'):continue
            heard,reason=hears(signal,sounder['pos'],u['pos'])
            obeyed=heard and u['status']!='routed' and not u.get('leaderless')
            signal['receipts'][u['id']]={'heard':heard,'reason':reason,'turn':s['turn'],'obeyed':obeyed}
            emit(s,'signal_heard' if heard else 'signal_not_heard',signal_id=signal['id'],unit_id=u['id'],reason=reason,obeyed=obeyed)
            if heard:u.setdefault('heard_signals',[]).append(signal['id'])
            if obeyed:_obey(s,u,signal)


def visible(s,side):
    """``side``'s own signals as its headquarters knows them: when ordered and
    sounded, never who heard."""
    return [{k:deepcopy(b[k]) for k in ('id','kind','meaning','stance','destination','turn','ordered_turn','sounded_turn')}
            for b in s.get('broadcasts',()) if b['side']==side]
