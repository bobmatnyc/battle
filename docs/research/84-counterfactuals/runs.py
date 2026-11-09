import json
for l in open('/Users/masa/trusty-mpm-projects/bobmatnyc/battle/apps/poc/artifacts/d37-option-a-f1f4210/runs.jsonl'):
    r=json.loads(l)
    p=r['pins']
    print(r['entry'],r['game'],'side',p['player_side'],'turns',r['turns'],'win',r['winner'],'dec',r['player_decisions'],'cost',r['cost_usd'],{k:v for k,v in r.items() if k not in('pins','db','db_sha256','entry','game','player_decisions','cost_usd','turns','winner','model','plan_item')})
