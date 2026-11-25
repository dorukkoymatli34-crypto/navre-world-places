import argparse
import json
import os
import re
import time
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "places.json")
JS_PATH = os.path.join(BASE_DIR, "places.js")
CACHE_PATH = os.path.join(BASE_DIR, "ai_cache_gpt_oss.json")

DEFAULT_GROQ_KEY = "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"
MODEL_NAME = "llama-3.3-70b-versatile"

ALLOWED_CATEGORIES = [
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
]

HARD_BLOCK_REGEX = re.compile(
    r"\b(lisesi|anadolu lisesi|fen lisesi|meslek lisesi|koleji|okulu|ilkokulu|ortaokulu|"
    r"üniversitesi|universitesi|fakültesi|fakultesi|hastanesi|belediyesi|valiliği|"
    r"havalimanı|stadyumu|stadyum|oteli|hotel|avm|alışveriş merkezi|shopping mall|"
    r"istasyon|metro|marmaray|metrobüs|tramvay|durak|gar|terminal|iskele|otogar|"
    r"parkı|parki|park|otopark|korusu|koru|high school|school|university|hospital|airport|stadium)\b",
    re.IGNORECASE,
)

# Sadece en popüler başkentlerle sınırlı olmayan, dünya geneline yayılmış geniş hub listesi
# (hub_adi, lat, lon, yaricap_m, limit, lang)
WORLD_HUBS = [
    # Türkiye - farklı bölgeler
    ("TR-Canakkale-Assos-Boğaz", 39.8500, 26.3500, 10000, 90, "tr"),
    ("TR-Mardin-Midyat", 37.3131, 40.7350, 10000, 90, "tr"),
    ("TR-Ani-Kars", 40.5067, 43.5722, 10000, 80, "tr"),
    ("TR-Divrigi-Sivas", 39.3711, 38.1172, 10000, 80, "tr"),
    ("TR-Nemrut-Adiyaman", 37.9806, 38.7408, 10000, 80, "tr"),
    ("TR-Hattusas-Corum", 40.0194, 34.6156, 10000, 80, "tr"),
    ("TR-Myra-Kekova-Antalya", 36.2450, 29.9850, 10000, 90, "tr"),
    ("TR-Safranbolu-Karabuk", 41.2508, 32.6942, 10000, 80, "tr"),

    # Avrupa - klasiklerin yanı sıra Orta/Doğu/Kuzey/Güney Avrupa
    ("PT-Evora-Sintra", 38.5714, -7.9077, 10000, 90, "en"),
    ("HR-Dubrovnik-Split", 42.6507, 18.0944, 10000, 90, "en"),
    ("GE-Mtskheta-Tbilisi", 41.8425, 44.7186, 10000, 90, "en"),
    ("AM-Geghard-Etchmiadzin", 40.1406, 44.7986, 10000, 80, "en"),
    ("RO-Sighisoara-Transylvania", 46.2197, 24.7964, 10000, 90, "en"),
    ("PL-Krakow-Wieliczka", 50.0647, 19.9450, 10000, 90, "en"),
    ("SE-Visby-Gotland", 57.6348, 18.2948, 10000, 80, "en"),

    # Orta Doğu, Kafkasya & Orta Asya / İpek Yolu
    ("UZ-Samarkand-Registan", 39.6542, 66.9597, 10000, 100, "en"),
    ("UZ-Bukhara", 39.7747, 64.4286, 10000, 90, "en"),
    ("JO-Petra", 30.3285, 35.4444, 10000, 90, "en"),
    ("LB-Byblos-Baalbek", 34.1236, 35.6511, 10000, 80, "en"),

    # Afrika - Kuzey, Doğu ve Güney
    ("MA-Marrakesh-Fes", 31.6295, -7.9811, 10000, 100, "en"),
    ("ET-Lalibela-Aksum", 12.0319, 39.0475, 10000, 80, "en"),
    ("TZ-Kilwa-Zanzibar", -8.9500, 39.5167, 10000, 80, "en"),

    # Asya - Güney, Güneydoğu, Doğu
    ("IN-Hampi-Rajasthan", 15.3350, 76.4600, 10000, 100, "en"),
    ("KH-Angkor", 13.4125, 103.8670, 10000, 100, "en"),
    ("VN-Hue-HoiAn", 16.4637, 107.5909, 10000, 90, "en"),
    ("JP-Kamakura-Himeji", 34.8394, 134.6939, 10000, 90, "en"),

    # Amerika - Andlar, Mezoamerika, Kuzey
    ("PE-Cusco-SacredValley", -13.5319, -71.9675, 10000, 100, "en"),
    ("GT-Tikal-Antigua", 17.2220, -89.6237, 10000, 90, "en"),
    ("BO-Tiwanaku", -16.5547, -68.6736, 10000, 80, "en"),
]


