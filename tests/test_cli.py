import os

import pandas as pd

from conftest import SAMPLE_CSV
from tollcheck.__main__ import main

HERE = os.path.dirname(__file__)


def test_extract_then_pairs(tmp_path):
    booths = tmp_path / "booths.csv"
    main(["extract", os.path.join(HERE, "sample.osm"), "-o", str(booths)])
    assert len(pd.read_csv(booths)) == 3
    out = tmp_path / "out"
    main(["pairs", str(booths), "-o", str(out)])
    assert len(pd.read_csv(out / "plazas.csv")) == 2
    assert len(pd.read_csv(out / "pairs.csv")) == 1
    html = (out / "map.html").read_text(encoding="utf-8")
    assert "leaflet" in html and "Alpha Toll Plaza" in html


def test_pairs_on_sample_data(tmp_path, capsys):
    main(["pairs", SAMPLE_CSV, "-o", str(tmp_path), "--booths-only"])
    assert "28 booth nodes -> 16 plazas -> 12 pairs" in capsys.readouterr().out
