import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
rows=c.execute('select decision_index,payload from decisions order by 1').fetchall()
p=json.loads(rows[0][1])
def sh(d,pre=''):
    for k,v in d.items():
        if k=='observation': print(pre+k,'<obs>');continue
        if isinstance(v,dict) and len(json.dumps(v))>200: print(pre+k,'{'); sh(v,pre+'  ')
        else: print(pre+k,json.dumps(v)[:300])
sh(p)
print('events kinds');
for r in c.execute('select kind,count(*) from events group by 1'): print(r)
