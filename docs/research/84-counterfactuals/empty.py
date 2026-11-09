import json,sqlite3,glob
A='/Users/masa/trusty-mpm-projects/bobmatnyc/battle/apps/poc/artifacts/d37-option-a-f1f4210/'
n=0;e=0;ce=0.0;ct=0.0
for f in sorted(glob.glob(A+'*.sqlite')):
    c=sqlite3.connect('file:'+f+'?mode=ro',uri=True)
    for (p,) in c.execute('select payload from decisions'):
        d=json.loads(p)
        if not d.get('model'): continue
        n+=1;ct+=d['usage']['cost']
        if not d['orders']: e+=1;ce+=d['usage']['cost']
print(n,e,round(ce,4),round(ct,4))
