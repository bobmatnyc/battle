"""Generic counterfactual: argv[1]=entry, argv[2]=recorded|none. Replays recorded model orders (game 1) or none. Local, no network."""
import json,sqlite3,sys,tempfile
from pathlib import Path
sys.path.insert(0,'/Users/masa/trusty-mpm-projects/bobmatnyc/battle/.claude/worktrees/agent-a3710adf3b45ab492/apps/poc')
from battle.bootstrap import build_headless
entry=sys.argv[1]
A='/Users/masa/trusty-mpm-projects/bobmatnyc/battle/apps/poc/artifacts/d37-option-a-f1f4210/'+entry+'-1.sqlite'
c=sqlite3.connect('file:'+A+'?mode=ro',uri=True)
rec=[json.loads(p)['orders'] for (p,) in c.execute('select payload from decisions order by decision_index') if json.loads(p).get('model')]
class Fake:
    available=True; model='fake/cf'; effort='high'
    def __init__(self,seq): self.n=0; self.seq=seq
    def request(self,instruction,payload):
        k=self.n; self.n+=1
        orders=[dict(o) for o in self.seq[k]] if k<len(self.seq) else []
        return {'text':'cf','orders':orders},{'model':self.model,'usage':{'prompt_tokens':1,'completion_tokens':1,'cost':0.0},'response_id':'cf%d'%k}
for v in sys.argv[2:]:
    with tempfile.TemporaryDirectory() as tmp:
        r=build_headless(Path(tmp)/'g.sqlite',player_provider='openrouter',provider=Fake(rec if v=='recorded' else []),scenario_id=entry)
        out=r.run()
        print(entry,v,out['winner'],out['turns'],out['replay']['status'])
