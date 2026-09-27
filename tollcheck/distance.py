"""Distances, plaza clustering and the 60 km spacing check.

Note: Haversine is the straight-line (great-circle) distance. Road distance is
always >= this, so any plaza pair that is >= 60 km apart here is definitely
compliant; pairs < 60 km are *candidates* that still need a road-distance or
manual check.
"""
from math import asin, cos, radians, sin, sqrt

import pandas as pd

EARTH_RADIUS_KM = 6371.0
RULE_KM = 60.0          # NHAI fee rules: plazas on the same section >= 60 km apart
PLAZA_RADIUS_KM = 1.0   # booths closer than this are lanes/directions of one plaza


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def cluster_plazas(booths, radius_km=PLAZA_RADIUS_KM):
    """Group booth nodes into plazas (single-linkage within radius_km).

    Returns (booths with a 'plaza_id' column, plazas DataFrame with the centroid,
    booth count, a name if any booth had one, and member booth ids).
    """
    df = booths.reset_index(drop=True).copy()
    n = len(df)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    lat, lon = df["lat"].tolist(), df["lon"].tolist()
    for i in range(n):
        for j in range(i + 1, n):
            if haversine(lat[i], lon[i], lat[j], lon[j]) <= radius_km:
                parent[find(i)] = find(j)

    roots = [find(i) for i in range(n)]
    order = {r: k for k, r in enumerate(dict.fromkeys(roots))}
    df["plaza_id"] = [order[r] for r in roots]

    names = df["name"] if "name" in df else pd.Series([None] * n)
    rows = []
    for pid, g in df.groupby("plaza_id", sort=True):
        valid_names = [x for x in names.loc[g.index] if isinstance(x, str) and x.strip()]
        rows.append({
            "plaza_id": pid,
            "lat": round(g["lat"].mean(), 7),
            "lon": round(g["lon"].mean(), 7),
            "booths": len(g),
            "name": valid_names[0] if valid_names else None,
            "booth_ids": ";".join(str(i) for i in g["id"]),
        })
    return df, pd.DataFrame(rows)


def close_pairs(points, max_km=RULE_KM, id_col="plaza_id"):
    """All unordered pairs of points closer than max_km, sorted by distance."""
    pts = points.reset_index(drop=True)
    ids, lat, lon = pts[id_col].tolist(), pts["lat"].tolist(), pts["lon"].tolist()
    names = pts["name"].tolist() if "name" in pts else [None] * len(pts)
    out = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = haversine(lat[i], lon[i], lat[j], lon[j])
            if d < max_km:
                out.append({
                    "id_1": ids[i], "name_1": names[i], "lat1": lat[i], "lon1": lon[i],
                    "id_2": ids[j], "name_2": names[j], "lat2": lat[j], "lon2": lon[j],
                    "distance_km": round(d, 3),
                })
    cols = ["id_1", "name_1", "lat1", "lon1", "id_2", "name_2", "lat2", "lon2", "distance_km"]
    return pd.DataFrame(out, columns=cols).sort_values("distance_km", ignore_index=True)
