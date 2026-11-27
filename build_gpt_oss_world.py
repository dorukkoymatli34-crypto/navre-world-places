import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CHUNKS_DIR = DATA_DIR / "chunks"
ROOT_CHUNKS_DIR = ROOT / "chunks"

PLACES_JSON = DATA_DIR / "places.json"
PLACES_JS = DATA_DIR / "places.js"
STATE_JSON = DATA_DIR / "progress_state.json"
CACHE_JSON = DATA_DIR / "ai_cache_gpt_oss.json"

ROOT_PLACES_JSON = ROOT / "places.json"
ROOT_PLACES_JS = ROOT / "places.js"
ROOT_STATE_JSON = ROOT / "progress_state.json"
ROOT_CACHE_JSON = ROOT / "ai_cache_gpt_oss.json"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

OPENROUTER_FREE_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/free",
]

ALLOWED_CATEGORIES = {
    "castle",
    "palace",
    "mosque",
    "church",
    "synagogue",
    "monastery",
    "temple",
    "archaeological_site",
    "ruins",
    "museum",
    "cistern",
    "aqueduct",
    "tomb",
    "tower",
    "bridge",
    "monument",
}

HARD_BLOCK_REGEX = re.compile(
    r"\b("
    r"airport|railway station|train station|metro station|subway station|bus station|"
    r"shopping mall|supermarket|hypermarket|department store|outlet|retail park|"
    r"stadium|arena|golf course|ski resort|theme park|amusement park|water park|"
    r"hospital|clinic|university|college|high school|elementary school|campus|"
    r"power plant|dam|reservoir|wind farm|solar farm|factory|refinery|industrial|"
    r"election|referendum|earthquake|flood|hurricane|typhoon|massacre|battle of|"
    r"municipality|district of|province of|county of|prefecture|commune of|"
    r"belediyesi|ilçesi|ili|bucak|mahallesi|köyü|list of"
    r")\b",
    re.IGNORECASE,
)

GLOBAL_GRID_BANDS = [
    ("turkiye_anatolia", "middle-east-anatolia", 35.8, 42.2, 25.8, 44.8, 0.48, 0.56, 10000, "tr"),
    ("levant_mesopotamia_persia", "middle-east-anatolia", 29.0, 39.5, 34.5, 61.0, 0.65, 0.75, 10000, "en"),
    ("egypt_north_africa", "africa", 22.0, 37.2, -10.5, 35.0, 0.75, 0.85, 10000, "en"),
    ("sub_saharan_africa", "africa", -34.8, 17.5, -17.5, 51.0, 0.95, 1.05, 10000, "en"),
    ("western_central_europe", "europe", 36.0, 60.5, -10.0, 22.0, 0.55, 0.65, 10000, "en"),
    ("eastern_northern_europe", "europe", 44.0, 69.5, 22.0, 45.0, 0.70, 0.85, 10000, "en"),
    ("south_southeast_asia", "asia", -10.5, 28.5, 68.0, 126.0, 0.75, 0.85, 10000, "en"),
    ("east_central_asia", "asia", 22.0, 52.0, 62.0, 145.0, 0.80, 0.90, 10000, "en"),
    ("north_america", "americas", 18.0, 62.0, -135.0, -60.0, 0.90, 1.05, 10000, "en"),
    ("mesoamerica_south_america", "americas", -54.0, 18.0, -105.0, -35.0, 0.85, 0.95, 10000, "en"),
    ("oceania", "oceania", -46.0, -10.0, 113.0, 178.0, 1.00, 1.15, 10000, "en"),
]

