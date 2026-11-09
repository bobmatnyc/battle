"""Counterfactual Gergovia: swap the first model call's orders between the two recorded games. Local, no network."""
import json,sqlite3,sys,tempfile
from pathlib import Path
sys.path.insert(0,'/Users/masa/trusty-mpm-projects/bobmatnyc/battle/.claude/worktrees/agent-a3710adf3b45ab492/apps/poc')
from battle.bootstrap import build_headless
A='/Users/masa/trusty-mpm-projects/bobmatnyc/battle/apps/poc/artifacts/d37-option-a-f1f4210/concord-north-bridge-%d.sqlite'
def load(g):
    c=sqlite3.connect('file:'+A%g+'?mode=ro',uri=True)
    rec=[]
    for (p,) in c.execute('select payload from decisions order by decision_index'):
        d=json.loads(p)
        if d.get('model'): rec.append(d['orders'])
    return rec
R={1:load(1),2:load(2)}
class Fake:
    available=True; model='fake/cf'; effort='high'
    def __init__(self,seq):
        self.n=0; self.seq=seq
    def request(self,instruction,payload):
        k=self.n; self.n+=1
        orders=[dict(o) for o in self.seq[k]] if k<len(self.seq) else []
        return {'text':'cf','orders':orders},{'model':self.model,'usage':{'prompt_tokens':1,'completion_tokens':1,'cost':0.0},'response_id':'cf%d'%k}
variants={
 'g1-recorded':R[1],
 'g2-recorded':R[2],
 'g1-with-g2-call0':[R[2][0]]+R[1][1:],
 'g2-with-g1-call0':[R[1][0]]+R[2][1:],
 'no-orders':[],
}
for v in sys.argv[1:]:
    with tempfile.TemporaryDirectory() as tmp:
        r=build_headless(Path(tmp)/'g.sqlite',player_provider='openrouter',provider=Fake(variants[v]),scenario_id='concord-north-bridge')
        out=r.run()
        print(v,out['winner'],out['turns'],out['replay']['status'])
