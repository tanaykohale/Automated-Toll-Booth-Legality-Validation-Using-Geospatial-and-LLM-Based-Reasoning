"""Web + local-LLM verification of candidate plazas.

1. Search the web for the plaza (by name, or by coordinates when unnamed).
2. A local Ollama model reads the page text and judges whether a toll plaza exists there.
3. A second, tiny prompt turns that explanation into 0 (real) / 1 (invalid / not found).

HTTP and browser calls are injectable so the logic can be tested offline.
"""
import time

import requests

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

TASK_PROMPT = (
    "You are verifying whether a location really has an operating toll plaza. "
    "You get text scraped from a web search, the expected toll name (may be unknown) "
    "and GPS coordinates. Decide whether this is a real toll plaza and justify briefly."
)


def ollama_chat(messages, model, url=OLLAMA_CHAT_URL, post=requests.post):
    r = post(url, json={"model": model, "messages": messages, "stream": False}, timeout=300)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "")


def search_query(name, lat, lon):
    if isinstance(name, str) and name.strip():
        return f"{name} toll plaza"
    return f"toll plaza near {lat:.4f},{lon:.4f}"


def llm_verify(text, name, lat, lon, model="llama3", chat=ollama_chat):
    user = (f"Toll name: {name or 'unknown'}\nCoordinates: ({lat:.6f}, {lon:.6f})\n"
            f"Web text:\n{text[:4000]}\n\nIs this a valid toll plaza?")
    return chat([{"role": "system", "content": TASK_PROMPT}, {"role": "user", "content": user}], model)


def classify_verification(explanation, model="llama3", chat=ollama_chat):
    """0 = real/confirmed, 1 = invalid/not found. Anything unclear counts as 1."""
    if not explanation or not explanation.strip():
        return 1
    prompt = ("Read this verification and reply with a single digit: 1 if it says the toll is "
              "invalid or not found, 0 if the toll is real or confirmed.\n\n" + explanation)
    try:
        reply = chat([{"role": "user", "content": prompt}], model).strip()
    except requests.RequestException:
        return 1
    for ch in reply:
        if ch in "01":
            return int(ch)
    return 1


class GoogleScraper:
    """Headless Chrome that returns the visible text of a Google results page."""

    def __init__(self, wait=2.5):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        opts = Options()
        for a in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage"):
            opts.add_argument(a)
        self.driver = webdriver.Chrome(options=opts)
        self.wait = wait

    def __call__(self, query):
        from selenium.webdriver.common.by import By

        self.driver.get("https://www.google.com/search?q=" + requests.utils.quote(query))
        time.sleep(self.wait)
        try:
            return self.driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            return ""

    def close(self):
        self.driver.quit()


def verify_plazas(plazas, scrape, model="llama3", chat=ollama_chat):
    """Add query / llm_explanation / invalid (0/1) columns to a plazas DataFrame."""
    df = plazas.copy()
    queries, explanations, flags = [], [], []
    for row in df.itertuples():
        q = search_query(row.name, row.lat, row.lon)
        text = scrape(q)
        try:
            exp = llm_verify(text, row.name, row.lat, row.lon, model=model, chat=chat)
        except requests.RequestException as e:
            exp = f"[verification failed: {e}]"
        queries.append(q)
        explanations.append(exp)
        flags.append(classify_verification(exp, model=model, chat=chat))
    df["query"], df["llm_explanation"], df["invalid"] = queries, explanations, flags
    return df


def drop_invalid_pairs(pairs, verified_plazas):
    """Keep only pairs where both plazas were verified as real (invalid == 0)."""
    real = set(verified_plazas.loc[verified_plazas["invalid"] == 0, "plaza_id"])
    keep = pairs["id_1"].isin(real) & pairs["id_2"].isin(real)
    return pairs[keep].reset_index(drop=True)
