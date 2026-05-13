"""End-to-end verify: each ui_in[i] pad must connect to exactly ONE
cv-cell's gate (via the new strap+route)."""
import gdstk, time
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"

L = {(67,20):'li1',(67,44):'mcon',(68,20):'M1',(68,44):'via1',
     (69,20):'M2',(69,44):'via2',(70,20):'M3',(70,44):'via3',(71,20):'M4'}
CONN = set()
for a,b in [('M4','via3'),('via3','M3'),('M3','via2'),('via2','M2'),
            ('M2','via1'),('via1','M1'),('M1','mcon'),('mcon','li1')]:
    CONN.add((a,b)); CONN.add((b,a))

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])
def touch(a,b,tol=0.001):
    return (a[2]+tol>=b[0] and b[2]+tol>=a[0] and a[3]+tol>=b[1] and b[3]+tol>=a[1])

lib = gdstk.read_gds(V8)
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
            polys.append(((b[0]+ox, b[1]+oy, b[2]+ox, b[3]+oy), 'M1'))

n = len(polys)
print(f"Total polys: {n}")
class UF:
    def __init__(self,n): self.p=list(range(n))
    def find(self,x):
        while self.p[x]!=x: self.p[x]=self.p[self.p[x]]; x=self.p[x]
        return x
    def union(self,a,b):
        ra,rb = self.find(a),self.find(b)
        if ra!=rb: self.p[ra]=rb
uf = UF(n)

# Spatial bucket for speed
bucket = {}
bs = 5.0
for i,(b,_) in enumerate(polys):
    for bx in range(int(b[0]/bs)-1, int(b[2]/bs)+2):
        for by in range(int(b[1]/bs)-1, int(b[3]/bs)+2):
            bucket.setdefault((bx,by),[]).append(i)

t0 = time.time()
for (bx,by), idxs in bucket.items():
    for i_idx,i in enumerate(idxs):
        bi,li = polys[i]
        for j in idxs[i_idx+1:]:
            bj,lj = polys[j]
            if li==lj:
                if touch(bi,bj): uf.union(i,j)
            elif (li,lj) in CONN:
                if touch(bi,bj): uf.union(i,j)
print(f"UF done in {time.time()-t0:.1f}s")

# Find ui_in pad components
ui_seed = {}
for lab in top.labels:
    if not lab.text.startswith("ui_in["): continue
    x,y = lab.origin
    for i,(b,l) in enumerate(polys):
        if l=='M4' and b[0]-0.5<=x<=b[2]+0.5 and b[1]-0.5<=y<=b[3]+0.5:
            ui_seed[lab.text] = i; break

# Find cv-cell components
cv_seed = {}
cv_origins = [(175.8,96.05),(186.8,96.05),(175.8,118.05),(186.8,118.05),
              (175.8,140.05),(186.8,140.05),(175.8,162.05),(186.8,162.05)]
for (cx,cy) in cv_origins:
    # find a top-level paddle for this cell (top-paddle at y=cy+10.275)
    target_y = cy + 10.275
    for i,(b,l) in enumerate(polys):
        if l=='M1' and abs((b[1]+b[3])/2 - target_y) < 0.1:
            cx_lo = b[0]; cx_hi = b[2]
            if cx-1 < (cx_lo+cx_hi)/2 < cx+1:
                cv_seed[(cx,cy)] = i; break

print(f"\nui_in pad components:")
for name in sorted(ui_seed.keys()):
    root = uf.find(ui_seed[name])
    print(f"  {name}: root={root}")

print(f"\ncv-cell gate components:")
for cell in cv_origins:
    if cell in cv_seed:
        root = uf.find(cv_seed[cell])
        print(f"  cv{cell}: root={root}")

# Check: which ui_in pads share root with which cv-cell
print(f"\nConnectivity matrix (ui_in pad → cv-cell match if same root):")
for name in sorted(ui_seed.keys()):
    ui_root = uf.find(ui_seed[name])
    matches = [cell for cell in cv_origins if cell in cv_seed and uf.find(cv_seed[cell]) == ui_root]
    if matches:
        print(f"  {name}  →  cv-cell {matches[0]} ✓")
    else:
        print(f"  {name}  →  (floating, comp size = {sum(1 for i in range(n) if uf.find(i)==ui_root)} polys)")
