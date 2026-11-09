import json,sqlite3,sys
db=sys.argv[1]
c=sqlite3.connect('file:'+db+'?mode=ro',uri=True)
for i,p in c.execute('select decision_index,payload from decisions order by 1'):
    print(i,p[:int(sys.argv[2]) if len(sys.argv)>2 else 600])
