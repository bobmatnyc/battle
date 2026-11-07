"""Surrender and a conserved captive account (docs/research/59 §1).

Why: at Hill 223 groups yielded on what they believed they faced, and the
patrol brought its prisoners back (docs/research/56 §10, gap 2). No
surrender or captive account existed. The rule is a unit override that only a
declaring entry writes, so every other battle plays as before.
What: ``check`` decides, from each declaring unit's own sightings, which units
yield this interval; ``escape`` frees the captives of a holder that can no
longer hold them. A yielding unit's whole strength becomes one captive record
(count, holder unit, turn) in ``s['captives']``; the unit is ``lost`` with
``surrendered``. Captives are counted, never created or turned back into a
unit, and no individual is modelled. No dice.
"""
from . import facing,grid,recon

GONE=('routed','lost','merged')


def _yields(s,u,contacts):
    """The holder ``u`` yields to, or None. Reads only ``contacts`` (``u``'s own
    sightings) and the friends ``u`` sees; see ``check``."""
    rule=u['surrender']
    near=[c for c in contacts if grid.distance(u['pos'],c['pos'])<=rule['reach']
          and not (rule['rear_only'] and facing.within(u,c['pos']))]
    if not near:return None
    believed=sum(c['strength_range'][1] for c in near)
    support=sum(f['strength'] for f in s['units'] if f['side']==u['side'] and f is not u and f['strength']>0
                and f['status'] not in GONE and grid.distance(u['pos'],f['pos'])<=rule['support_reach']
                and recon.sees(s,u,f['pos']))
    if believed*100<rule['odds_pct']*(u['strength']+support):return None
    return min(near,key=lambda c:(grid.distance(u['pos'],c['pos']),c['id']))['id']


def check(s,sightings,emit,enqueue):
    """Why: a group yields on what it observes, not on the truth.
    What: every live unit that declares ``surrender`` yields when the high
    end of the strength it estimates (``recon.estimate``) for the enemies it
    sees within ``reach`` hexes (with ``rear_only``, only those outside its
    arc) is at least ``odds_pct`` per cent of its own strength plus that of
    the effective friends it sees within ``support_reach``. All decisions are
    taken from the same state before any applies, so the order of ids cannot
    matter. The nearest of those enemies (lowest id on a tie) takes the whole
    strength as captives and reports it to its headquarters by the ordinary
    report transport (``kind`` ``captives``).
    Test: `test_a_declaring_unit_yields_to_a_seen_party_that_it_believes_strong_enough`,
    `test_an_enemy_the_unit_cannot_observe_does_not_change_the_decision`,
    `test_decisions_in_one_interval_are_taken_together`."""
    decided=[(u,_yields(s,u,sightings.get(u['id'],[]))) for u in sorted(s['units'],key=lambda x:x['id'])
             if u.get('surrender') and u['strength']>0 and u['status'] not in GONE]
    for u,holder_id in decided:
        if holder_id is None:continue
        holder=next(x for x in s['units'] if x['id']==holder_id)
        record={'id':f'K{len(s.setdefault("captives",[]))+1}','count':u['strength'],'from_unit':u['id'],
                'from_side':u['side'],'holder_id':holder_id,'holder_side':holder['side'],'turn':s['turn'],
                'status':'held'}
        s['captives'].append(record)
        holder['captives']=holder.get('captives',0)+record['count']
        u.update(strength=0,status='lost',surrendered=True)
        emit(s,'unit_surrendered',unit_id=u['id'],holder_id=holder_id,count=record['count'],captive_id=record['id'])
        enqueue(s,holder['side'],f'{holder_id}: {record["count"]} prisoners taken from {u["id"]}.',
                data=dict(record),kind='captives',sender=holder_id)


def escape(s,emit):
    """Captives held by a unit now routed or lost go free (``escaped``) and
    leave the account; they do not become a unit again.
    Test: `test_captives_escape_when_their_holder_routs`."""
    for record in s.get('captives',()):
        if record['status']!='held':continue
        holder=next(x for x in s['units'] if x['id']==record['holder_id'])
        if holder['strength']>0 and holder['status'] not in GONE:continue
        record.update(status='escaped',escaped_turn=s['turn'])
        holder['captives']-=record['count']
        emit(s,'captives_escaped',captive_id=record['id'],holder_id=holder['id'],count=record['count'])
