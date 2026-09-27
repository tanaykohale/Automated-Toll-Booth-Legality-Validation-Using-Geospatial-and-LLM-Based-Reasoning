"""Stream an OpenStreetMap .osm XML file and pull out toll booth nodes.

Uses lxml.iterparse and clears elements as it goes, so memory stays flat even
for multi-GB files. For .osm.pbf extracts (Geofabrik), convert first:
    osmconvert north-eastern-zone-latest.osm.pbf -o=north-eastern-zone-latest.osm
"""
import pandas as pd
from lxml import etree

TOLL_TAGS = {("barrier", "toll_booth"), ("highway", "toll_gantry")}


def is_toll(tags):
    return any(tags.get(k) == v for k, v in TOLL_TAGS)


def iter_toll_nodes(path):
    for _, elem in etree.iterparse(path, events=("end",), tag="node"):
        tags = {t.attrib["k"]: t.attrib["v"] for t in elem.findall("tag")}
        if tags and is_toll(tags):
            yield {
                **tags,
                "id": int(elem.attrib["id"]),
                "lat": float(elem.attrib["lat"]),
                "lon": float(elem.attrib["lon"]),
                "name": tags.get("name"),
            }
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


def extract_toll_booths(path):
    """DataFrame with id, lat, lon, name, barrier, highway + any other OSM tags."""
    df = pd.DataFrame(list(iter_toll_nodes(path)))
    if df.empty:
        return pd.DataFrame(columns=["id", "lat", "lon", "name", "barrier", "highway"])
    first = [c for c in ["id", "lat", "lon", "name", "barrier", "highway"] if c in df]
    return df[first + [c for c in df.columns if c not in first]]