ICONIC_ANCHORS = [
    ("Sultanahmet / Fatih, Istanbul", "middle-east-anatolia", 41.0086, 28.9802, 7500, "tr"),
    ("Beyoglu / Karakoy, Istanbul", "middle-east-anatolia", 41.0285, 28.9765, 7500, "tr"),
    ("Uskudar / Kadikoy, Istanbul", "middle-east-anatolia", 41.0120, 29.0250, 8500, "tr"),
    ("Edirne Merkez", "middle-east-anatolia", 41.6771, 26.5557, 8000, "tr"),
    ("Bursa Merkez", "middle-east-anatolia", 40.1885, 29.0610, 8500, "tr"),
    ("Selcuk / Efes, Izmir", "middle-east-anatolia", 37.9497, 27.3639, 9000, "tr"),
    ("Bergama, Izmir", "middle-east-anatolia", 39.1214, 27.1836, 9000, "tr"),
    ("Goreme / Urgup, Kapadokya", "middle-east-anatolia", 38.6431, 34.8289, 10000, "tr"),
    ("Konya Merkez", "middle-east-anatolia", 37.8714, 32.4846, 9000, "tr"),
    ("Mardin Merkez", "middle-east-anatolia", 37.3122, 40.7350, 9000, "tr"),
    ("Diyarbakir Sur", "middle-east-anatolia", 37.9100, 40.2366, 8500, "tr"),
    ("Sanliurfa / Gobeklitepe", "middle-east-anatolia", 37.1850, 38.8500, 10000, "tr"),
    ("Ani, Kars", "middle-east-anatolia", 40.5069, 43.5722, 9000, "tr"),
    ("Centro Storico / Colosseum, Rome", "europe", 41.8925, 12.4853, 7500, "en"),
    ("Vatican / Castel Sant'Angelo, Rome", "europe", 41.9029, 12.4534, 7000, "en"),
    ("Acropolis / Plaka, Athens", "europe", 37.9715, 23.7257, 7500, "en"),
    ("Ile de la Cite / Louvre, Paris", "europe", 48.8566, 2.3522, 8000, "en"),
    ("Westminster / Tower, London", "europe", 51.5055, -0.1050, 8500, "en"),
    ("Alhambra / Albayzin, Granada", "europe", 37.1760, -3.5881, 8000, "en"),
    ("Innere Stadt, Vienna", "europe", 48.2082, 16.3738, 8000, "en"),
    ("Old Town / Prague Castle", "europe", 50.0880, 14.4208, 8000, "en"),
    ("Hradcany / Lesser Town, Prague", "europe", 50.0909, 14.4006, 7500, "en"),
    ("Buda Castle / Pest, Budapest", "europe", 47.4979, 19.0402, 8500, "en"),
    ("Dubrovnik Old Town", "europe", 42.6414, 18.1086, 7500, "en"),
    ("Giza Necropolis, Cairo", "middle-east-anatolia", 29.9792, 31.1342, 9500, "en"),
    ("Islamic / Coptic Cairo", "middle-east-anatolia", 30.0250, 31.2450, 9000, "en"),
    ("Luxor / Karnak", "middle-east-anatolia", 25.7188, 32.6573, 10000, "en"),
    ("Petra, Jordan", "middle-east-anatolia", 30.3285, 35.4444, 9500, "en"),
    ("Persepolis, Iran", "middle-east-anatolia", 29.9352, 52.8916, 9500, "en"),
    ("Isfahan Naqsh-e Jahan", "middle-east-anatolia", 32.6572, 51.6776, 9000, "en"),
    ("Medina of Fez, Morocco", "africa", 34.0631, -4.9780, 8500, "en"),
    ("Marrakech Medina", "africa", 31.6295, -7.9811, 8500, "en"),
    ("Lalibela, Ethiopia", "africa", 12.0319, 39.0476, 9000, "en"),
    ("Great Zimbabwe", "africa", -20.2742, 30.9336, 9500, "en"),
    ("Forbidden City, Beijing", "asia", 39.9163, 116.3972, 9000, "en"),
    ("Higashiyama / Central Kyoto", "asia", 35.0116, 135.7681, 8500, "en"),
    ("Angkor Archaeological Park", "asia", 13.4125, 103.8670, 10000, "en"),
    ("Agra / Taj Mahal", "asia", 27.1751, 78.0421, 9000, "en"),
    ("Old Delhi, India", "asia", 28.6562, 77.2410, 9000, "en"),
    ("Samarkand Registan", "asia", 39.6542, 66.9756, 9000, "en"),
    ("Bukhara Historic Center", "asia", 39.7747, 64.4286, 9000, "en"),
    ("Gyeongju Historic Areas", "asia", 35.8562, 129.2247, 9500, "en"),
    ("Zocalo / Historic Center, Mexico City", "americas", 19.4326, -99.1332, 8500, "en"),
    ("Cusco / Machu Picchu Axis", "americas", -13.5319, -71.9675, 9500, "en"),
    ("Teotihuacan", "americas", 19.6925, -98.8435, 9500, "en"),
    ("Cartagena Old Town", "americas", 10.4236, -75.5517, 8000, "en"),
    ("Boston Freedom Trail / Beacon Hill", "americas", 42.3588, -71.0636, 8500, "en"),
    ("Aotearoa / Waitangi & Rotorua", "oceania", -38.1368, 176.2497, 10000, "en"),
]


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--max-new-per-run", type=int, default=0)
    parser.add_argument("--max-hubs", type=int, default=300)
    parser.add_argument("--max-seconds", type=int, default=720)
    args, _ = parser.parse_known_args()
    return args


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_first_existing(paths: list[Path], default):
    for p in paths:
        if p.exists():
            val = load_json(p, None)
            if val is not None:
                return val
    return default


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_hubs() -> list[dict]:
    hubs: list[dict] = []
    seen_coords: set[tuple[float, float, str]] = set()

    for label, region, lat, lon, radius, lang in ICONIC_ANCHORS:
        key = (round(lat, 2), round(lon, 2), lang)
        if key not in seen_coords:
            seen_coords.add(key)
            hubs.append(
                {
                    "id": f"anchor-{region}-{len(hubs)}",
                    "label": label,
                    "region": region,
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "radius": radius,
                    "lang": lang,
                }
            )

    for band_name, region, lat_min, lat_max, lon_min, lon_max, lat_step, lon_step, radius, lang in GLOBAL_GRID_BANDS:
        lat = lat_min
        while lat <= lat_max + 1e-9:
            lon = lon_min
            while lon <= lon_max + 1e-9:
                key = (round(lat, 2), round(lon, 2), lang)
                if key not in seen_coords:
                    seen_coords.add(key)
                    hubs.append(
                        {
                            "id": f"{band_name}-{len(hubs)}",
                            "label": f"{band_name} ({lat:.2f}, {lon:.2f})",
                            "region": region,
                            "lat": round(lat, 4),
                            "lon": round(lon, 4),
                            "radius": radius,
                            "lang": lang,
                        }
                    )
                lon += lon_step
            lat += lat_step

    return hubs


