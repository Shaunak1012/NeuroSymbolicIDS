"""
kg_visualize.py — Obsidian-style interactive view of the Knowledge Graph.

Emits a SELF-CONTAINED HTML file (no CDN, no external assets — everything inline)
with a force-directed graph in the Obsidian aesthetic: dark canvas, glowing nodes
sized by degree, coloured by node type, hover-to-highlight-neighbourhood, drag,
zoom and pan.

Why hand-rolled rather than d3: the published-artifact CSP blocks every external
host, so a CDN import would silently fail. At ~215 nodes an O(n^2) repulsion step
is far cheaper than the download would be anyway.

Reads models/kg.gpickle (produced by kg.py).
Run:  python scripts/kg_visualize.py
Out:  outputs/figures/kg_graph.html
"""
import os
import json
import pickle
import numpy as np

import paths

TAG = os.environ.get("KG_TAG", "kg")
TOP_EDGES = int(os.environ.get("KG_TOP_EDGES", 3))   # per cluster, per relation

with open(os.path.join(paths.MODELS, f"{TAG}.gpickle"), "rb") as f:
    blob = pickle.load(f)
G, burst, emerging = blob["graph"], blob["burstiness"], set(blob["emerging"])

# ---- nodes -------------------------------------------------------------------
nodes, index = [], {}
for n, d in G.nodes(data=True):
    kind = d["kind"]
    cid = d.get("cid")
    activity = float(d.get("activity", 0.0))
    label = n.split(":", 1)[1]
    is_em = kind == "Cluster" and cid in emerging
    index[n] = len(nodes)
    nodes.append({
        "id": n, "label": label, "kind": kind,
        "emerging": bool(is_em),
        "burst": round(float(burst[cid]), 2) if cid is not None else None,
        "activity": round(activity, 1),
    })

# ---- edges: keep the strongest few per cluster so the view stays legible ------
edges, kept = [], 0
by_src = {}
for u, v, d in G.edges(data=True):
    by_src.setdefault((u, d["rel"]), []).append((v, d["weight"]))
for (u, rel), lst in by_src.items():
    tot = sum(w for _, w in lst) or 1.0
    for v, w in sorted(lst, key=lambda t: -t[1])[:TOP_EDGES]:
        edges.append({"s": index[u], "t": index[v], "rel": rel,
                      "w": round(w / tot, 3)})
        kept += 1

deg = np.zeros(len(nodes))
for e in edges:
    deg[e["s"]] += 1
    deg[e["t"]] += 1
for i, n in enumerate(nodes):
    n["deg"] = int(deg[i])

payload = json.dumps({"nodes": nodes, "edges": edges}, separators=(",", ":"))
n_em = sum(1 for n in nodes if n["emerging"])
print(f"{len(nodes)} nodes ({n_em} emerging) · {kept} edges (top {TOP_EDGES}/cluster/relation)")

HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>NeuroSymbolic-IDS — Knowledge Graph</title><style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#141416;color:#d7d7db;
  font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;overflow:hidden}
#c{display:block;cursor:grab}#c:active{cursor:grabbing}
.panel{position:fixed;background:rgba(24,24,27,.92);border:1px solid #2e2e33;
  border-radius:10px;padding:12px 14px;backdrop-filter:blur(8px)}
