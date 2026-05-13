"""Trace the connection between ui_in[2] and ui_in[3] (shouldn't be connected)."""
import gdstk
GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"

L = {(67,20):"li1",(67,44):"mcon",(68,20):"M1",(68,44):"via1",
     (69,20):"M2",(69,44):"via2",(70,20):"M3",(70,44):"via3",(71,20):"M4"}
CONN = set()
for a,b in [("M4","via3"),("via3","M3"),("M3","via2"),("via2","M2"),
            ("M2","via1"),("via1","M1"),("M1","mcon"),("mcon","li1")]:
    CONN.add((a,b)); CONN.add((b,a))

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])
def touch(a,b,tol=0.001):
    return (a[2]+tol>=b[0] and b[2]+tol>=a[0] and a[3]+tol>=b[1] and b[3]+tol>=a[1])

lib = gdstk.read_gds(GDS)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
cv_tmpl = next(c for c in lib.cells if "lvt_4WRHDT" in c.name)
tmpl_paddles = []
for p in cv_tmpl.polygons:
    if (p.layer, p.datatype) != (68,20): continue
    bb = p.bounding_box()
    if bb is None: continue
    if (bb[1][0]-bb[0][0]) < 1 and (bb[1][1]-bb[0][1]) < 1:
        tmpl_paddles.append((bb[0][0],bb[0][1],bb[1][0],bb[1][1]))

polys = []
for p in top.polygons:
    k = (p.layer, p.datatype)
    if k not in L: continue
    b = get_bb(p)
    if b: polys.append((b, L[k]))
for r in top.references:
    if r.cell and "lvt_4WRHDT" in r.cell.name:
        ox, oy = r.origin
        for b in tmpl_paddles:
            polys.append(((b[0]+ox, b[1]+oy, b[2]+ox, b[3]+oy), "M1"))

n = len(polys)
# BFS from ui_in[2] pad
ui_seed = {}
for lab in top.labels:
    if not lab.text.startswith("ui_in["): continue
    x,y = lab.origin
    for i,(b,l) in enumerate(polys):
        if l=="M4" and b[0]-0.5<=x<=b[2]+0.5 and b[1]-0.5<=y<=b[3]+0.5:
            ui_seed[lab.text] = i; break

start = ui_seed["ui_in[2]"]
target = ui_seed["ui_in[3]"]

# Build adjacency
adj = [[] for _ in range(n)]
bucket = {}
bs = 5.0
for i,(b,_) in enumerate(polys):
    for bx in range(int(b[0]/bs)-1, int(b[2]/bs)+2):
        for by in range(int(b[1]/bs)-1, int(b[3]/bs)+2):
            bucket.setdefault((bx,by),[]).append(i)

for (bx,by), idxs in bucket.items():
    for i_idx,i in enumerate(idxs):
        bi,li = polys[i]
        for j in idxs[i_idx+1:]:
            bj,lj = polys[j]
            if li==lj:
                if touch(bi,bj):
                    adj[i].append(j); adj[j].append(i)
            elif (li,lj) in CONN:
                if touch(bi,bj):
                    adj[i].append(j); adj[j].append(i)

# BFS for shortest path
from collections import deque
parent = {start: None}
q = deque([start])
while q:
    u = q.popleft()
    if u == target: break
    for v in adj[u]:
        if v not in parent:
            parent[v] = u
            q.append(v)

if target not in parent:
    print("No path found")
else:
    path = []
    u = target
    while u is not None:
        path.append(u)
        u = parent[u]
    path.reverse()
    print(f"Path from ui_in[2] to ui_in[3]: {len(path)} polys")
    for i,p in enumerate(path):
        b, l = polys[p]
        print(f"  {i:2d}: {l:5s}  ({b[0]:.3f},{b[1]:.3f})-({b[2]:.3f},{b[3]:.3f})")
