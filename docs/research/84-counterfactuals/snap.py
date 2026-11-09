import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
ids=sys.argv[2].split(',')
step=int(sys.argv[3]) if len(sys.argv)>3 else 1
rows=c.execute('select turn,revision,state from snapshots order by revision').fetchall()
last=-1
first=True
for t,r,st in rows:
    if t==last or (t%step and t!=rows[-1][0]): continue
    last=t
    s=json.loads(st)
    if first:
        print('state keys',list(s.keys())[:40]); u0=s['units'][0]; print('unit keys',list(u0.keys())); first=False
    out=[]
    for u in s['units']:
        if u['id'] in ids:
            out.append('%s@%s,%s %s st=%s mo=%s %s'%(u['id'],u['pos'][0],u['pos'][1],u['status'],u.get('strength'),u.get('morale'),u.get('stance','')))
    print('t%d r%d cap=%s | '%(t,r,s.get('capture'))+' ; '.join(out))
