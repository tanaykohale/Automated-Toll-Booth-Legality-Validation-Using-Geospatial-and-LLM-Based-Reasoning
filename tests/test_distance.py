import pandas as pd
import pytest

from conftest import SAMPLE_CSV
from tollcheck.distance import close_pairs, cluster_plazas, haversine


def test_haversine_known_values():
    assert haversine(0, 0, 0, 0) == 0
    assert haversine(0, 0, 1, 0) == pytest.approx(111.19, abs=0.01)   # 1 degree of latitude
    # Delhi (28.6139, 77.2090) -> Mumbai (19.0760, 72.8777) ~ 1,150 km straight line
    assert haversine(28.6139, 77.2090, 19.0760, 72.8777) == pytest.approx(1150, rel=0.01)
    assert haversine(10, 20, 30, 40) == pytest.approx(haversine(30, 40, 10, 20))


def booths(*pts):
    return pd.DataFrame([{"id": i, "lat": la, "lon": lo, "name": n} for i, (la, lo, n) in enumerate(pts)])


def test_cluster_merges_lanes_of_same_plaza():
    df = booths((26.0, 91.0, None), (26.0001, 91.0001, "Alpha"), (26.5, 91.0, None))
    tagged, plazas = cluster_plazas(df, radius_km=1)
    assert tagged["plaza_id"].tolist() == [0, 0, 1]
    assert plazas.loc[0, "booths"] == 2 and plazas.loc[0, "name"] == "Alpha"
    assert plazas.loc[0, "booth_ids"] == "0;1"


def test_cluster_is_transitive_chain():
    # A-B 0.8 km, B-C 0.8 km, A-C 1.6 km -> still one plaza (single linkage)
    step = 0.8 / 111.19
    df = booths((26.0, 91.0, None), (26.0 + step, 91.0, None), (26.0 + 2 * step, 91.0, None))
    _, plazas = cluster_plazas(df, radius_km=1)
    assert len(plazas) == 1


def test_close_pairs_threshold_and_sorting():
    df = pd.DataFrame({"plaza_id": [0, 1, 2], "lat": [26.0, 26.3, 27.0], "lon": [91, 91, 91], "name": [None] * 3})
    p = close_pairs(df, max_km=60)
    assert len(p) == 1 and p.loc[0, "distance_km"] == pytest.approx(33.36, abs=0.05)
    assert close_pairs(df, max_km=200)["distance_km"].is_monotonic_increasing
    assert close_pairs(df.iloc[:1]).empty


def test_sample_data_reproduces_notebook_and_fixes_overcount():
    df = pd.read_csv(SAMPLE_CSV)
    df = df[df["barrier"] == "toll_booth"]
    assert len(df) == 28
    raw = close_pairs(df, id_col="id")
    assert len(raw) == 54                         # what findingDistance.ipynb reported
    assert (raw["distance_km"] < 1).sum() == 12   # ...12 of which are lanes of one plaza
    _, plazas = cluster_plazas(df)
    assert len(plazas) == 16
    assert len(close_pairs(plazas)) == 12         # real plaza-to-plaza candidates
