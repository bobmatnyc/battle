import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
kinds=sys.argv[2].split(',')
lo=int(sys.argv[3]) if len(sys.argv)>3 else 0
hi=int(sys.argv[4]) if len(sys.argv)>4 else 9999
lim=int(sys.argv[5]) if len(sys.argv)>5 else 260
q='select seq,turn,kind,payload from events where kind in (%s) and turn between ? and ? order by seq'%','.join('?'*len(kinds))
for s,t,k,p in c.execute(q,kinds+[lo,hi]):
    print(s,'t%d'%t,k,p[:lim])
