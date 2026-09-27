import os

from tollcheck.extract import extract_toll_booths

HERE = os.path.dirname(__file__)


def test_extracts_booths_and_gantries_only():
    df = extract_toll_booths(os.path.join(HERE, "sample.osm"))
    assert df["id"].tolist() == [1, 2, 3]
    assert list(df.columns[:6]) == ["id", "lat", "lon", "name", "barrier", "highway"]
    assert df.loc[0, "name"] == "Alpha Toll Plaza"
    assert df.loc[2, "highway"] == "toll_gantry"
    assert df["lat"].dtype == float


def test_empty_file(tmp_path):
    f = tmp_path / "empty.osm"
    f.write_text('<?xml version="1.0"?><osm version="0.6"></osm>')
    df = extract_toll_booths(str(f))
    assert df.empty and "lat" in df.columns
