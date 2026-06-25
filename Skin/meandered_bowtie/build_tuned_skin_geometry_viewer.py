"""Build an HTML geometry viewer for the tuned Slide-12 skin simulation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AIR_BOWTIE = ROOT / "Air" / "meandered_bowtie"
sys.path.insert(0, str(AIR_BOWTIE))

from dxf_utils import parse_polylines  # noqa: E402


DXF = ROOT / "dxf" / "Meandered_Bowtie_v1.0.dxf"
OUT = Path(__file__).resolve().parent
HTML_OUT = OUT / "meandered_bowtie_skin_tuned_geometry_viewer.html"

# Must match Skin/meandered_bowtie/simulate_meandered_bowtie_skin.py.
ROGERS_T_MM = 1.27
SKIN_MARGIN_MM = 12.0
SKIN_T_MM = 20.0
AIR_PAD_XY_MM = 25.0
AIR_PAD_TOP_MM = 35.0
AIR_PAD_BOTTOM_MM = 10.0

TUNED_PORT = {
    "name": "tuned Slide-12 vertical CPW lumped port",
    "x0": -0.8925,
    "x1": 0.8925,
    "y": 1.4500,
    "z0": -ROGERS_T_MM,
    "z1": 0.0,
    "zref_ohm": 10.0,
    "height_override_mm": 0.62,
    "maxh_mm": 0.50,
}


def _pack(poly):
    return {
        "layer": poly.layer,
        "points": poly.ccw_points_mm(),
        "bbox": poly.bbox_mm,
        "area": poly.area_mm2,
    }


def build_payload() -> dict:
    polylines = parse_polylines(DXF)
    rogers = [p for p in polylines if "rogers" in p.layer.lower()]
    pec = [p for p in polylines if p.layer.lower() == "pec"]
    if not rogers or len(pec) < 2:
        raise RuntimeError("Expected one Rogers outline and two PEC loops in DXF.")

    main_metal = min(pec, key=lambda p: abs(p.area_mm2))
    gray_region = max(pec, key=lambda p: abs(p.area_mm2))
    xmin, ymin, xmax, ymax = rogers[0].bbox_mm

    return {
        "dxf_name": DXF.name,
        "unit": "mm",
        "rogers": _pack(rogers[0]),
        "main_metal": _pack(main_metal),
        "gray_region": _pack(gray_region),
        "side_metal": {"outer": _pack(rogers[0]), "holes": [_pack(gray_region)]},
        "port": TUNED_PORT,
        "stack": {
            "board": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "z0": -ROGERS_T_MM, "z1": 0.0},
            "skin": {
                "xmin": xmin - SKIN_MARGIN_MM,
                "ymin": ymin - SKIN_MARGIN_MM,
                "xmax": xmax + SKIN_MARGIN_MM,
                "ymax": ymax + SKIN_MARGIN_MM,
                "z0": -(ROGERS_T_MM + SKIN_T_MM),
                "z1": -ROGERS_T_MM,
            },
            "air": {
                "xmin": xmin - AIR_PAD_XY_MM,
                "ymin": ymin - AIR_PAD_XY_MM,
                "xmax": xmax + AIR_PAD_XY_MM,
                "ymax": ymax + AIR_PAD_XY_MM,
                "z0": -(ROGERS_T_MM + SKIN_T_MM + AIR_PAD_BOTTOM_MM),
                "z1": AIR_PAD_TOP_MM,
            },
        },
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Meandered Bowtie tuned skin geometry viewer</title>
  <style>
    body { margin:0; background:#f5f7fb; color:#1f2937; font-family:Arial,Helvetica,sans-serif; }
    main { max-width:1240px; margin:0 auto; padding:22px; }
    h2 { margin:0 0 6px; }
    p { line-height:1.42; }
    canvas {
      width:100%; height:760px; display:block; background:linear-gradient(#fff,#edf2f8);
      border:1px solid #d5dce8; border-radius:14px; box-shadow:0 8px 30px rgba(20,31,50,.08);
      cursor:grab;
    }
    canvas:active { cursor:grabbing; }
    .toolbar { display:flex; flex-wrap:wrap; gap:10px 16px; align-items:center; margin:12px 0 14px; font-size:14px; }
    button { border:1px solid #c8d0dd; background:#fff; border-radius:8px; padding:7px 10px; cursor:pointer; }
    button:hover { background:#eef3fb; }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(235px,1fr)); gap:10px; margin-top:14px; }
    .card { background:#fff; border:1px solid #d8deea; border-radius:10px; padding:10px 12px; font-size:14px; line-height:1.38; }
    .sw { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }
    code { background:#eef2f7; padding:1px 4px; border-radius:4px; }
  </style>
</head>
<body>
<main>
  <h2>Meandered Bowtie on skin — tuned Slide-12 geometry</h2>
  <p>
    Drag to rotate in 3D mode. Turn on <b>2D ruler mode</b> and click two points to measure top-view distance in millimeters.
    The red vertical sheet is the tuned CPW-style lumped port used in the latest simulation.
  </p>
  <div class="toolbar">
    <label><input id="showAir" type="checkbox" checked /> air box</label>
    <label><input id="showSkin" type="checkbox" checked /> skin block</label>
    <label><input id="showRogers" type="checkbox" checked /> Rogers board</label>
    <label><input id="showSide" type="checkbox" checked /> side metal</label>
    <label><input id="showMain" type="checkbox" checked /> main metal</label>
    <label><input id="showPort" type="checkbox" checked /> tuned feed port</label>
    <label><input id="showLabels" type="checkbox" checked /> labels</label>
    <label><input id="rulerMode" type="checkbox" /> 2D ruler mode</label>
    <button id="clearRuler">Clear ruler</button>
    <button id="isoView">Iso view</button>
    <button id="topView">Top view</button>
    <button id="resetView">Reset view</button>
  </div>
  <canvas id="viewer"></canvas>
  <div class="cards">
    <div class="card"><span class="sw" style="background:#8bb7ff"></span>Air box: simulation boundary/ABC region.</div>
    <div class="card"><span class="sw" style="background:#d59adf"></span>Skin: tabulated <code>skin_Er.tab</code> and <code>skin_cond.tab</code>, 20 mm thick.</div>
    <div class="card"><span class="sw" style="background:#aaa"></span>Rogers board: 42 × 38.5 mm, thickness 1.27 mm, Er=10.2 assumption.</div>
    <div class="card"><span class="sw" style="background:#d99655"></span>Orange: PEC metal regions from DXF interpretation.</div>
    <div class="card"><span class="sw" style="background:#e23b3b"></span>Tuned feed: vertical x-z port, x=-0.8925…+0.8925 mm, y=1.45 mm, Zref=10 Ω, height override=0.62 mm.</div>
  </div>
</main>

<script>
const DATA = __DATA__;
const canvas = document.getElementById("viewer");
const ctx = canvas.getContext("2d");
const ui = {
  air: document.getElementById("showAir"),
  skin: document.getElementById("showSkin"),
  rogers: document.getElementById("showRogers"),
  side: document.getElementById("showSide"),
  main: document.getElementById("showMain"),
  port: document.getElementById("showPort"),
  labels: document.getElementById("showLabels"),
  ruler: document.getElementById("rulerMode"),
};

let yaw = -0.62, pitch = 0.42, zoom = 1.0, dragging = false, last = {x:0,y:0}, rulerPts = [];
const board = DATA.stack.board, skin = DATA.stack.skin, air = DATA.stack.air, port = DATA.port;
const cx = (air.xmin + air.xmax) / 2, cy = (air.ymin + air.ymax) / 2, cz = (air.z0 + air.z1) / 2;

function resize() {
  const r = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0); draw();
}
function tr3(p) {
  let x = p[0] - cx, y = p[1] - cy, z = p[2] - cz;
  const cyw = Math.cos(yaw), syw = Math.sin(yaw);
  const x1 = x * cyw - y * syw, y1 = x * syw + y * cyw;
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  return {x:x1, y:y1*cp - z*sp, z:y1*sp + z*cp};
}
function pr(t,s,w,h) { return {x:w/2 + t.x*s, y:h/2 - t.z*s}; }
function allScale3(w,h) {
  return Math.min(w / ((air.xmax-air.xmin)*1.65), h / ((air.ymax-air.ymin + air.z1-air.z0)*1.2)) * zoom;
}
function scale2(w,h) { return Math.min(w/(air.xmax-air.xmin+8), h/(air.ymax-air.ymin+8)); }
function w2s(p,w,h) { const s=scale2(w,h); return {x:w/2+(p[0]-cx)*s, y:h/2-(p[1]-cy)*s}; }
function s2w(x,y,w,h) { const s=scale2(w,h); return [cx+(x-w/2)/s, cy-(y-h/2)/s]; }

function boxVerts(b) {
  return [[b.xmin,b.ymin,b.z0],[b.xmax,b.ymin,b.z0],[b.xmax,b.ymax,b.z0],[b.xmin,b.ymax,b.z0],
          [b.xmin,b.ymin,b.z1],[b.xmax,b.ymin,b.z1],[b.xmax,b.ymax,b.z1],[b.xmin,b.ymax,b.z1]];
}
function drawBox(b, style, s,w,h, fillTop=false) {
  const v = boxVerts(b).map(p => pr(tr3(p),s,w,h));
  const edges = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  if (fillTop) {
    ctx.beginPath(); ctx.moveTo(v[4].x,v[4].y); [5,6,7].forEach(i=>ctx.lineTo(v[i].x,v[i].y)); ctx.closePath();
    ctx.fillStyle = style.fill; ctx.fill();
  }
  ctx.strokeStyle = style.stroke; ctx.lineWidth = style.lineWidth || 1.2;
  for (const [a,b2] of edges) { ctx.beginPath(); ctx.moveTo(v[a].x,v[a].y); ctx.lineTo(v[b2].x,v[b2].y); ctx.stroke(); }
}
function path3(points,s,w,h,z,holes=[]) {
  const pts = points.map(p => pr(tr3([p[0],p[1],z]),s,w,h));
  ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y); for (let i=1;i<pts.length;i++) ctx.lineTo(pts[i].x,pts[i].y); ctx.closePath();
  for (const hole of holes) {
    const hp = hole.map(p => pr(tr3([p[0],p[1],z]),s,w,h));
    if (!hp.length) continue; ctx.moveTo(hp[0].x,hp[0].y); for (let i=1;i<hp.length;i++) ctx.lineTo(hp[i].x,hp[i].y); ctx.closePath();
  }
}
function drawPoly3(points, style, s,w,h,z=0, holes=[]) {
  path3(points,s,w,h,z,holes);
  ctx.fillStyle = style.fill; ctx.strokeStyle = style.stroke; ctx.lineWidth = style.lineWidth || 1;
  holes.length ? ctx.fill("evenodd") : ctx.fill(); ctx.stroke();
}
function drawPort3(s,w,h) {
  const pts = [[port.x0,port.y,port.z0],[port.x1,port.y,port.z0],[port.x1,port.y,port.z1],[port.x0,port.y,port.z1]];
  const sp = pts.map(p => pr(tr3(p),s,w,h));
  ctx.beginPath(); ctx.moveTo(sp[0].x,sp[0].y); for (let i=1;i<sp.length;i++) ctx.lineTo(sp[i].x,sp[i].y); ctx.closePath();
  ctx.fillStyle="rgba(226,59,59,.82)"; ctx.strokeStyle="#8b1010"; ctx.lineWidth=1.5; ctx.fill(); ctx.stroke();
}

function path2(points,w,h,holes=[]) {
  const pts = points.map(p => w2s(p,w,h));
  ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y); for (let i=1;i<pts.length;i++) ctx.lineTo(pts[i].x,pts[i].y); ctx.closePath();
  for (const hole of holes) {
    const hp = hole.map(p => w2s(p,w,h));
    if (!hp.length) continue; ctx.moveTo(hp[0].x,hp[0].y); for (let i=1;i<hp.length;i++) ctx.lineTo(hp[i].x,hp[i].y); ctx.closePath();
  }
}
function drawPoly2(points, style, w,h,holes=[]) {
  path2(points,w,h,holes); ctx.fillStyle=style.fill; ctx.strokeStyle=style.stroke; ctx.lineWidth=style.lineWidth || 1;
  holes.length ? ctx.fill("evenodd") : ctx.fill(); ctx.stroke();
}
function drawRect2(b,style,w,h) {
  drawPoly2([[b.xmin,b.ymin],[b.xmax,b.ymin],[b.xmax,b.ymax],[b.xmin,b.ymax]], style, w,h);
}
function drawGrid(w,h) {
  ctx.strokeStyle="rgba(100,110,130,.20)"; ctx.fillStyle="#667085"; ctx.font="11px Arial";
  for (let x=Math.ceil(air.xmin/10)*10; x<=air.xmax; x+=10) {
    const a=w2s([x,air.ymin],w,h), b=w2s([x,air.ymax],w,h);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); ctx.fillText(`${x}`,a.x+2,h-10);
  }
  for (let y=Math.ceil(air.ymin/10)*10; y<=air.ymax; y+=10) {
    const a=w2s([air.xmin,y],w,h), b=w2s([air.xmax,y],w,h);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); ctx.fillText(`${y}`,10,a.y-2);
  }
}
function drawPort2(w,h) {
  const a=w2s([port.x0,port.y],w,h), b=w2s([port.x1,port.y],w,h), c=w2s([(port.x0+port.x1)/2,port.y],w,h);
  ctx.strokeStyle="#d61f1f"; ctx.lineWidth=4; ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  ctx.fillStyle="#d61f1f"; ctx.beginPath(); ctx.arc(c.x,c.y,5,0,Math.PI*2); ctx.fill();
}
function label(text,p,w,h,color) {
  if (!ui.labels.checked) return;
  const q = w2s(p,w,h); ctx.fillStyle=color; ctx.font="13px Arial"; ctx.fillText(text,q.x+6,q.y-6);
}
function drawRuler(w,h) {
  if (!rulerPts.length) return;
  const pts = rulerPts.map(p => w2s(p,w,h));
  ctx.fillStyle="#111827"; ctx.strokeStyle="#111827"; ctx.lineWidth=2;
  for (const p of pts) { ctx.beginPath(); ctx.arc(p.x,p.y,4,0,Math.PI*2); ctx.fill(); }
  if (pts.length === 2) {
    ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y); ctx.lineTo(pts[1].x,pts[1].y); ctx.stroke();
    const dx=rulerPts[1][0]-rulerPts[0][0], dy=rulerPts[1][1]-rulerPts[0][1], d=Math.hypot(dx,dy);
    const mx=(pts[0].x+pts[1].x)/2, my=(pts[0].y+pts[1].y)/2;
    ctx.fillStyle="rgba(255,255,255,.95)"; ctx.strokeStyle="rgba(30,41,59,.35)"; ctx.fillRect(mx+8,my-42,196,56); ctx.strokeRect(mx+8,my-42,196,56);
    ctx.fillStyle="#111827"; ctx.font="13px Arial"; ctx.fillText(`distance = ${d.toFixed(3)} mm`,mx+16,my-24); ctx.fillText(`dx=${dx.toFixed(3)}, dy=${dy.toFixed(3)} mm`,mx+16,my-7);
  }
}
function draw2D(w,h) {
  drawGrid(w,h);
  if (ui.air.checked) drawRect2(air,{fill:"rgba(139,183,255,.08)",stroke:"rgba(67,125,210,.55)",lineWidth:1.2},w,h);
  if (ui.skin.checked) drawRect2(skin,{fill:"rgba(213,154,223,.20)",stroke:"rgba(142,74,155,.70)",lineWidth:1.2},w,h);
  if (ui.rogers.checked) drawRect2(board,{fill:"rgba(160,160,160,.36)",stroke:"rgba(60,60,60,.75)"},w,h);
  if (ui.side.checked) drawPoly2(DATA.side_metal.outer.points,{fill:"rgba(154,106,53,.86)",stroke:"rgba(55,35,15,.88)"},w,h,DATA.side_metal.holes.map(h=>h.points));
  if (ui.main.checked) drawPoly2(DATA.main_metal.points,{fill:"rgba(217,150,85,.95)",stroke:"rgba(35,25,20,.88)"},w,h);
  if (ui.port.checked) drawPort2(w,h);
  label("skin block",[skin.xmin,skin.ymax],w,h,"#944aa0"); label("Rogers board",[board.xmin,board.ymax],w,h,"#555");
  label("tuned vertical port",[(port.x0+port.x1)/2,port.y],w,h,"#c02d2d"); label("main metal",[0,10.5],w,h,"#8a4b16");
  drawRuler(w,h);
  ctx.fillStyle="#20242a"; ctx.font="15px Arial"; ctx.fillText("Top view / ruler mode: dimensions in mm",18,28);
}
function draw3D(w,h) {
  const s = allScale3(w,h);
  if (ui.air.checked) drawBox(air,{stroke:"rgba(67,125,210,.55)"},s,w,h,false);
  if (ui.skin.checked) drawBox(skin,{fill:"rgba(213,154,223,.18)",stroke:"rgba(142,74,155,.80)"},s,w,h,true);
  if (ui.rogers.checked) drawBox(board,{fill:"rgba(160,160,160,.34)",stroke:"rgba(70,70,70,.78)"},s,w,h,true);
  if (ui.side.checked) drawPoly3(DATA.side_metal.outer.points,{fill:"rgba(154,106,53,.86)",stroke:"rgba(55,35,15,.88)"},s,w,h,0.05,DATA.side_metal.holes.map(h=>h.points));
  if (ui.main.checked) drawPoly3(DATA.main_metal.points,{fill:"rgba(217,150,85,.96)",stroke:"rgba(35,25,20,.9)"},s,w,h,0.12);
  if (ui.port.checked) drawPort3(s,w,h);
  ctx.fillStyle="#20242a"; ctx.font="15px Arial"; ctx.fillText("3D geometry: tuned vertical CPW port + Rogers + skin block",18,28);
}
function draw() {
  const r=canvas.getBoundingClientRect(), w=r.width, h=r.height; ctx.clearRect(0,0,w,h);
  ui.ruler.checked ? draw2D(w,h) : draw3D(w,h);
}
canvas.addEventListener("pointerdown", e => {
  const r=canvas.getBoundingClientRect();
  if (ui.ruler.checked) {
    if (rulerPts.length >= 2) rulerPts = [];
    rulerPts.push(s2w(e.clientX-r.left,e.clientY-r.top,r.width,r.height)); draw(); return;
  }
  dragging=true; last={x:e.clientX,y:e.clientY}; canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointermove", e => {
  if (!dragging || ui.ruler.checked) return;
  yaw += (e.clientX-last.x)*0.008; pitch += (e.clientY-last.y)*0.008; pitch = Math.max(-1.35, Math.min(1.35, pitch));
  last={x:e.clientX,y:e.clientY}; draw();
});
canvas.addEventListener("pointerup",()=>dragging=false); canvas.addEventListener("pointercancel",()=>dragging=false);
canvas.addEventListener("wheel", e => { e.preventDefault(); zoom *= e.deltaY > 0 ? .92 : 1.08; zoom = Math.max(.25, Math.min(8, zoom)); draw(); }, {passive:false});
for (const el of Object.values(ui)) el.addEventListener("change", draw);
document.getElementById("clearRuler").addEventListener("click",()=>{rulerPts=[]; draw();});
document.getElementById("isoView").addEventListener("click",()=>{ui.ruler.checked=false; yaw=-0.62; pitch=0.42; zoom=1; draw();});
document.getElementById("topView").addEventListener("click",()=>{ui.ruler.checked=true; rulerPts=[]; draw();});
document.getElementById("resetView").addEventListener("click",()=>{ui.ruler.checked=false; rulerPts=[]; yaw=-0.62; pitch=0.42; zoom=1; draw();});
window.addEventListener("resize",resize); resize();
</script>
</body>
</html>
"""


def main() -> None:
    payload = build_payload()
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_OUT}")
    print("Tuned feed:")
    print(
        f"  vertical x-z port, x={TUNED_PORT['x0']}..{TUNED_PORT['x1']} mm, "
        f"y={TUNED_PORT['y']} mm, z={TUNED_PORT['z0']}..{TUNED_PORT['z1']} mm, "
        f"Zref={TUNED_PORT['zref_ohm']} ohm"
    )


if __name__ == "__main__":
    main()
