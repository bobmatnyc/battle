import json,sqlite3,glob,os
A='/Users/masa/trusty-mpm-projects/bobmatnyc/battle/apps/poc/artifacts/d37-option-a-f1f4210/'
rows=[json.loads(l) for l in open(A+'runs.jsonl') if 'entry' in l]
T=[0,0,0,0.0,0,0]
for r in rows:
    db=A+os.path.basename(r['db'])
    c=sqlite3.connect('file:'+db+'?mode=ro',uri=True)
    n=pi=po=0;cost=0.0;ordering=0;orders=0;rt=0;lat=[]
    for (p,) in c.execute('select payload from decisions order by decision_index'):
        d=json.loads(p)
        if not d.get('model'): continue
        u=d['usage'];n+=1;pi+=u['prompt_tokens'];po+=u['completion_tokens'];cost+=u['cost']
        rt+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
        o=d.get('orders') or []
        if o: ordering+=1;orders+=len(o)
        lat.append(d['latency_ms'])
    print('%s-%d side=%s win=%s turns=%d n=%d in=%d out=%d reas=%d cost=%.6f (row %.6f) per=%.5f ord_dec=%d orders=%d maxlat=%.0f'%(r['entry'],r['game'],r['pins']['player_side'],r['winner'],r['turns'],n,pi,po,rt,cost,r['cost_usd'],cost/n,ordering,orders,max(lat)))
    T[0]+=n;T[1]+=pi;T[2]+=po;T[3]+=cost;T[4]+=ordering;T[5]+=orders
print('TOTAL n=%d in=%d out=%d cost=%.6f order_decisions=%d orders=%d per=%.5f'%(T[0],T[1],T[2],T[3],T[4],T[5],T[3]/T[0]))
