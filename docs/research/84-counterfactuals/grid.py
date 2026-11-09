import sys
sys.path.insert(0,'/Users/masa/trusty-mpm-projects/bobmatnyc/battle/.claude/worktrees/agent-a3710adf3b45ab492/apps/poc')
from battle import grid
print('neighbors of 11,15',grid.neighbors((11,15)))
for p in [(11,14),(13,15),(10,13),(11,13),(12,14),(12,13),(12,12),(13,14),(13,12),(10,15),(10,16),(13,13)]:
    print(p,grid.distance(p,(11,15)))
