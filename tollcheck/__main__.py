"""Command line:

  python -m tollcheck extract region.osm -o data/booths.csv
  python -m tollcheck pairs data/booths.csv -o output/          # plazas.csv, pairs.csv, map.html
  python -m tollcheck verify output/plazas.csv output/pairs.csv -o output/ --model llama3
  python -m tollcheck site data/booths.csv -o docs --booths-only   # static page for GitHub Pages
"""
import argparse
import os

import pandas as pd

from tollcheck import distance, extract, report


def cmd_extract(a):
    df = extract.extract_toll_booths(a.osm)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} toll nodes -> {a.out}")


def load_booths(path, booths_only=False):
    """Read a booth CSV; optionally keep only barrier=toll_booth (drop highway=toll_gantry)."""
    df = pd.read_csv(path)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    if booths_only and "barrier" in df:
        df = df[df["barrier"] == "toll_booth"]
    return df


def cmd_pairs(a):
    booths = load_booths(a.booths, a.booths_only)
    _, plazas = distance.cluster_plazas(booths, radius_km=a.plaza_radius)
    pairs = distance.close_pairs(plazas, max_km=a.km)
    os.makedirs(a.out, exist_ok=True)
    plazas.to_csv(os.path.join(a.out, "plazas.csv"), index=False)
    pairs.to_csv(os.path.join(a.out, "pairs.csv"), index=False)
    report.write_map(plazas, pairs, os.path.join(a.out, "map.html"))
    print(f"{len(booths)} booth nodes -> {len(plazas)} plazas -> {len(pairs)} pairs < {a.km} km")
    print(f"wrote plazas.csv, pairs.csv, map.html to {a.out}")


def cmd_verify(a):
    from tollcheck import verify

    plazas = pd.read_csv(a.plazas)
    pairs = pd.read_csv(a.pairs)
    involved = set(pairs["id_1"]) | set(pairs["id_2"])
    todo = plazas[plazas["plaza_id"].isin(involved)]
    scraper = verify.GoogleScraper()
    try:
        checked = verify.verify_plazas(todo, scraper, model=a.model)
    finally:
        scraper.close()
    final = verify.drop_invalid_pairs(pairs, checked)
    checked.to_csv(os.path.join(a.out, "plazas_verified.csv"), index=False)
    final.to_csv(os.path.join(a.out, "pairs_verified.csv"), index=False)
    print(f"{len(final)} of {len(pairs)} pairs have both plazas verified as real")


def cmd_site(a):
    from tollcheck.site import build_site

    booths = load_booths(a.booths, a.booths_only)
    s = build_site(booths, a.out, region=a.region, km=a.km, radius_km=a.plaza_radius)
    print(f"{s['n_booths']} booths -> {s['n_plazas']} plazas -> {s['n_pairs']} pairs; "
          f"wrote {a.out}/index.html")


def main(argv=None):
    p = argparse.ArgumentParser(prog="tollcheck")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="OSM XML -> toll booth CSV")
    e.add_argument("osm")
    e.add_argument("-o", "--out", default="data/booths.csv")
    e.set_defaults(fn=cmd_extract)
    q = sub.add_parser("pairs", help="booth CSV -> plazas, <60 km pairs, map")
    q.add_argument("booths")
    q.add_argument("-o", "--out", default="output")
    q.add_argument("--km", type=float, default=distance.RULE_KM)
    q.add_argument("--plaza-radius", type=float, default=distance.PLAZA_RADIUS_KM)
    q.add_argument("--booths-only", action="store_true",
                   help="ignore highway=toll_gantry nodes (ORR/FASTag gantries)")
    q.set_defaults(fn=cmd_pairs)
    v = sub.add_parser("verify", help="web search + local LLM check of plazas in pairs")
    v.add_argument("plazas")
    v.add_argument("pairs")
    v.add_argument("-o", "--out", default="output")
    v.add_argument("--model", default="llama3")
    v.set_defaults(fn=cmd_verify)
    w = sub.add_parser("site", help="booth CSV -> static results page (GitHub Pages)")
    w.add_argument("booths")
    w.add_argument("-o", "--out", default="docs")
    w.add_argument("--region", default="North-Eastern zone, India (OpenStreetMap)")
    w.add_argument("--km", type=float, default=distance.RULE_KM)
    w.add_argument("--plaza-radius", type=float, default=distance.PLAZA_RADIUS_KM)
    w.add_argument("--booths-only", action="store_true")
    w.set_defaults(fn=cmd_site)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
