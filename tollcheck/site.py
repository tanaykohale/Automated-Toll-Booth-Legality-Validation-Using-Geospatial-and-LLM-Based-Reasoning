"""Static results page for GitHub Pages: one self-contained docs/index.html.

    python -m tollcheck site data/north_eastern_zone_booths.csv -o docs --booths-only

Only needs Leaflet + OpenStreetMap tiles from the web; tables and numbers work offline.
"""
import html
import json
import os
from datetime import date

from tollcheck import distance

REPO_URL = ("https://github.com/tanaykohale/"
            "Automated-Toll-Booth-Legality-Validation-Using-Geospatial-and-LLM-Based-Reasoning")

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Toll Plaza Spacing Audit</title>
<meta name="description" content="OpenStreetMap audit of Indian toll plazas closer than the 60 km spacing rule, with local-LLM verification.">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root {{ --bg:#fafaf7; --fg:#1d1d1b; --muted:#6b6b66; --card:#fff; --line:#e4e2dc; --accent:#c62828; --plaza:#1565c0; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#141413; --fg:#ecebe6; --muted:#9d9c96; --card:#1e1e1c; --line:#33322f; --accent:#ef5350; --plaza:#64b5f6; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1040px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-size:clamp(1.6rem,4vw,2.3rem); line-height:1.2; margin:0 0 8px; }}
h2 {{ font-size:1.25rem; margin:40px 0 12px; }}
p.lede {{ color:var(--muted); max-width:720px; margin:0 0 24px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }}
.stat {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.stat b {{ display:block; font-size:1.8rem; line-height:1.1; font-variant-numeric:tabular-nums; }}
.stat span {{ color:var(--muted); font-size:.9rem; }}
.stat.hl b {{ color:var(--accent); }}
#map {{ height:480px; border-radius:10px; border:1px solid var(--line); margin-top:16px; background:var(--card); }}
#map .offline {{ padding:24px; color:var(--muted); }}
.legend {{ font-size:.9rem; color:var(--muted); margin-top:8px; }}
.legend i {{ display:inline-block; width:18px; height:3px; background:var(--accent); vertical-align:middle; margin-right:6px; }}
.legend s {{ display:inline-block; width:11px; height:11px; border:2px solid var(--plaza); border-radius:50%; vertical-align:middle; margin:0 6px 0 16px; text-decoration:none; }}
.note {{ background:var(--card); border-left:3px solid var(--accent); padding:12px 16px; border-radius:0 8px 8px 0; margin:16px 0; }}
.table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; }}
table {{ border-collapse:collapse; width:100%; font-size:.92rem; font-variant-numeric:tabular-nums; background:var(--card); }}
th,td {{ padding:8px 12px; text-align:left; border-bottom:1px solid var(--line); white-space:nowrap; }}
th {{ font-weight:600; color:var(--muted); }}
tr:last-child td {{ border-bottom:0; }}
tbody tr {{ cursor:pointer; }}
tbody tr:hover {{ background:color-mix(in srgb, var(--accent) 8%, transparent); }}
ol {{ padding-left:20px; }} li {{ margin:6px 0; }}
a {{ color:var(--plaza); }}
footer {{ margin-top:48px; color:var(--muted); font-size:.85rem; }}
</style>
</head>
<body>
<main>
<h1>Toll Plaza Spacing Audit</h1>
<p class="lede">India's national-highway fee rules space toll plazas at least <b>60 km</b> apart. This project pulls every
toll booth out of OpenStreetMap, groups booths into plazas, flags plaza pairs that sit closer than 60 km, and checks
the suspects against the web with a locally hosted LLM. Region shown: <b>{region}</b>.</p>

<div class="stats">
  <div class="stat"><b>{n_booths}</b><span>toll booth nodes in OSM</span></div>
  <div class="stat"><b>{n_raw}</b><span>booth pairs &lt; 60 km (naive)</span></div>
  <div class="stat"><b>{n_same}</b><span>of those = lanes of one plaza</span></div>
  <div class="stat"><b>{n_plazas}</b><span>plazas after clustering</span></div>
  <div class="stat hl"><b>{n_pairs}</b><span>plaza pairs &lt; 60 km</span></div>
  <div class="stat"><b>{closest}</b><span>closest pair (km)</span></div>
</div>

<div id="map"><div class="offline">Loading map… (needs internet for map tiles — the tables below work offline)</div></div>
<div class="legend"><i></i>plaza pair closer than 60 km<s></s>plaza (size = booth nodes)</div>

<div class="note"><b>How to read this.</b> Distances are straight-line (Haversine). Road distance is always longer, so these
are <i>candidates</i>: a pair ≥ 60 km apart here is certainly compliant; a pair below it still needs a road-distance
check, and the rule only applies to plazas on the same highway section. OpenStreetMap can be incomplete or outdated.</div>

<h2>Candidate pairs</h2>
<div class="table-wrap"><table id="pairs">
<thead><tr><th>#</th><th>Plaza A</th><th>Plaza B</th><th>Distance (km)</th><th>Short by (km)</th></tr></thead>
<tbody></tbody></table></div>

<h2>Plazas</h2>
<div class="table-wrap"><table id="plazas">
<thead><tr><th>Plaza</th><th>Name (OSM)</th><th>Lat</th><th>Lon</th><th>Booth nodes</th><th>In pairs</th></tr></thead>
<tbody></tbody></table></div>

<h2>Method</h2>
<ol>
<li><b>Extract</b> — stream-parse the OSM extract with <code>lxml.iterparse</code> (flat memory on multi-GB files) and keep <code>barrier=toll_booth</code> nodes.</li>
<li><b>Cluster</b> — booths within {radius} km of each other (single linkage) are lanes/directions of one plaza.</li>
<li><b>Pair</b> — every plaza pair closer than 60 km by Haversine distance.</li>
<li><b>Verify</b> — search each flagged plaza (by name, or by coordinates when unnamed) with headless Chrome, let a local Ollama model judge whether a real plaza exists, and drop pairs with an invalid plaza.</li>
</ol>
<p>Code, tests and the command line tool: <a href="{repo}">GitHub repository</a>.</p>

<footer>Data © OpenStreetMap contributors (ODbL) · generated {today} by <code>python -m tollcheck site</code></footer>
</main>

<script>
const PLAZAS = {plazas_json};
const PAIRS = {pairs_json};
const label = p => p.name ? `#${{p.plaza_id}} ${{p.name}}` : `#${{p.plaza_id}}`;
const byId = Object.fromEntries(PLAZAS.map(p => [p.plaza_id, p]));
const esc = s => String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
const inPairs = {{}};
PAIRS.forEach(q => {{ inPairs[q.id_1] = (inPairs[q.id_1]||0)+1; inPairs[q.id_2] = (inPairs[q.id_2]||0)+1; }});

document.querySelector('#pairs tbody').innerHTML = PAIRS.map((q, i) =>
  `<tr data-i="${{i}}"><td>${{i+1}}</td><td>${{esc(label(byId[q.id_1]))}}</td><td>${{esc(label(byId[q.id_2]))}}</td>` +
  `<td>${{q.distance_km.toFixed(1)}}</td><td>${{(60 - q.distance_km).toFixed(1)}}</td></tr>`).join('');
document.querySelector('#plazas tbody').innerHTML = PLAZAS.map(p =>
  `<tr data-p="${{p.plaza_id}}"><td>#${{p.plaza_id}}</td><td>${{esc(p.name || '—')}}</td><td>${{p.lat.toFixed(4)}}</td>` +
  `<td>${{p.lon.toFixed(4)}}</td><td>${{p.booths}}</td><td>${{inPairs[p.plaza_id] || 0}}</td></tr>`).join('');

function initMap() {{
  if (typeof L === 'undefined') {{
    document.querySelector('#map .offline').textContent = 'Map unavailable offline — see the tables below.';
    return;
  }}
  document.getElementById('map').innerHTML = '';
  const css = getComputedStyle(document.documentElement);
  const red = css.getPropertyValue('--accent').trim(), blue = css.getPropertyValue('--plaza').trim();
  const map = L.map('map', {{ scrollWheelZoom: false }});
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
    {{ attribution: '&copy; OpenStreetMap contributors', maxZoom: 18 }}).addTo(map);
  const lines = PAIRS.map(q => L.polyline([[q.lat1, q.lon1], [q.lat2, q.lon2]], {{ color: red, weight: 3 }})
    .bindPopup(`${{esc(label(byId[q.id_1]))}} ↔ ${{esc(label(byId[q.id_2]))}}<br><b>${{q.distance_km.toFixed(1)}} km</b>`).addTo(map));
  const dots = {{}};
  PLAZAS.forEach(p => {{
    dots[p.plaza_id] = L.circleMarker([p.lat, p.lon], {{ radius: 4 + 2 * p.booths, color: blue, weight: 2, fillOpacity: .15 }})
      .bindPopup(`<b>Plaza ${{esc(label(p))}}</b><br>${{p.booths}} booth node(s)<br>` +
                 `<a href="https://www.openstreetmap.org/?mlat=${{p.lat}}&mlon=${{p.lon}}#map=16/${{p.lat}}/${{p.lon}}" target="_blank" rel="noopener">open in OSM</a>`)
      .addTo(map);
  }});
  map.fitBounds(PLAZAS.map(p => [p.lat, p.lon]), {{ padding: [30, 30] }});
  document.querySelectorAll('#pairs tbody tr').forEach(tr => tr.addEventListener('click', () => {{
    const l = lines[+tr.dataset.i]; map.fitBounds(l.getBounds(), {{ padding: [60, 60] }}); l.openPopup();
    document.getElementById('map').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  }}));
  document.querySelectorAll('#plazas tbody tr').forEach(tr => tr.addEventListener('click', () => {{
    const d = dots[tr.dataset.p]; map.setView(d.getLatLng(), 13); d.openPopup();
    document.getElementById('map').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  }}));
}}
</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" onload="initMap()" onerror="initMap()"></script>
</body>
</html>
"""


def _records(df):
    return json.dumps(df.astype(object).where(df.notna(), None).to_dict("records"))


def build_site(booths, out_dir, region="OpenStreetMap extract", km=distance.RULE_KM,
               radius_km=distance.PLAZA_RADIUS_KM):
    """Compute everything from a booth DataFrame and write out_dir/index.html. Returns summary dict."""
    raw = distance.close_pairs(booths, max_km=km, id_col="id")
    _, plazas = distance.cluster_plazas(booths, radius_km=radius_km)
    pairs = distance.close_pairs(plazas, max_km=km)
    summary = {
        "n_booths": len(booths),
        "n_raw": len(raw),
        "n_same": int((raw["distance_km"] <= radius_km).sum()),
        "n_plazas": len(plazas),
        "n_pairs": len(pairs),
        "closest": f"{pairs['distance_km'].min():.1f}" if len(pairs) else "—",
    }
    page = PAGE.format(
        region=html.escape(region), radius=radius_km, repo=REPO_URL, today=date.today().isoformat(),
        plazas_json=_records(plazas[["plaza_id", "lat", "lon", "booths", "name"]]),
        pairs_json=_records(pairs), **summary,
    )
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    # GitHub Pages: serve files as-is (no Jekyll processing)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()
    return summary
