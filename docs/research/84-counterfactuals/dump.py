import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
full=len(sys.argv)>2
tot=[0,0,0.0]
for i,p in c.execute('select decision_index,payload from decisions order by 1'):
    d=json.loads(p)
    o=d.get('orders') or []
    s=' '.join('%s:%s%s'%(x.get('unit_id'),x.get('stance'),('>'+','.join(map(str,x['destination']))) if x.get('destination') else '') for x in o)
    u=d.get('usage') or {}
    if d.get('model'):
        tot[0]+=u.get('prompt_tokens',0);tot[1]+=u.get('completion_tokens',0);tot[2]+=u.get('cost',0)
    print(i,'t',d.get('turn'),d.get('side'),'M' if d.get('model') else 'S',u.get('prompt_tokens',''),u.get('completion_tokens',''),u.get('cost',''),'|',s, d.get('instructions','') or '')
    if full and d.get('text'): print('    TEXT:',d['text'][:700])
print('model totals in/out/cost',tot)
