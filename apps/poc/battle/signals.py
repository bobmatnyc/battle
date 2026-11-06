"""Success codewords sent as reports (docs/research/53).

Why: at Pegasus Bridge "Ham" meant the canal bridge was taken (S54). A
codeword is news, so headquarters must learn it only when a report carrying
it arrives, never from a global flag. What: pure functions of the snapshot
that ``engine`` calls. ``s['signals']`` holds the authored signals and is
written only for an entry that declares them; a battle without it plays
exactly as before.
"""
from copy import deepcopy
from . import comms,grid


def _taken(s,signal,bridge):
    """The unit of ``signal['side']`` holding ``bridge``, or None: the lowest-id
    live unit on its hex, the bridge not destroyed and no live enemy within
    ``radius`` hexes."""
    if bridge['state']=='destroyed':return None
    live=[u for u in s['units'] if u['strength']>0 and u['status'] not in ('lost','merged')]
    if any(u['side']!=signal['side'] and grid.distance(u['pos'],bridge['pos'])<=signal['radius'] for u in live):return None
    holders=[u for u in live if u['side']==signal['side'] and u['pos']==bridge['pos'] and u['status']!='routed']
    return min(holders,key=lambda u:u['id']) if holders else None


def check(s,emit,enqueue):
    """Why: the unit that takes a bridge must report the codeword itself.
    What: for each unsent signal whose condition ``taken`` holds, the holding
    unit sends one ``signal`` report to its command detachment by the
    ordinary report transport (voice, radio or runner) and ``signal_sent``
    records the codeword, sender, receiver and turn sent. Each is sent once.
    Test: `test_codeword_arrives_as_a_delivered_report_not_a_flag`,
    `test_codeword_is_not_sent_while_an_enemy_is_near_or_the_bridge_is_down`."""
    if 'signals' not in s:return
    bridges={f['id']:f for f in s['map_features'] if f.get('kind')=='bridge'}
    for signal in s['signals']:
        if signal['sent_turn'] is not None:continue
        holder=_taken(s,signal,bridges[signal['bridge']])
        if holder is None:continue
        receiver=comms.command_unit(s,signal['side'])
        signal.update(sent_turn=s['turn'],sender_id=holder['id'],receiver_id=receiver['id'])
        emit(s,'signal_sent',codeword=signal['codeword'],side=signal['side'],bridge_id=signal['bridge'],
             sender_id=holder['id'],receiver_id=receiver['id'],sent_turn=s['turn'])
        data={k:signal[k] for k in ('codeword','meaning','bridge','sender_id','receiver_id','sent_turn')}
        enqueue(s,signal['side'],f'{holder["id"]} to headquarters: {signal["codeword"]}. {signal["meaning"]}',
                data=data,kind='signal',sender=holder['id'])


def receive(s,report):
    """Records a delivered codeword for its side, with the turn it arrived."""
    data=report['data']
    s['signals_received'][report['side']].append(dict(deepcopy(data),delivered_turn=s['turn']))


def visible(s,side):
    """The codewords ``side``'s headquarters has received, oldest first."""
    return deepcopy(s['signals_received'][side])


def setup(s,signals):
    """Store authored ``signals`` (``scenario_wwii.SignalEntry``) in ``s``, unsent."""
    s['signals']=[{'codeword':x.codeword,'meaning':x.meaning,'side':x.side,'bridge':x.bridge,
                   'condition':x.condition,'radius':x.radius,'sent_turn':None} for x in signals]
    s['signals_received']={side:[] for side in s['contacts']}