def http_get_json(url: str, timeout: int = 20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NAVRE-World-Curator/2.4 (contact@navre.app)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wiki_get_with_retry(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return http_get_json(url, timeout=20)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            if e.code in (500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except Exception:
            time.sleep(1.0 * (attempt + 1))
    return None


def fetch_geosearch(lat: float, lon: float, radius_m: int, lang: str, limit: int = 500) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat}|{lon}",
            "gsradius": min(max(radius_m, 100), 10000),
            "gslimit": min(max(limit, 1), 500),
            "format": "json",
        }
    )
    url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
    data = wiki_get_with_retry(url)
    if not isinstance(data, dict):
        return []
    return data.get("query", {}).get("geosearch", []) or []


def fetch_extracts(pageids: list[int], lang: str) -> dict[str, str]:
    extracts: dict[str, str] = {}
    for i in range(0, len(pageids), 50):
        batch = pageids[i : i + 50]
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "prop": "extracts",
                "exintro": "1",
                "explaintext": "1",
                "exchars": "260",
                "pageids": "|".join(str(pid) for pid in batch),
                "format": "json",
            }
        )
        url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
        data = wiki_get_with_retry(url)
        if isinstance(data, dict):
            pages = data.get("query", {}).get("pages", {}) or {}
            for pid_str, page_obj in pages.items():
                if isinstance(page_obj, dict):
                    extracts[str(pid_str)] = (page_obj.get("extract") or "").strip()
    return extracts


