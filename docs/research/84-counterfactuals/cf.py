"""Counterfactual LRT: replay the recorded model orders (call k -> orders) with edits. Local, no network."""
import json,sqlite3,sys,tempfile
from pathlib import Path
sys.path.insert(0,'/Users/masa/trusty-mpm-projects/bobmatnyc/battle/.claude/worktrees/agent-a3710adf3b45ab492/apps/poc')
from battle.bootstrap import build_headless
A='/Users/masa/trusty-mpm-projects/bobmatnyc/battle/apps/poc/artifacts/d37-option-a-f1f4210/little-round-top-1.sqlite'
c=sqlite3.connect('file:'+A+'?mode=ro',uri=True)
rec=[]
for (p,) in c.execute('select payload from decisions order by decision_index'):
    d=json.loads(p)
    if d.get('model'): rec.append(d['orders'])
class Fake:
    available=True; model='fake/cf'; effort='high'
    def __init__(self,variant):
        self.n=0; self.variant=variant
    def request(self,instruction,payload):
        k=self.n; self.n+=1
        orders=[dict(o) for o in rec[k]] if k<len(rec) else []
        v=self.variant
        if v=='none': orders=[]
        elif v=='no-u1-move-t0' and k==0: orders=[o for o in orders if o['unit_id']!='U1']
        elif v=='only-u1-move-t0': orders=orders if k==0 else []
        return {'text':'cf','orders':orders},{'model':self.model,'usage':{'prompt_tokens':1,'completion_tokens':1,'cost':0.0},'response_id':'cf%d'%k}
for v in sys.argv[1:]:
    with tempfile.TemporaryDirectory() as tmp:
        r=build_headless(Path(tmp)/'g.sqlite',player_provider='openrouter',provider=Fake(v))
        out=r.run()
        print(v,out['winner'],out['turns'],out['replay'])
