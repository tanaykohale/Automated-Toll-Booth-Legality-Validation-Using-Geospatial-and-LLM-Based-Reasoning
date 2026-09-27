import pandas as pd
import requests

from tollcheck.verify import (classify_verification, drop_invalid_pairs, llm_verify,
                              search_query, verify_plazas)


def test_search_query_uses_name_or_coordinates():
    assert search_query("Jorabat", 26.1, 91.9) == "Jorabat toll plaza"
    assert search_query(float("nan"), 26.123456, 91.9) == "toll plaza near 26.1235,91.9000"
    assert search_query("  ", 1, 2).startswith("toll plaza near")


def test_llm_verify_sends_scraped_text():
    seen = {}

    def chat(msgs, model):
        seen["msgs"], seen["model"] = msgs, model
        return "It is real."

    assert llm_verify("Jorabat toll plaza NH-27 ...", "Jorabat", 26.1, 91.9, model="m", chat=chat) == "It is real."
    assert seen["msgs"][0]["role"] == "system"
    assert "Jorabat toll plaza NH-27" in seen["msgs"][1]["content"]   # old code sent text=""
    assert seen["model"] == "m"


def test_classify():
    assert classify_verification("real", chat=lambda m, model: "0") == 0
    assert classify_verification("fake", chat=lambda m, model: " 1 ") == 1
    assert classify_verification("x", chat=lambda m, model: "Answer: 0") == 0
    assert classify_verification("x", chat=lambda m, model: "") == 1          # old code: IndexError
    assert classify_verification("x", chat=lambda m, model: "maybe") == 1
    assert classify_verification("", chat=lambda m, model: "0") == 1


def test_classify_network_error_counts_as_invalid():
    def boom(m, model):
        raise requests.ConnectionError("ollama down")
    assert classify_verification("x", chat=boom) == 1


def test_verify_plazas_and_drop_invalid_pairs():
    plazas = pd.DataFrame({"plaza_id": [0, 1, 2], "lat": [26.0, 26.3, 26.5],
                           "lon": [91.0] * 3, "name": ["Real A", "Ghost", "Real C"]})

    def scrape(q):
        return "no results" if "Ghost" in q else f"{q} on NH-27"

    def chat(msgs, model):
        text = msgs[-1]["content"]
        if "single digit" in text:
            return "1" if "NOT FOUND" in text else "0"
        return "NOT FOUND" if "no results" in text else "Confirmed toll plaza"

    checked = verify_plazas(plazas, scrape, chat=chat)
    assert checked["invalid"].tolist() == [0, 1, 0]
    pairs = pd.DataFrame({"id_1": [0, 0], "id_2": [1, 2], "distance_km": [33.0, 55.0]})
    assert drop_invalid_pairs(pairs, checked)[["id_1", "id_2"]].values.tolist() == [[0, 2]]