def is_hard_blocked(title: str, extract: str) -> bool:
    combined = f"{title} {extract}".strip()
    if not combined:
        return True
    return bool(HARD_BLOCK_REGEX.search(combined))


def parse_json_array_response(content: str) -> list[dict] | None:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return None
    raw_json = match.group(0)
    try:
        parsed = json.loads(raw_json)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        cleaned = re.sub(r",\s*([\]}])", r"\1", raw_json)
        last_brace = cleaned.rfind("}")
        if last_brace != -1:
            candidate = cleaned[: last_brace + 1].rstrip(",") + "]"
            try:
                parsed = json.loads(candidate)
                return parsed if isinstance(parsed, list) else None
            except Exception:
                return None
        return None


def call_openai_compatible(endpoint: str, api_key: str, model: str, messages: list[dict], extra_headers: dict | None = None):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2200,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "NAVRE-World-Curator/2.4",
    }
    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def call_gemini(api_key: str, model: str, system_prompt: str, user_prompt: str):
    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={urllib.parse.quote(api_key)}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "NAVRE-World-Curator/2.4"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    cands = body.get("candidates") or []
    parts = ((cands[0].get("content") or {}).get("parts") or []) if cands else []
    return "".join(str(p.get("text") or "") for p in parts)


def curate_batch_with_ai(
    candidates: list[dict],
    gemini_key: str,
    groq_key: str,
    openrouter_key: str,
    cache: dict,
    deadline: float | None = None,
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    uncached: list[dict] = []

    for item in candidates:
        c_key = f"{item['lang']}:{item['pageid']}"
        if c_key in cache:
            results[c_key] = cache[c_key]
        else:
            uncached.append(item)

    if not uncached:
        return results

    system_prompt = (
        "You are a high-bar historical & cultural heritage curator for NAVRE.\n"
        "Select ONLY genuinely notable, historically or architecturally significant heritage landmarks, "
        "monuments, archaeological sites, ruins, historic palaces/castles/towers/bridges/cisterns/aqueducts/tombs, "
        "ancient temples/churches/mosques/synagogues/monasteries, or notable museums.\n"
        "Reject minor/obscure/trivial entries, modern buildings, administrative units, settlements, nature/geography, "
        "schools, hospitals, malls, sports venues, or events.\n"
        "Allowed categories: castle, palace, mosque, church, synagogue, monastery, temple, archaeological_site, "
        "ruins, museum, cistern, aqueduct, tomb, tower, bridge, monument.\n"
        "Return ONLY a JSON array: [{\"idx\": 0, \"keep\": true/false, \"score\": 1-10, \"category\": \"...\"}]."
    )

    compact_list = [
        {
            "idx": i,
            "title": c["title"],
            "lang": c["lang"],
            "summary": (c.get("extract") or "")[:200],
        }
        for i, c in enumerate(uncached)
    ]
    user_prompt = json.dumps(compact_list, ensure_ascii=False)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    backoff = 15.0
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            return results

        parsed_arr = None
        hit_429 = False

        if gemini_key:
            for m in GEMINI_MODELS:
                try:
                    raw = call_gemini(gemini_key, m, system_prompt, user_prompt)
                    arr = parse_json_array_response(raw)
                    if arr is not None:
                        parsed_arr = arr
                        break
                except urllib.error.HTTPError as e:
                    print(f"  [Gemini {e.code}] {m} gecildi.", flush=True)
                    if e.code == 429:
                        hit_429 = True
                except Exception as exc:
                    print(f"  [Gemini Err] {m}: {str(exc)[:70]}", flush=True)

        if parsed_arr is None:
            providers = []
            if groq_key:
                for m in GROQ_MODELS:
                    providers.append(("Groq", GROQ_API_URL, groq_key, m, None))
            if openrouter_key:
                or_headers = {"HTTP-Referer": "[https://navre.app](https://navre.app)", "X-Title": "NAVRE World Curator"}
                for m in OPENROUTER_FREE_MODELS:
                    providers.append(("OpenRouter", OPENROUTER_API_URL, openrouter_key, m, or_headers))

            for prov_name, endpoint, key, model_name, extra_hdrs in providers:
                try:
                    raw = call_openai_compatible(endpoint, key, model_name, messages, extra_hdrs)
                    arr = parse_json_array_response(raw)
                    if arr is not None:
                        parsed_arr = arr
                        break
                except urllib.error.HTTPError as e:
                    print(f"  [{prov_name} {e.code}] {model_name} gecildi.", flush=True)
                    if e.code == 429:
                        hit_429 = True
                except Exception as exc:
                    print(f"  [{prov_name} Err] {model_name}: {str(exc)[:70]}", flush=True)

        if parsed_arr is not None:
            decision_by_idx: dict[int, dict] = {}
            for entry in parsed_arr:
                if isinstance(entry, dict) and isinstance(entry.get("idx"), int):
                    score = entry.get("score", 6.5)
                    try:
                        score_num = float(score)
                    except Exception:
                        score_num = 6.5
                    keep = bool(entry.get("keep")) and (score_num >= 6.5)
                    cat = (entry.get("category") or "monument").strip().lower()
                    if cat not in ALLOWED_CATEGORIES:
                        cat = "monument"
                    decision_by_idx[entry["idx"]] = {"keep": keep, "category": cat}

            for idx, item in enumerate(uncached):
                if idx in decision_by_idx:
                    dec = decision_by_idx[idx]
                    c_key = f"{item['lang']}:{item['pageid']}"
                    cache[c_key] = dec
                    results[c_key] = dec
            return results

        if hit_429:
            sleep_sec = min(backoff, 180.0)
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 2.0:
                    return results
                sleep_sec = min(sleep_sec, max(1.0, remaining - 1.0))
            print(f"  [Rate Limit 429] Tum modeller limitli, {sleep_sec:.0f}s bekleniyor...", flush=True)
            time.sleep(sleep_sec)
            backoff = min(backoff * 1.5, 180.0)
        else:
            return results


def dedupe_and_clean_places(raw_places: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    seen_ids: set[str] = set()
    seen_coord_name: set[tuple[float, float, str]] = set()
    seen_nearby_name: set[tuple[float, float, str]] = set()

    for p in raw_places:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        name = str(p.get("name") or "").strip()
        cat = str(p.get("category") or "monument").strip().lower()
        region = str(p.get("region") or "europe").strip().lower()
        wiki_title = str(p.get("wikiTitle") or name).strip()

        try:
            lat = float(p["lat"])
            lon = float(p["lon"])
        except Exception:
            continue

        if not name or not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            continue
        if cat not in ALLOWED_CATEGORIES:
            cat = "monument"
        if is_hard_blocked(name, ""):
            continue

        norm_name = re.sub(r"\s+", " ", name.lower()).strip()
        coord_key = (round(lat, 4), round(lon, 4), norm_name)
        nearby_key = (round(lat, 2), round(lon, 2), norm_name)

        if (pid and pid in seen_ids) or coord_key in seen_coord_name or nearby_key in seen_nearby_name:
            continue

        if pid:
            seen_ids.add(pid)
        seen_coord_name.add(coord_key)
        seen_nearby_name.add(nearby_key)

        cleaned.append(
            {
                "id": pid or f"w/{hashlib.md5(f'{name}:{lat}:{lon}'.encode()).hexdigest()[:10]}",
                "name": name,
                "category": cat,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "wikiTitle": wiki_title,
                "region": region,
            }
        )

    return cleaned


def rebuild_and_save(places: list[dict], sync_chunks: bool = True) -> list[dict]:
    cleaned = dedupe_and_clean_places(places)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    save_json(PLACES_JSON, cleaned)
    save_json(ROOT_PLACES_JSON, cleaned)

    js_body = "window.NAVRE_SEED_PLACES = " + json.dumps(cleaned, ensure_ascii=False) + ";\n"
    PLACES_JS.write_text(js_body, encoding="utf-8")
    ROOT_PLACES_JS.write_text(js_body, encoding="utf-8")

    if sync_chunks or not CHUNKS_DIR.exists():
        CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
        ROOT_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
        chunk_size = 250
        index_manifest = []
        for idx in range(0, len(cleaned), chunk_size):
            part = cleaned[idx : idx + chunk_size]
            part_num = (idx // chunk_size) + 1
            fname = f"places-{part_num:03d}.json"
            save_json(CHUNKS_DIR / fname, part)
            save_json(ROOT_CHUNKS_DIR / fname, part)
            index_manifest.append({"file": fname, "count": len(part)})

        save_json(
            DATA_DIR / "index.json",
            {
                "total": len(cleaned),
                "chunkSize": chunk_size,
                "chunks": index_manifest,
            },
        )
    return cleaned


def main():
    args = parse_args()
    start_time = time.monotonic()
    batch_size = max(10, int(os.environ.get("BATCH_SIZE", str(args.batch_size))))
    max_new_per_run = int(os.environ.get("MAX_NEW_PER_RUN", str(args.max_new_per_run)))
    max_hubs = int(os.environ.get("MAX_HUBS_PER_RUN", str(args.max_hubs)))
    max_seconds = int(os.environ.get("MAX_SECONDS_PER_RUN", str(args.max_seconds)))
    deadline = start_time + max_seconds

    gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    openrouter_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()

    hubs = build_hubs()
    total_hubs = len(hubs)

    p1 = load_json(ROOT_PLACES_JSON, [])
    p2 = load_json(PLACES_JSON, [])
    if isinstance(p1, dict) and isinstance(p1.get("places"), list):
        p1 = p1["places"]
    if isinstance(p2, dict) and isinstance(p2.get("places"), list):
        p2 = p2["places"]
    combined_existing = (p1 if isinstance(p1, list) else []) + (p2 if isinstance(p2, list) else [])
    places = dedupe_and_clean_places(combined_existing)

    cache = load_first_existing([ROOT_CACHE_JSON, CACHE_JSON], {})
    if not isinstance(cache, dict):
        cache = {}

    state = load_first_existing([ROOT_STATE_JSON, STATE_JSON], {})
    if not isinstance(state, dict):
        state = {}

    grid_signature = hashlib.md5(f"{total_hubs}:{len(GLOBAL_GRID_BANDS)}:{len(ICONIC_ANCHORS)}".encode()).hexdigest()[:10]
    if state.get("grid_signature") != grid_signature:
        current_idx = 0
    else:
        current_idx = int(state.get("hub_index", 0)) % max(total_hubs, 1)

    completed_cycles = int(state.get("completed_cycles", 0))
    seen_page_keys: set[str] = {str(p.get("id")) for p in places if p.get("id")}

    start_idx = current_idx
    processed_in_run = 0
    candidates_buffer: list[dict] = []
    candidate_meta_map: dict[str, dict] = {}
    new_added_count = 0
    dirty_since_save = False

    active_sources = [
        name
        for name, enabled in [
            ("Gemini", bool(gemini_key)),
            ("Groq", bool(groq_key)),
            ("OpenRouter", bool(openrouter_key)),
        ]
        if enabled
    ]
    print(
        f"Toplam hub: {total_hubs} | Baslangic indeksi: {current_idx} | "
        f"Mevcut kayit: {len(places)} | Saglayicilar: {', '.join(active_sources) or 'YOK'}",
        flush=True,
    )

    def flush_candidates():
        nonlocal places, new_added_count, dirty_since_save
        if not candidates_buffer:
            return
        decisions = curate_batch_with_ai(
            candidates_buffer,
            gemini_key,
            groq_key,
            openrouter_key,
            cache,
            deadline=deadline,
        )
        for c_key, dec in decisions.items():
            if dec.get("keep") and c_key in candidate_meta_map:
                if max_new_per_run > 0 and new_added_count >= max_new_per_run:
                    break
                meta = candidate_meta_map[c_key]
                if meta["id"] not in seen_page_keys:
                    seen_page_keys.add(meta["id"])
                    places.append(
                        {
                            "id": meta["id"],
                            "name": meta["title"],
                            "category": dec.get("category", "monument"),
                            "lat": meta["lat"],
                            "lon": meta["lon"],
                            "wikiTitle": meta["title"],
                            "region": meta["region"],
                        }
                    )
                    new_added_count += 1
                    dirty_since_save = True
        candidates_buffer.clear()
        candidate_meta_map.clear()

    def save_all_state(force_chunks: bool = False):
        nonlocal places, dirty_since_save
        places = rebuild_and_save(places, sync_chunks=(force_chunks or dirty_since_save))
        save_json(ROOT_CACHE_JSON, cache)
        save_json(CACHE_JSON, cache)
        st = {
            "grid_signature": grid_signature,
            "hub_index": current_idx,
            "completed_cycles": completed_cycles,
            "total_places": len(places),
            "total_hubs": total_hubs,
        }
        save_json(ROOT_STATE_JSON, st)
        save_json(STATE_JSON, st)
        dirty_since_save = False

    while processed_in_run < max_hubs and time.monotonic() < deadline:
        if max_new_per_run > 0 and new_added_count >= max_new_per_run:
            break

        hub = hubs[current_idx]
        lang = hub["lang"]
        geo_items = fetch_geosearch(hub["lat"], hub["lon"], hub["radius"], lang, limit=500)

        page_ids_to_fetch: list[int] = []
        raw_items_by_pid: dict[int, dict] = {}

        for g in geo_items:
            pid = g.get("pageid")
            title = (g.get("title") or "").strip()
            lat = g.get("lat")
            lon = g.get("lon")
            if not isinstance(pid, int) or not title or lat is None or lon is None:
                continue

            rec_id = f"w-{lang}/{pid}"
            c_key = f"{lang}:{pid}"
            if rec_id in seen_page_keys or c_key in cache:
                continue

            raw_items_by_pid[pid] = {
                "pageid": pid,
                "id": rec_id,
                "title": title,
                "lat": float(lat),
                "lon": float(lon),
                "lang": lang,
                "region": hub["region"],
            }
            page_ids_to_fetch.append(pid)

        if page_ids_to_fetch:
            extracts = fetch_extracts(page_ids_to_fetch, lang)
            for pid in page_ids_to_fetch:
                item = raw_items_by_pid[pid]
                ext = extracts.get(str(pid), "")
                if is_hard_blocked(item["title"], ext):
                    cache[f"{lang}:{pid}"] = {"keep": False, "category": "monument"}
                    continue
                item["extract"] = ext
                c_key = f"{lang}:{pid}"
                candidates_buffer.append(item)
                candidate_meta_map[c_key] = item

        if len(candidates_buffer) >= batch_size:
            flush_candidates()

        processed_in_run += 1
        current_idx += 1
        if current_idx >= total_hubs:
            current_idx = 0
            completed_cycles += 1
            print(f"[Dongu Tamamlandi] Toplam tamamlanan dongu: {completed_cycles}", flush=True)

        if processed_in_run % 100 == 0:
            flush_candidates()
            save_all_state(force_chunks=False)
            print(
                f"  Tur ici hub: {processed_in_run}/{max_hubs} | Sonraki indeks: {current_idx}/{total_hubs} | "
                f"Toplam nitelikli yer: {len(places)}",
                flush=True,
            )

    flush_candidates()
    save_all_state(force_chunks=True)

    print(
        f"Tur bitti! Baslangic: {start_idx} -> Sonraki indeks: {current_idx}/{total_hubs} | "
        f"Bu tur eklenen: +{new_added_count} | Toplam nitelikli yer: {len(places)} | "
        f"Onbellek karar: {len(cache)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
