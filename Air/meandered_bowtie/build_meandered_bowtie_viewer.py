"""Build a standalone HTML geometry/ruler viewer for Meandered_Bowtie_v1.0.dxf.

Slide-12 interpretation:

* Rogers material = full 42 x 38.5 mm gray board rectangle.
* Main metal = smaller inner PEC loop.
* Side metal lines = Rogers rectangle minus the larger gray-region PEC loop.
"""

from __future__ import annotations

import json
from pathlib import Path

from dxf_utils import parse_polylines


ROOT = Path(__file__).resolve().parents[2]
DXF = ROOT / "dxf" / "Meandered_Bowtie_v1.0.dxf"
OUT = Path(__file__).resolve().parent
HTML_OUT = OUT / "meandered_bowtie_air_geometry_viewer.html"

PORT = {
    "name": "Slide-12 CPW feed gap lumped port",
    "x0": -0.3000,
    "x1": 0.3000,
    "y0": 0.8575,
    "y1": 1.7500,
    "feed_x": 0.0,
    "feed_y": 0.8575,
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
    main_metal = min(pec, key=lambda p: abs(p.area_mm2)) if pec else None
    gray_region = max(pec, key=lambda p: abs(p.area_mm2)) if pec else None

    return {
        "dxf_name": DXF.name,
        "unit": "mm",
        "rogers": [_pack(p) for p in rogers],
        "main_metal": _pack(main_metal) if main_metal else None,
        "gray_region": _pack(gray_region) if gray_region else None,
        "side_metal_regions": [
            {
                "outer": _pack(rogers[0]),
                "holes": [_pack(gray_region)],
            }
        ]
        if rogers and gray_region
        else [],
        "port": PORT,
    }


def build_html(payload: dict) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Meandered Bowtie geometry viewer with ruler</title>
  <style>
    body {{ margin:0; font-family:Arial,Helvetica,sans-serif; background:#f5f7fb; color:#20242a; }}
    main {{ max-width:1220px; margin:0 auto; padding:22px; }}
    canvas {{
      display:block; width:100%; height:740px;
      background:linear-gradient(180deg,#ffffff 0%,#eef2f8 100%);
      border:1px solid #d9dee8; border-radius:14px;
      box-shadow:0 8px 28px rgba(20,31,50,.08); cursor:grab;
    }}
    canvas:active {{ cursor:grabbing; }}
    .toolbar {{ display:flex; flex-wrap:wrap; gap:10px 16px; align-items:center; margin:10px 0 14px; font-size:14px; }}
    button {{ border:1px solid #c7cfdd; background:white; color:#20242a; border-radius:8px; padding:7px 10px; cursor:pointer; }}
    button:hover {{ background:#eef3fb; }}
    .notes {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(255px,1fr)); gap:10px; margin-top:14px; font-size:14px; line-height:1.4; }}
    .note {{ background:#fff; border:1px solid #d9dee8; border-radius:10px; padding:10px 12px; }}
    .swatch {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }}
  </style>
</head>
<body>
  <main>
    <h2>Meandered Bowtie DXF geometry review</h2>
    <p>Drag to rotate in 3D mode. Turn on <b>2D ruler mode</b> and click two points to measure in DXF millimeters.</p>
    <div class="toolbar">
      <label><input id="showMainMetal" type="checkbox" checked /> main metal / meander lines</label>
      <label><input id="showSideMetal" type="checkbox" checked /> side metal lines</label>
      <label><input id="showRogers" type="checkbox" checked /> Rogers material</label>
      <label><input id="showAir" type="checkbox" checked /> air box</label>
      <label><input id="showPort" type="checkbox" checked /> feed / port</label>
      <label><input id="showLabels" type="checkbox" checked /> labels</label>
      <label><input id="rulerMode" type="checkbox" /> 2D ruler mode</label>
      <button id="clearRuler">Clear ruler</button>
      <button id="isoView">Iso view</button>
      <button id="resetView">Reset view</button>
    </div>
    <canvas id="viewer"></canvas>
    <div class="notes">
      <div class="note"><span class="swatch" style="background:#b9b9b9"></span>Rogers material: full 42.0 × 38.5 mm gray board plane.</div>
      <div class="note"><span class="swatch" style="background:#d99655"></span>Main metal: smaller inner PEC loop.</div>
      <div class="note"><span class="swatch" style="background:#9a6a35"></span>Side metal lines: Rogers rectangle minus the larger gray-region loop.</div>
      <div class="note"><span class="swatch" style="background:#e34b4b"></span>Feed: Slide-12 CPW lumped port across the central slot gap.</div>
    </div>
  </main>

  <script>
    const DATA = {data};
    const canvas = document.getElementById("viewer");
    const ctx = canvas.getContext("2d");
    const ui = {{
      main: document.getElementById("showMainMetal"),
      side: document.getElementById("showSideMetal"),
      rogers: document.getElementById("showRogers"),
      air: document.getElementById("showAir"),
      port: document.getElementById("showPort"),
      labels: document.getElementById("showLabels"),
      ruler: document.getElementById("rulerMode")
    }};

    let yaw=-0.62, pitch=0.42, zoom=1.0, dragging=false, last={{x:0,y:0}}, rulerPts=[];
    const allPolys=[...DATA.rogers, DATA.main_metal, DATA.gray_region].filter(Boolean);
    const allPoints=allPolys.flatMap(p=>p.points);
    const minX=Math.min(...allPoints.map(p=>p[0])), maxX=Math.max(...allPoints.map(p=>p[0]));
    const minY=Math.min(...allPoints.map(p=>p[1])), maxY=Math.max(...allPoints.map(p=>p[1]));
    const cx=(minX+maxX)/2, cy=(minY+maxY)/2, airPad=14, airZ=22;

    function resize() {{
      const r=canvas.getBoundingClientRect(), dpr=Math.min(window.devicePixelRatio||1,2);
      canvas.width=Math.round(r.width*dpr); canvas.height=Math.round(r.height*dpr);
      ctx.setTransform(dpr,0,0,dpr,0,0); draw();
    }}
    function resetView() {{ yaw=-0.62; pitch=0.42; zoom=1.0; rulerPts=[]; draw(); }}
    function isoView() {{ ui.ruler.checked=false; yaw=-0.62; pitch=0.42; zoom=1.0; draw(); }}
    function tr3(p) {{
      let x=p[0]-cx, y=p[1]-cy, z=p[2]||0;
      const cyw=Math.cos(yaw), syw=Math.sin(yaw), x1=x*cyw-y*syw, y1=x*syw+y*cyw;
      const cp=Math.cos(pitch), sp=Math.sin(pitch);
      return {{x:x1, y:y1*cp-z*sp, z:y1*sp+z*cp}};
    }}
    function pr3(t,s,w,h) {{ return {{x:w/2+t.x*s, y:h/2-t.z*s}}; }}
    function scale2d(w,h) {{ return Math.min(w/(maxX-minX+16), h/(maxY-minY+16)); }}
    function w2s(p,w,h) {{ const s=scale2d(w,h); return {{x:w/2+(p[0]-cx)*s, y:h/2-(p[1]-cy)*s}}; }}
    function s2w(x,y,w,h) {{ const s=scale2d(w,h); return [cx+(x-w/2)/s, cy-(y-h/2)/s]; }}

    function path2d(points,w,h,holes=[]) {{
      const pts=points.map(p=>w2s(p,w,h));
      ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y);
      for(let i=1;i<pts.length;i++) ctx.lineTo(pts[i].x,pts[i].y);
      ctx.closePath();
      for(const hole of holes) {{
        const hpts=hole.map(p=>w2s(p,w,h)); if(!hpts.length) continue;
        ctx.moveTo(hpts[0].x,hpts[0].y);
        for(let i=1;i<hpts.length;i++) ctx.lineTo(hpts[i].x,hpts[i].y);
        ctx.closePath();
      }}
    }}
    function drawPoly2d(points,style,w,h,holes=[]) {{
      path2d(points,w,h,holes); ctx.fillStyle=style.fill; ctx.strokeStyle=style.stroke; ctx.lineWidth=style.lineWidth||1;
      holes.length ? ctx.fill("evenodd") : ctx.fill(); ctx.stroke();
    }}
    function path3d(points,s,w,h,z,holes=[]) {{
      const pts=points.map(p=>pr3(tr3([p[0],p[1],z]),s,w,h));
      ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y);
      for(let i=1;i<pts.length;i++) ctx.lineTo(pts[i].x,pts[i].y);
      ctx.closePath();
      for(const hole of holes) {{
        const hpts=hole.map(p=>pr3(tr3([p[0],p[1],z]),s,w,h)); if(!hpts.length) continue;
        ctx.moveTo(hpts[0].x,hpts[0].y);
        for(let i=1;i<hpts.length;i++) ctx.lineTo(hpts[i].x,hpts[i].y);
        ctx.closePath();
      }}
    }}
    function drawPoly3d(points,style,s,w,h,z=0,holes=[]) {{
      path3d(points,s,w,h,z,holes); ctx.fillStyle=style.fill; ctx.strokeStyle=style.stroke; ctx.lineWidth=style.lineWidth||1;
      holes.length ? ctx.fill("evenodd") : ctx.fill(); ctx.stroke();
    }}

    function drawAir3d(s,w,h) {{
      const x0=minX-airPad,x1=maxX+airPad,y0=minY-airPad,y1=maxY+airPad,z0=-airZ,z1=airZ;
      const v=[[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]].map(p=>pr3(tr3(p),s,w,h));
      const e=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
      ctx.strokeStyle="rgba(67,125,210,.55)"; ctx.lineWidth=1.2;
      for(const [a,b] of e) {{ ctx.beginPath(); ctx.moveTo(v[a].x,v[a].y); ctx.lineTo(v[b].x,v[b].y); ctx.stroke(); }}
    }}
    function drawGrid2d(w,h) {{
      ctx.strokeStyle="rgba(100,110,130,.20)"; ctx.lineWidth=1; ctx.font="11px Arial"; ctx.fillStyle="#6b7280";
      for(let x=Math.ceil((minX-airPad)/5)*5;x<=maxX+airPad;x+=5) {{
        const a=w2s([x,minY-airPad],w,h), b=w2s([x,maxY+airPad],w,h);
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); ctx.fillText(`${{x}}`,a.x+2,h-10);
      }}
      for(let y=Math.ceil((minY-airPad)/5)*5;y<=maxY+airPad;y+=5) {{
        const a=w2s([minX-airPad,y],w,h), b=w2s([maxX+airPad,y],w,h);
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); ctx.fillText(`${{y}}`,10,a.y-2);
      }}
    }}
    function drawPort2d(w,h) {{
      const p=DATA.port; drawPoly2d([[p.x0,p.y0],[p.x1,p.y0],[p.x1,p.y1],[p.x0,p.y1]],{{fill:"rgba(227,75,75,.90)",stroke:"rgba(120,25,25,.95)",lineWidth:1.4}},w,h);
      const fp=w2s([p.feed_x,p.feed_y],w,h); ctx.fillStyle="rgba(220,20,20,.96)"; ctx.strokeStyle="white"; ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(fp.x,fp.y,6,0,Math.PI*2); ctx.fill(); ctx.stroke();
    }}
    function drawPort3d(s,w,h) {{
      const p=DATA.port; drawPoly3d([[p.x0,p.y0],[p.x1,p.y0],[p.x1,p.y1],[p.x0,p.y1]],{{fill:"rgba(227,75,75,.90)",stroke:"rgba(120,25,25,.95)",lineWidth:1.4}},s,w,h,1);
      const fp=pr3(tr3([p.feed_x,p.feed_y,2]),s,w,h); ctx.fillStyle="rgba(220,20,20,.96)"; ctx.strokeStyle="white"; ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(fp.x,fp.y,6,0,Math.PI*2); ctx.fill(); ctx.stroke();
    }}
    function label2d(text,p,w,h,color) {{ if(!ui.labels.checked) return; const q=w2s(p,w,h); ctx.fillStyle=color; ctx.font="13px Arial"; ctx.fillText(text,q.x+6,q.y-6); }}
    function drawRuler(w,h) {{
      if(!rulerPts.length) return; const pts=rulerPts.map(p=>w2s(p,w,h)); ctx.fillStyle="#111827"; ctx.strokeStyle="#111827"; ctx.lineWidth=2;
      for(const p of pts) {{ ctx.beginPath(); ctx.arc(p.x,p.y,4,0,Math.PI*2); ctx.fill(); }}
      if(pts.length===2) {{
        ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y); ctx.lineTo(pts[1].x,pts[1].y); ctx.stroke();
        const dx=rulerPts[1][0]-rulerPts[0][0], dy=rulerPts[1][1]-rulerPts[0][1], d=Math.hypot(dx,dy), mx=(pts[0].x+pts[1].x)/2, my=(pts[0].y+pts[1].y)/2;
        ctx.fillStyle="rgba(255,255,255,.94)"; ctx.strokeStyle="rgba(30,41,59,.35)"; ctx.lineWidth=1; ctx.fillRect(mx+8,my-42,190,56); ctx.strokeRect(mx+8,my-42,190,56);
        ctx.fillStyle="#111827"; ctx.font="13px Arial"; ctx.fillText(`distance = ${{d.toFixed(3)}} mm`,mx+16,my-24); ctx.fillText(`Δx=${{dx.toFixed(3)}} mm, Δy=${{dy.toFixed(3)}} mm`,mx+16,my-7);
      }}
    }}
    function draw2d(w,h) {{
      drawGrid2d(w,h);
      if(ui.air.checked) drawPoly2d([[minX-airPad,minY-airPad],[maxX+airPad,minY-airPad],[maxX+airPad,maxY+airPad],[minX-airPad,maxY+airPad]],{{fill:"rgba(185,215,255,.12)",stroke:"rgba(67,125,210,.65)",lineWidth:1.3}},w,h);
      if(ui.rogers.checked) for(const p of DATA.rogers) drawPoly2d(p.points,{{fill:"rgba(160,160,160,.42)",stroke:"rgba(70,70,70,.75)",lineWidth:1}},w,h);
      if(ui.side.checked) for(const r of DATA.side_metal_regions) drawPoly2d(r.outer.points,{{fill:"rgba(154,106,53,.86)",stroke:"rgba(55,35,15,.88)",lineWidth:1.1}},w,h,r.holes.map(h=>h.points));
      if(ui.main.checked&&DATA.main_metal) drawPoly2d(DATA.main_metal.points,{{fill:"rgba(217,150,85,.95)",stroke:"rgba(35,25,20,.88)",lineWidth:1.2}},w,h);
      if(DATA.gray_region) drawPoly2d(DATA.gray_region.points,{{fill:"rgba(255,255,255,0)",stroke:"rgba(70,70,75,.45)",lineWidth:.8}},w,h);
      if(ui.port.checked) drawPort2d(w,h);
      label2d("Rogers gray plane",[minX,maxY],w,h,"#555"); label2d("side metal lines",[18,24],w,h,"#6b4218"); label2d("main metal",[0,10.5],w,h,"#8a4b16"); label2d("feed",[DATA.port.feed_x,DATA.port.feed_y],w,h,"#c02d2d");
      drawRuler(w,h); ctx.fillStyle="#20242a"; ctx.font="15px Arial"; ctx.fillText("2D ruler mode: click two points to measure in mm",18,28);
    }}
    function draw3d(w,h) {{
      const s=Math.min(w/((maxX-minX+2*airPad)*1.45),h/((maxY-minY+2*airPad)*1.35))*zoom;
      if(ui.air.checked) drawAir3d(s,w,h);
      if(ui.rogers.checked) for(const p of DATA.rogers) drawPoly3d(p.points,{{fill:"rgba(160,160,160,.44)",stroke:"rgba(70,70,70,.72)",lineWidth:1}},s,w,h,-.15);
      if(ui.side.checked) for(const r of DATA.side_metal_regions) drawPoly3d(r.outer.points,{{fill:"rgba(154,106,53,.86)",stroke:"rgba(55,35,15,.88)",lineWidth:1.1}},s,w,h,.25,r.holes.map(h=>h.points));
      if(ui.main.checked&&DATA.main_metal) drawPoly3d(DATA.main_metal.points,{{fill:"rgba(217,150,85,.95)",stroke:"rgba(35,25,20,.85)",lineWidth:1.2}},s,w,h,.55);
      if(DATA.gray_region) drawPoly3d(DATA.gray_region.points,{{fill:"rgba(255,255,255,0)",stroke:"rgba(70,70,75,.45)",lineWidth:.8}},s,w,h,.3);
      if(ui.port.checked) drawPort3d(s,w,h);
      ctx.fillStyle="#20242a"; ctx.font="15px Arial"; ctx.fillText("3D view: orange metal lines over gray Rogers plane",18,28); ctx.font="13px Arial"; ctx.fillStyle="#5a6070"; ctx.fillText("Use 2D ruler mode for exact dimension checks.",18,50);
    }}
    function draw() {{ const r=canvas.getBoundingClientRect(), w=r.width, h=r.height; ctx.clearRect(0,0,w,h); ui.ruler.checked ? draw2d(w,h) : draw3d(w,h); }}
    canvas.addEventListener("pointerdown", e=>{{ const r=canvas.getBoundingClientRect(); if(ui.ruler.checked) {{ if(rulerPts.length>=2) rulerPts=[]; rulerPts.push(s2w(e.clientX-r.left,e.clientY-r.top,r.width,r.height)); draw(); return; }} dragging=true; last={{x:e.clientX,y:e.clientY}}; canvas.setPointerCapture(e.pointerId); }});
    canvas.addEventListener("pointermove", e=>{{ if(!dragging||ui.ruler.checked) return; yaw+=(e.clientX-last.x)*.008; pitch+=(e.clientY-last.y)*.008; pitch=Math.max(-1.35,Math.min(1.35,pitch)); last={{x:e.clientX,y:e.clientY}}; draw(); }});
    canvas.addEventListener("pointerup",()=>dragging=false); canvas.addEventListener("pointercancel",()=>dragging=false);
    canvas.addEventListener("wheel", e=>{{ e.preventDefault(); zoom*=e.deltaY>0?.92:1.08; zoom=Math.max(.25,Math.min(8,zoom)); draw(); }}, {{passive:false}});
    for(const el of Object.values(ui)) el.addEventListener("change", draw);
    document.getElementById("clearRuler").addEventListener("click",()=>{{rulerPts=[]; draw();}});
    document.getElementById("resetView").addEventListener("click",resetView);
    document.getElementById("isoView").addEventListener("click",isoView);
    window.addEventListener("resize",resize); resize();
  </script>
</body>
</html>
"""


def main() -> None:
    payload = build_payload()
    HTML_OUT.write_text(build_html(payload), encoding="utf-8")
    print(f"Wrote {HTML_OUT}")
    print("DXF material interpretation:")
    for idx, poly in enumerate(payload["rogers"], start=1):
        print(f"  Rogers {idx}: vertices={len(poly['points'])}, bbox={poly['bbox']}")
    if payload["main_metal"]:
        metal = payload["main_metal"]
        print(f"  Main metal: vertices={len(metal['points'])}, bbox={metal['bbox']}")
    for idx, region in enumerate(payload["side_metal_regions"], start=1):
        print(f"  Side metal region {idx}: outer_bbox={region['outer']['bbox']}, hole_bbox={region['holes'][0]['bbox']}")
    print(
        "  Slide-12 CPW feed-gap port: "
        f"x={PORT['x0']:.4f}..{PORT['x1']:.4f} mm, "
        f"y={PORT['y0']:.4f}..{PORT['y1']:.4f} mm"
    )


if __name__ == "__main__":
    main()
