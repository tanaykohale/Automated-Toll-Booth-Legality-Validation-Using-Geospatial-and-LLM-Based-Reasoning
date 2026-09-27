"""Self-contained Leaflet HTML map of plazas and < 60 km pairs."""
import html
import json

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<title>{title}</title><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{{height:100%;margin:0}}#info{{position:absolute;z-index:999;top:10px;right:10px;
background:#fff;padding:8px 12px;font:14px sans-serif;border-radius:6px;box-shadow:0 1px 4px #0004}}</style>
</head><body><div id="map"></div><div id="info">{summary}</div><script>
const plazas={plazas};const pairs={pairs};
const map=L.map('map');L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
{{attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);
const b=[];plazas.forEach(p=>{{b.push([p.lat,p.lon]);L.circleMarker([p.lat,p.lon],{{radius:6,color:'#1565c0'}})
.bindPopup(`Plaza ${{p.plaza_id}}${{p.name?' – '+p.name:''}}<br>${{p.booths}} booth node(s)`).addTo(map);}});
pairs.forEach(q=>L.polyline([[q.lat1,q.lon1],[q.lat2,q.lon2]],{{color:'#d32f2f',weight:3}})
.bindPopup(`Plaza ${{q.id_1}} ↔ ${{q.id_2}}: ${{q.distance_km}} km`).addTo(map));
if(b.length)map.fitBounds(b,{{padding:[30,30]}});else map.setView([22,79],5);
</script></body></html>"""


def write_map(plazas, pairs, path, title="Toll plazas closer than 60 km"):
    summary = (f"<b>{len(plazas)}</b> plazas · <b>{len(pairs)}</b> pairs &lt; 60 km "
               "<span style='color:#d32f2f'>━</span>")
    page = TEMPLATE.format(
        title=html.escape(title),
        summary=summary,
        plazas=json.dumps(plazas.where(plazas.notna(), None).to_dict("records")),
        pairs=json.dumps(pairs.where(pairs.notna(), None).to_dict("records")),
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path
