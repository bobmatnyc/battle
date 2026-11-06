"""Local design diagnostics: no database, UI, model calls or credentials."""
import json
import random
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from battle import engine, grid, recon, runtime, scenario
from battle.adapters.openrouter import DisabledProvider
from battle.adapters.rules import RulesSimulation
from battle.command_policy import fallback_orders
from battle.services.commander import CommanderService


def tactical_probe(plan):
    state = scenario.create()
    commander = CommanderService(RulesSimulation(), DisabledProvider())
    sent = 0
    while state['status'] == 'active':
        orders = []
        decision = None
        if state['turn'] % 3 == 0:
            friendly = engine.view(state, 'union')
            if plan == 'scripted':
                orders = fallback_orders(friendly)
            elif plan == 'move_to_rear' and state['turn'] == 0:
                orders = [dict(unit_id=u['id'], stance='move', destination=[10+i,4])
                          for i,u in enumerate(friendly['units'])]
            # 'initial_positions' leaves local commanders under their starting missions.
            if orders:
                sent += len(orders)
                state = runtime.apply(state, dict(type='orders', orders=orders))
            decision = commander.decide(state, engine.computer_side(state), mode='scripted')
        state = runtime.apply(state, dict(type='advance', decision=decision))
    return dict(plan=plan, winner=state['winner'], reason=state['reason'],
                elapsed_seconds=state['turn'] * state['seconds_per_turn'], union_orders=sent,
                strength={side:sum(u['strength'] for u in state['units'] if u['side']==side)
                          for side in scenario.SIDES})


def scan_probe(count):
    state = scenario.create()
    cells = [[x,y] for y in range(grid.ROWS) for x in range(grid.COLS)]
    random.Random(1863).shuffle(cells)  # Fixture placement only.
    state['units'] = [scenario.unit(str(i),scenario.SIDES[i % 2],str(i),cells[i])
                      for i in range(count)]
    samples = []
    for _ in range(8):
        state['recon_memory'] = {}
        start = perf_counter_ns()
        sightings = recon.scan(state)
        samples.append((perf_counter_ns() - start) / 1_000_000)
    return dict(units=count, directed_sightings=sum(map(len,sightings.values())),
                median_scan_ms=round(statistics.median(samples[1:]),3))


if __name__ == '__main__':
    print(json.dumps(dict(rules=scenario.RULES_VERSION, python=sys.version.split()[0],
                          policies=[tactical_probe(p) for p in ('scripted','initial_positions','move_to_rear')],
                          reconnaissance=[scan_probe(n) for n in (6,24,96)]),indent=2))