def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def save_places(places):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(JS_PATH, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write(";\n")
        with open(JS_PATH, "r", encoding="utf-8") as rf:
            content = rf.read()
        if not content.startswith("window.NAVRE_SEED_PLACES = "):
            with open(JS_PATH, "w", encoding="utf-8") as wf:
                wf.write("window.NAVRE_SEED_PLACES = " + content)


def fetch_geosearch(lang, lat, lon, radius, limit):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lon}",
        "gsradius": radius,
        "gslimit": limit,
        "format": "json",
    }
    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": "NAVRE-GPT-OSS-Curator/1.0 (https://navre.app)"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("query", {}).get("geosearch", [])


def fetch_extracts(lang, titles):
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i : i + 40]
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "exchars": 240,
            "titles": "|".join(chunk),
            "format": "json",
        }
        resp = requests.get(
            url,
            params=params,
            headers={"User-Agent": "NAVRE-GPT-OSS-Curator/1.0 (https://navre.app)"},
            timeout=20,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for p in pages.values():
            t = (p.get("title") or "").strip().lower()
            if t:
                out[t] = (p.get("extract") or "").strip()
        time.sleep(0.15)
    return out


def parse_json_array_loose(raw_text: str):
    txt = (raw_text or "").strip()
    if not txt:
        return []
    txt = re.sub(r"^```(?:json)?\s*", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\s*```$", "", txt)
    try:
        parsed = json.loads(txt)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for k in ("results", "items", "places", "data"):
                if isinstance(parsed.get(k), list):
                    return parsed[k]
    except Exception:
        pass
    m = re.search(r"\[[\s\S]*\]", txt)
    if m:
        try:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                return arr
        except Exception:
            pass
    return []


def ask_groq_gpt_oss(items_batch, api_key: str):
    payload = [
        {"idx": i, "title": it["title"], "extract": it["extract"][:180]}
        for i, it in enumerate(items_batch)
    ]

    system_prompt = (
        "You curate historical and cultural heritage places for a discovery map app. "
        "When a user gets a notification and reads about a place, they should think: "
        "'Oh, that's genuinely interesting and historically/culturally meaningful.' "
        "Keep the list generous across diverse world regions, while filtering out modern schools, "
        "universities, hospitals, municipalities, stations, airports, stadiums, shopping malls, "
        "parks, neighborhoods, villages, rivers, mountains, or mundane/trivial entries. "
        f"Allowed categories: {ALLOWED_CATEGORIES}. "
        "Reply ONLY with a valid JSON array of objects: "
        '[{"idx": 0, "keep": true, "category": "castle"}]'
    )

    for attempt in range(4):
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            },
            timeout=60,
        )
        if resp.status_code == 429:
            wait_s = 6 * (attempt + 1)
            print(f"  [Rate limit 429] {wait_s} sn bekleniyor...")
            time.sleep(wait_s)
            continue
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"].get("content", "")
        return parse_json_array_loose(content)

    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--reset-places", action="store_true")
    args = parser.parse_args()

    api_key = (os.environ.get("GROQ_API_KEY") or DEFAULT_GROQ_KEY).strip()
    cache = load_cache()
    places = [] if args.reset_places else load_json_list(JSON_PATH)

    seen_coords = {
        (str(p.get("name", "")).strip().lower(), round(float(p.get("lat", 0)), 3), round(float(p.get("lon", 0)), 3))
        for p in places
    }

    candidates = []
    seen_cand = set()

    for hub_name, lat, lon, radius, limit, lang in WORLD_HUBS:
        try:
            raw = fetch_geosearch(lang, lat, lon, radius, limit)
            titles_to_fetch = []
            valid_raw = []
            for it in raw:
                title = (it.get("title") or "").strip()
                plat, plon = it.get("lat"), it.get("lon")
                if not title or not isinstance(plat, (int, float)) or not isinstance(plon, (int, float)):
                    continue
                if HARD_BLOCK_REGEX.search(title):
                    continue
                ckey = f"{lang}:{title.lower()}"
                if ckey in seen_cand:
                    continue
                seen_cand.add(ckey)
                valid_raw.append((title, float(plat), float(plon), it.get("pageid")))
                if ckey not in cache:
                    titles_to_fetch.append(title)

            extracts = fetch_extracts(lang, titles_to_fetch) if titles_to_fetch else {}
            for title, plat, plon, pageid in valid_raw:
                ckey = f"{lang}:{title.lower()}"
                candidates.append({
                    "ckey": ckey,
                    "lang": lang,
                    "title": title,
                    "lat": round(plat, 6),
                    "lon": round(plon, 6),
                    "pageid": pageid,
                    "extract": extracts.get(title.lower(), ""),
                })
        except Exception as e:
            print(f"[Geosearch Uyarı] {hub_name}: {e}")
        time.sleep(0.2)

    uncached = [c for c in candidates if c["ckey"] not in cache]
    print(f"Aday: {len(candidates)} | Önbellekte: {len(candidates) - len(uncached)} | gpt-oss-120b'ye sorulacak: {len(uncached)}")

    for i in range(0, len(uncached), args.batch_size):
        batch = uncached[i : i + args.batch_size]
        try:
            decisions = ask_groq_gpt_oss(batch, api_key=api_key)
            dec_map = {int(d.get("idx", -1)): d for d in decisions if isinstance(d, dict)}
            for idx_in_batch, item in enumerate(batch):
                d = dec_map.get(idx_in_batch)
                if not d:
                    continue
                keep = bool(d.get("keep"))
                cat = d.get("category")
                if cat not in ALLOWED_CATEGORIES:
                    cat = "monument"
                cache[item["ckey"]] = {"keep": keep, "category": cat if keep else None}
            save_cache(cache)
            print(f"[{min(i + len(batch), len(uncached))}/{len(uncached)}] gpt-oss-120b paket tamamlandı.")
        except Exception as e:
            print(f"[gpt-oss-120b Uyarı] {e} — 5 sn sonra devam...")
            time.sleep(5)
        time.sleep(1.5)

    final_places = []
    for c in candidates:
        decision = cache.get(c["ckey"])
        if not decision or not decision.get("keep"):
            continue
        dkey = (c["title"].lower(), round(c["lat"], 3), round(c["lon"], 3))
        if dkey in seen_coords and not args.reset_places:
            continue
        seen_coords.add(dkey)
        cat = decision.get("category")
        if cat not in ALLOWED_CATEGORIES:
            cat = "monument"
        final_places.append({
            "id": f"w-{c['lang']}/{c['pageid'] or len(places) + len(final_places) + 1}",
            "name": c["title"],
            "category": cat,
            "lat": c["lat"],
            "lon": c["lon"],
            "wikiTitle": c["title"],
        })

    merged = final_places if args.reset_places else (places + final_places)
    save_places(merged)
    print(f"Bitti! Toplam nitelikli kayıt: {len(merged)} | Önbellekteki toplam karar: {len(cache)}")


if __name__ == "__main__":
    main()

