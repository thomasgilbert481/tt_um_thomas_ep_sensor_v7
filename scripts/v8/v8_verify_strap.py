"""Verify v8draft: each cv-cell's 4 gate paddles + new strap + via1 + M2
escape are a single connected component, and the 8 cells are NOT shorted
to each other."""
import gdstk, time

V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"

LAY = {(67,20):'li1',(67,44):'mcon',(68,20):'M1',(68,44):'via1',
       (69,20):'M2',(69,44):'via2',(70,20):'M3',(70,44):'via3',(71,20):'M4'}
CONN = set()
for a,b in [('M1','via1'),('via1','M2'),('M2','via2'),('via2','M3'),
            ('M3','via3'),('via3','M4'),('M1','mcon'),('mcon','li1')]:
    CONN.add((a,b)); CONN.add((b,a))

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])

def boxes_touch(a, b, tol=0.001):
    return (a[2]+tol>=b[0] and b[2]+tol>=a[0] and a[3]+tol>=b[1] and b[3]+tol>=a[1])

class UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x]!=x: self.p[x]=self.p[self.p[x]]; x=self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra]=rb

lib = gdstk.read_gds(V8)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
# Also resolve cv-cell internals: each cv-cell's M1 paddles live inside its template.
# We need to ADD them to the polygon list with absolute coords.
cv_template = next(c for c in lib.cells if "lvt_4WRHDT" in c.name)
template_paddles = []
for p in cv_template.polygons:
    if (p.layer, p.datatype) != (68, 20): continue
    bb = p.bounding_box()
    if bb is None: continue
    w = bb[1][0]-bb[0][0]; h = bb[1][1]-bb[0][1]
    if w < 1.0 and h < 1.0:
        template_paddles.append((bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

polys = []
for p in top.polygons:
    key = (p.layer, p.datatype)
    if key not in LAY: continue
    b = get_bb(p)
    if b: polys.append((b, LAY[key]))

# Expand cv-cell instances and add their paddles at absolute coords
cv_origins = []
for r in top.references:
    if r.cell and "lvt_4WRHDT" in r.cell.name:
        ox, oy = r.origin
        cv_origins.append((ox, oy))
        for b in template_paddles:
            abs_bb = (b[0]+ox, b[1]+oy, b[2]+ox, b[3]+oy)
            polys.append((abs_bb, 'M1'))

print(f"Total polys (top + expanded cv-cell paddles): {len(polys)}")
print(f"cv-cells: {len(cv_origins)}")

# UF only on polys within ROI to save time
ROI = (170, 80, 195, 230)
roi_idx = [i for i,(b,_) in enumerate(polys) if b[2]>ROI[0] and b[0]<ROI[2] and b[3]>ROI[1] and b[1]<ROI[3]]
print(f"Polys in ROI {ROI}: {len(roi_idx)}")

n = len(polys)
uf = UF(n)
t0 = time.time()
for i_idx, i in enumerate(roi_idx):
    bi, li = polys[i]
    for j in roi_idx[i_idx+1:]:
        bj, lj = polys[j]
        if li == lj:
            if boxes_touch(bi, bj): uf.union(i, j)
        elif (li, lj) in CONN:
            if boxes_touch(bi, bj): uf.union(i, j)
print(f"UF computed in {time.time()-t0:.1f}s")

# For each cv-cell, find a paddle poly index and report its component
print("\nPer cv-cell, component info of one paddle:")
seen_roots = {}
for (cx, cy) in cv_origins:
    # find a paddle by EXACT y-coordinate of one of this cell's bottom paddles
    target_y = cy - 10.275  # bottom paddle center y
    seed = None
    for i in roi_idx:
        b, l = polys[i]
        if l != 'M1': continue
        bcy = (b[1]+b[3])/2
        if abs(bcy - target_y) < 0.05 and cx-1 < (b[0]+b[2])/2 < cx+1:
            seed = i; break
    if seed is None:
        print(f"  cell ({cx},{cy}): no paddle found at target y={target_y}")
        continue
    root = uf.find(seed)
    if root not in seen_roots:
        seen_roots[root] = []
    seen_roots[root].append((cx, cy))

print(f"\nUnique gate nets (after strapping): {len(seen_roots)}")
for root, cells in seen_roots.items():
    members = [i for i in roi_idx if uf.find(i) == root]
    from collections import Counter
    layer_ct = Counter(polys[i][1] for i in members)
    print(f"  net root={root}: {len(cells)} cv-cell(s) at {cells}, comp size={len(members)}, layers={dict(layer_ct)}")

# DEBUG: print every member of the first component
if seen_roots:
    first_root = next(iter(seen_roots))
    print(f"\nDEBUG: members of net root {first_root} (cell at {seen_roots[first_root]}):")
    for i in roi_idx:
        if uf.find(i) == first_root:
            b, l = polys[i]
            print(f"  {l}: ({b[0]:7.3f},{b[1]:7.3f})-({b[2]:7.3f},{b[3]:7.3f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")