#legend{top:16px;left:16px;min-width:210px}
#legend h1{font-size:13px;font-weight:600;color:#fff;margin-bottom:2px;letter-spacing:.2px}
#legend .sub{font-size:11px;color:#7c7c85;margin-bottom:10px}
.row{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12px}
.dot{width:9px;height:9px;border-radius:50%;flex:none;box-shadow:0 0 7px currentColor}
.hint{font-size:11px;color:#6b6b73;margin-top:10px;border-top:1px solid #2a2a2f;padding-top:8px}
#info{top:16px;right:16px;width:270px;display:none}
#info .t{font-size:13px;font-weight:600;color:#fff;word-break:break-all}
#info .k{font-size:11px;color:#8a8a93;margin-bottom:9px}
#info .m{display:flex;justify-content:space-between;font-size:12px;margin:3px 0}
#info .m span:first-child{color:#8a8a93}
.badge{display:inline-block;font-size:10px;padding:2px 7px;border-radius:20px;
  background:#3a2a12;color:#ffb454;border:1px solid #5a3f18;margin-top:7px}
</style></head><body>
<canvas id="c"></canvas>
<div class="panel" id="legend">
  <h1>Knowledge Graph</h1><div class="sub">adaptive memory · Phase 4</div>
  <div class="row"><span class="dot" style="color:#7c6cf0;background:#7c6cf0"></span>Cluster</div>
  <div class="row"><span class="dot" style="color:#ffb454;background:#ffb454"></span>Cluster — emerging</div>
  <div class="row"><span class="dot" style="color:#4ec9a5;background:#4ec9a5"></span>Behaviour</div>
  <div class="row"><span class="dot" style="color:#f0637c;background:#f0637c"></span>AttackType</div>
  <div class="hint">hover to isolate · drag a node · scroll to zoom<br><span id="stat"></span></div>
</div>
<div class="panel" id="info"></div>
<script>
const DATA=__DATA__;
const C={Cluster:"#7c6cf0",Emerging:"#ffb454",Behaviour:"#4ec9a5",AttackType:"#f0637c"};
const cv=document.getElementById("c"),ctx=cv.getContext("2d");
let W,H,DPR=window.devicePixelRatio||1;
function size(){W=innerWidth;H=innerHeight;cv.width=W*DPR;cv.height=H*DPR;
  cv.style.width=W+"px";cv.style.height=H+"px";ctx.setTransform(DPR,0,0,DPR,0,0);}
size();addEventListener("resize",size);
const N=DATA.nodes,E=DATA.edges;
document.getElementById("stat").textContent=N.length+" nodes · "+E.length+" edges";
// hub nodes (Behaviour/AttackType) start centred; clusters ring the outside
N.forEach((n,i)=>{const hub=n.kind!=="Cluster";const a=i/N.length*Math.PI*2;
  const r=hub?60:Math.min(W,H)*0.34;
  n.x=W/2+Math.cos(a)*r+(Math.random()-.5)*40;
  n.y=H/2+Math.sin(a)*r+(Math.random()-.5)*40;n.vx=0;n.vy=0;
  n.r=n.kind==="Cluster"?(n.emerging?5.5:3.6)+Math.min(n.deg,10)*0.22:9+Math.min(n.deg,40)*0.13;
  n.col=n.kind==="Cluster"?(n.emerging?C.Emerging:C.Cluster):C[n.kind];});
const adj=new Map();E.forEach(e=>{if(!adj.has(e.s))adj.set(e.s,new Set());
  if(!adj.has(e.t))adj.set(e.t,new Set());adj.get(e.s).add(e.t);adj.get(e.t).add(e.s);});
let hover=null,drag=null,zoom=1,px=0,py=0,pan=false,lx=0,ly=0,alpha=1;
function step(){
  // O(n^2) repulsion is fine at this scale and avoids a quadtree dependency
  for(let i=0;i<N.length;i++)for(let j=i+1;j<N.length;j++){
    const a=N[i],b=N[j];let dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy||1;
    if(d2>90000)continue;const d=Math.sqrt(d2),f=(a.kind==="Cluster"&&b.kind==="Cluster"?260:900)/d2;
    const fx=dx/d*f,fy=dy/d*f;a.vx-=fx;a.vy-=fy;b.vx+=fx;b.vy+=fy;}
  E.forEach(e=>{const a=N[e.s],b=N[e.t];let dx=b.x-a.x,dy=b.y-a.y;
    const d=Math.sqrt(dx*dx+dy*dy)||1,f=(d-90)*0.0016*(0.35+e.w);
    const fx=dx/d*f,fy=dy/d*f;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;});
  N.forEach(n=>{n.vx+=(W/2-n.x)*0.0012;n.vy+=(H/2-n.y)*0.0012;
    if(n===drag)return;n.x+=n.vx*alpha;n.y+=n.vy*alpha;n.vx*=0.86;n.vy*=0.86;});
  alpha=Math.max(alpha*0.999,0.25);
}
function draw(){
  ctx.setTransform(DPR,0,0,DPR,0,0);ctx.fillStyle="#141416";ctx.fillRect(0,0,W,H);
  ctx.translate(px,py);ctx.scale(zoom,zoom);
  const near=hover!==null?adj.get(hover)||new Set():null;
  E.forEach(e=>{const a=N[e.s],b=N[e.t];
    const lit=hover!==null&&(e.s===hover||e.t===hover);
    ctx.globalAlpha=hover===null?0.13+e.w*0.22:(lit?0.75:0.03);
    ctx.strokeStyle=lit?(e.rel==="exhibits"?C.Behaviour:C.AttackType):"#8b8b96";
    ctx.lineWidth=lit?1.5:0.6;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();});
  N.forEach((n,i)=>{
    const lit=hover===null||i===hover||(near&&near.has(i));
    ctx.globalAlpha=lit?1:0.12;
    ctx.shadowBlur=lit?(n.emerging?20:11):0;ctx.shadowColor=n.col;
    ctx.fillStyle=n.col;ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,6.2832);ctx.fill();
    ctx.shadowBlur=0;
    if(n.kind!=="Cluster"||(lit&&hover!==null&&zoom>0.8)){
      ctx.globalAlpha=lit?0.95:0.1;ctx.fillStyle="#e8e8ee";
      ctx.font=(n.kind==="Cluster"?"10px":"600 11px")+" -apple-system,Segoe UI,sans-serif";
      ctx.textAlign="center";ctx.fillText(n.label,n.x,n.y-n.r-5);}});
  ctx.globalAlpha=1;
}
(function loop(){step();draw();requestAnimationFrame(loop);})();
function at(ev){const mx=(ev.clientX-px)/zoom,my=(ev.clientY-py)/zoom;
  for(let i=N.length-1;i>=0;i--){const n=N[i];
    if((mx-n.x)**2+(my-n.y)**2<(n.r+5)**2)return i;}return null;}
const info=document.getElementById("info");
cv.addEventListener("mousemove",ev=>{
  if(pan){px+=ev.clientX-lx;py+=ev.clientY-ly;lx=ev.clientX;ly=ev.clientY;return;}
  if(drag){drag.x=(ev.clientX-px)/zoom;drag.y=(ev.clientY-py)/zoom;alpha=1;return;}
  const h=at(ev);if(h===hover)return;hover=h;
  if(h===null){info.style.display="none";return;}
  const n=N[h];info.style.display="block";
  info.innerHTML='<div class="t">'+n.label+'</div><div class="k">'+n.kind+'</div>'+
    '<div class="m"><span>connections</span><span>'+n.deg+'</span></div>'+
    (n.burst!==null?'<div class="m"><span>burstiness</span><span>'+n.burst+'&times;</span></div>':'')+
    (n.activity?'<div class="m"><span>activity</span><span>'+n.activity+'</span></div>':'')+
    (n.emerging?'<div class="badge">EMERGING PATTERN</div>':'');});
cv.addEventListener("mousedown",ev=>{const h=at(ev);
  if(h!==null){drag=N[h];alpha=1;}else{pan=true;lx=ev.clientX;ly=ev.clientY;}});
addEventListener("mouseup",()=>{drag=null;pan=false;});
cv.addEventListener("wheel",ev=>{ev.preventDefault();
  const f=ev.deltaY<0?1.1:0.9,mx=ev.clientX,my=ev.clientY;
  px=mx-(mx-px)*f;py=my-(my-py)*f;zoom*=f;},{passive:false});
</script></body></html>"""

out = os.path.join(paths.FIGURES, "kg_graph.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(HTML.replace("__DATA__", payload))
print(f"wrote {out}  ({os.path.getsize(out)/1024:.0f} KB, fully self-contained)")
