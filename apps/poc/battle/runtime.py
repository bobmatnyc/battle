"""Recorded input transitions: replay never calls a model or wall clock."""
from copy import deepcopy
from . import engine,formations,recommendations,standing

def apply(state,action):
    """Why: one recorded action changes one snapshot, identically on replay.
    What: applies ``action`` to a copy of ``state``. Player actions (orders,
    formation, recommendation, standing) act for the snapshot's player side:
    Union before poc-9, the scenario's ``player_side`` from poc-9.
    Test: `test_renamed_side_duel_runs_headless_and_replays`.
    """
    s=deepcopy(state)
    player=engine.player_side(s)
    if s['status']!='active' and action['type']!='chat':
        raise ValueError('Battle complete. Start a new battle.')
    if action['type']=='orders':
        for order in action['orders']:
            engine.issue(s,player,order,'human')
    elif action['type']=='formation':
        if s.get('rules')=='poc-4':
            from . import formations_v4
            formations_v4.request(s,player,action['instruction'])
        elif s.get('rules')=='poc-5':
            from . import formations_v5
            formations_v5.request(s,player,action['instruction'])
        elif s.get('rules')=='poc-6':
            from . import formations_v6
            formations_v6.request(s,player,action['instruction'])
        elif s.get('rules')=='poc-7':
            from . import formations_v7
            formations_v7.request(s,player,action['instruction'])
        else:formations.request(s,player,action['instruction'])
    elif action['type']=='recommendation':
        if s.get('rules')=='poc-7':
            from . import recommendations_v7
            recommendations_v7.respond(s,player,action['recommendation_id'],action['response'])
        else:recommendations.respond(s,player,action['recommendation_id'],action['response'])
    elif action['type']=='standing':
        standing.issue(s,player,action['instruction'])
    elif action['type']=='advance':
        decision=action.get('decision')
        if decision:record_decision(s,decision)
        engine.advance(s)
    elif action['type']=='decision':
        # Player-side decision committed before the next advance; added for
        # headless player runs, so no earlier save contains this action type.
        record_decision(s,action['decision'])
    elif action['type']=='chat':
        decision=deepcopy(action['decision'])
        s['decisions'].append(decision)
        engine.emit(s,'staff_consulted',source=decision['source'],decision_index=len(s['decisions'])-1)
    else:
        raise ValueError('Unknown action.')
    s['revision']+=1
    s['last_action']=deepcopy(action)
    return s

def record_decision(s,decision):
    """Why: a decision must issue orders for the side that made it.
    What: appends the decision, emits ``commander_decision`` and issues its
    orders for ``decision['side']``. Decisions recorded before sides were named
    carry no ``side`` and keep their original Confederate effect, so old saves
    replay unchanged. Test: `test_decision_orders_are_issued_for_their_side`,
    `test_decision_without_side_replays_as_confederate`.
    """
    side=decision.get('side','confederate')
    if side not in engine.sides(s):raise ValueError('Unknown decision side.')
    s['decisions'].append(deepcopy(decision))
    engine.emit(s,'commander_decision',source=decision['source'],decision_index=len(s['decisions'])-1)
    for order in decision['orders']:
        engine.issue(s,side,order,decision['source'])

def verify_replay(store,gid):
    """Compatibility entry point; replay never constructs inference dependencies."""
    from .replay import verify
    return verify(store,gid,apply)
