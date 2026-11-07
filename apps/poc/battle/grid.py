"""Pointy topped odd-row hexes. Distances are in cells; edges are 50 m."""
import heapq
import math

COLS, ROWS, RADIUS = 24, 21, 25.5
METRES_PER_HEX = 50

def key(pos):
    return f'{pos[0]},{pos[1]}'

def valid(pos):
    return (isinstance(pos, (list, tuple)) and len(pos) == 2
            and all(type(n) is int for n in pos)
            and 0 <= pos[0] < COLS and 0 <= pos[1] < ROWS)

def cube(pos):
    x = pos[0] - (pos[1] - (pos[1] & 1)) // 2
    z = pos[1]
    return x, -x-z, z

def distance(a, b):
    return max(abs(x-y) for x, y in zip(cube(a), cube(b)))

def center(pos):
    return ((pos[0] + .5*(pos[1] & 1)) * math.sqrt(3)*RADIUS + 24,
            pos[1]*1.5*RADIUS + 26)

def neighbors(pos):
    c, r = pos
    offsets = [(1,0),(-1,0),(0,1),(0,-1),(1 if r&1 else -1,1),(1 if r&1 else -1,-1)]
    return [[c+dc,r+dr] for dc,dr in offsets if valid([c+dc,r+dr])]

def cost(cells, a, b):
    ta, tb = cells[key(a)], cells[key(b)]
    movement=70 if list(b) in ta.get('road_neighbors',[]) else tb['move_cost']
    return movement + max(0, tb['elevation']-ta['elevation']) * 3

def passable(cell):
    """poc-13: impassable water (``water``) is crossed only at a ``crossing``
    (bridge or ford). Cells without ``water`` (every earlier edition) pass.
    docs/research/53: a bridge whose ``bridge_state`` is ``destroyed`` does not."""
    if cell.get('bridge_state')=='destroyed':return False
    return not cell.get('water') or bool(cell.get('crossing'))

def path(cells, start, goal, blocked=()):
    if not valid(start) or not valid(goal):
        raise ValueError('Destination is outside the battlefield.')
    heuristic=70 if any(c.get('road_neighbors') for c in cells.values()) else 100
    frontier = [(0, tuple(start))]
    came, spent = {tuple(start): None}, {tuple(start): 0}
    while frontier:
        _, current = heapq.heappop(frontier)
        if list(current) == goal:
            break
        # poc-10: a cell lists the neighbours behind a wall or shut gate.
        walls = cells[key(current)].get('walls', ())
        for nxt in neighbors(current):
            if key(nxt) in blocked and nxt != goal or nxt in walls or not passable(cells[key(nxt)]):
                continue
            nt = tuple(nxt)
            nc = spent[current] + cost(cells, current, nxt)
            if nt not in spent or nc < spent[nt]:
                spent[nt], came[nt] = nc, current
                heapq.heappush(frontier,(nc + heuristic*distance(nxt,goal),nt))
    if tuple(goal) not in came:
        return []
    route, node = [], tuple(goal)
    while node != tuple(start):
        route.append(list(node))
        node = came[node]
    return list(reversed(route))

def line(a, b):
    n = distance(a, b)
    if not n:
        return [list(a)]
    ac, bc = cube(a), cube(b)
    result = []
    for i in range(n+1):
        v = [ac[j] + (bc[j]-ac[j])*i/n for j in range(3)]
        rounded = [round(x) for x in v]
        idx = max(range(3), key=lambda j: abs(rounded[j]-v[j]))
        rounded[idx] = -sum(rounded[j] for j in range(3) if j != idx)
        x, _, z = rounded
        result.append([x+(z-(z&1))//2,z])
    return result

def visible(cells, a, b):
    d = distance(a,b)
    if d > 7:
        return False
    if d <= 1:
        return True
    ray = line(a,b)
    ah, bh = cells[key(a)]['elevation']+2, cells[key(b)]['elevation']+2
    woods = 0
    for i,p in enumerate(ray[1:-1],1):
        terrain = cells.get(key(p))
        if terrain is None:  # off-grid points on a sight line are skipped (Architect ruling 2026-11-07, option c)
            continue
        if terrain['elevation']+terrain.get('obstacle_height',0) > ah+(bh-ah)*i/d+2:
            return False
        woods += terrain['terrain'] == 'woods'
    return woods < 4
