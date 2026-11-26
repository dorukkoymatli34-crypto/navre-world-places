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
CHUNKS_DIR = os.path.join(BASE_DIR, "chunks")

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
    r"havalimanı|stadyumu|stadyum|oteli|hotel|lodge|resort|avm|alışveriş merkezi|shopping mall|"
    r"istasyon|metro|marmaray|metrobüs|tramvay|durak|gar|terminal|iskele|otogar|"
    r"parkı|parki|park|otopark|korusu|koru|high school|school|university|hospital|airport|stadium|"
    r"siege of|massacre|attack)\b",
    re.IGNORECASE,
)

# (hub_adi, lat, lon, yaricap_m, limit, lang, region)
WORLD_HUBS = [
    # Türkiye - geniş tarihi akslar
    ("TR-Istanbul-Historic", 41.0082, 28.9784, 15000, 200, "tr", "middle-east-anatolia"),
    ("TR-Edirne", 41.6771, 26.5557, 12000, 120, "tr", "middle-east-anatolia"),
    ("TR-Bursa-Iznik", 40.1885, 29.0610, 15000, 150, "tr", "middle-east-anatolia"),
    ("TR-Izmir-Efes-Bergama", 37.9497, 27.3686, 20000, 180, "tr", "middle-east-anatolia"),
    ("TR-Canakkale-Assos-Troy", 39.8500, 26.3500, 18000, 150, "tr", "middle-east-anatolia"),
    ("TR-Konya", 37.8714, 32.4846, 15000, 140, "tr", "middle-east-anatolia"),
    ("TR-Kapadokya-Nevsehir", 38.6431, 34.8289, 20000, 180, "tr", "middle-east-anatolia"),
    ("TR-Mardin-Midyat", 37.3131, 40.7350, 15000, 140, "tr", "middle-east-anatolia"),
    ("TR-Sanliurfa-Gobeklitepe", 37.1591, 38.7969, 20000, 150, "tr", "middle-east-anatolia"),
    ("TR-Diyarbakir", 37.9144, 40.2306, 15000, 120, "tr", "middle-east-anatolia"),
    ("TR-Ani-Kars", 40.5067, 43.5722, 15000, 120, "tr", "middle-east-anatolia"),
    ("TR-Divrigi-Sivas", 39.3711, 38.1172, 12000, 100, "tr", "middle-east-anatolia"),
    ("TR-Nemrut-Adiyaman", 37.9806, 38.7408, 15000, 100, "tr", "middle-east-anatolia"),
    ("TR-Hattusas-Corum", 40.0194, 34.6156, 15000, 100, "tr", "middle-east-anatolia"),
    ("TR-Myra-Kekova-Antalya", 36.2450, 29.9850, 20000, 160, "tr", "middle-east-anatolia"),
    ("TR-Safranbolu-Karabuk", 41.2508, 32.6942, 12000, 100, "tr", "middle-east-anatolia"),
    ("TR-Trabzon-Sumela", 41.0027, 39.7168, 18000, 130, "tr", "middle-east-anatolia"),

    # Avrupa
    ("IT-Rome", 41.8902, 12.4922, 15000, 200, "en", "europe"),
    ("IT-Florence-Siena", 43.7696, 11.2558, 15000, 160, "en", "europe"),
    ("IT-Venice-Pompeii", 45.4340, 12.3388, 15000, 160, "en", "europe"),
    ("GR-Athens", 37.9715, 23.7257, 15000, 200, "en", "europe"),
    ("FR-Paris", 48.8566, 2.3522, 15000, 200, "en", "europe"),
    ("ES-Madrid-Toledo", 40.4168, -3.7038, 18000, 180, "en", "europe"),
    ("ES-Granada-Cordoba-Seville", 37.1773, -3.5986, 20000, 180, "en", "europe"),
    ("PT-Lisbon-Evora-Sintra", 38.7223, -9.1393, 20000, 160, "en", "europe"),
    ("AT-Vienna", 48.2082, 16.3738, 15000, 180, "en", "europe"),
    ("UK-London", 51.5072, -0.1276, 15000, 200, "en", "europe"),
    ("UK-Edinburgh-Oxford", 55.9533, -3.1883, 15000, 150, "en", "europe"),
    ("DE-Berlin-Munich", 52.5200, 13.4050, 15000, 160, "en", "europe"),
    ("CZ-Prague", 50.0755, 14.4378, 15000, 160, "en", "europe"),
    ("HU-Budapest", 47.4979, 19.0402, 15000, 150, "en", "europe"),
    ("PL-Krakow", 50.0647, 19.9450, 15000, 150, "en", "europe"),
    ("HR-Dubrovnik-Split", 42.6507, 18.0944, 15000, 140, "en", "europe"),
    ("RO-Sighisoara-Brasov", 46.2197, 24.7964, 18000, 130, "en", "europe"),
    ("GE-Mtskheta-Tbilisi", 41.8425, 44.7186, 18000, 140, "en", "europe"),
    ("AM-Geghard-Etchmiadzin", 40.1406, 44.7986, 18000, 120, "en", "europe"),
    ("SE-Stockholm-Visby", 59.3293, 18.0686, 15000, 130, "en", "europe"),

    # Orta Doğu, Kafkasya & Orta Asya
    ("EG-Cairo-Giza", 30.0444, 31.2357, 20000, 200, "en", "middle-east-anatolia"),
    ("EG-Luxor-Karnak", 25.6872, 32.6396, 20000, 180, "en", "middle-east-anatolia"),
    ("JO-Petra", 30.3285, 35.4444, 18000, 140, "en", "middle-east-anatolia"),
    ("LB-Byblos-Baalbek", 34.1236, 35.6511, 20000, 130, "en", "middle-east-anatolia"),
    ("IR-Persepolis-Shiraz-Isfahan", 29.9352, 52.8916, 20000, 160, "en", "middle-east-anatolia"),
    ("UZ-Samarkand", 39.6542, 66.9597, 18000, 150, "en", "asia"),
    ("UZ-Bukhara-Khiva", 39.7747, 64.4286, 18000, 140, "en", "asia"),

    # Afrika
    ("MA-Marrakesh-Fes", 31.6295, -7.9811, 20000, 160, "en", "africa"),
    ("ET-Lalibela-Aksum", 12.0319, 39.0475, 20000, 120, "en", "africa"),
    ("TZ-Kilwa-Zanzibar", -8.9500, 39.5167, 20000, 120, "en", "africa"),

    # Asya
    ("IN-Agra-Delhi", 27.1751, 78.0421, 20000, 180, "en", "asia"),
    ("IN-Hampi-Jaipur", 15.3350, 76.4600, 20000, 160, "en", "asia"),
    ("KH-Angkor", 13.4125, 103.8670, 20000, 160, "en", "asia"),
    ("VN-Hue-HoiAn", 16.4637, 107.5909, 20000, 140, "en", "asia"),
    ("CN-Beijing", 39.9042, 116.4074, 20000, 200, "en", "asia"),
    ("CN-Xian", 34.3416, 108.9398, 20000, 160, "en", "asia"),
    ("JP-Kyoto-Nara", 35.0116, 135.7681, 20000, 200, "en", "asia"),
    ("JP-Kamakura-Himeji", 34.8394, 134.6939, 18000, 150, "en", "asia"),

    # Amerika
    ("PE-Cusco-MachuPicchu", -13.5319, -71.9675, 20000, 180, "en", "americas"),
    ("MX-MexicoCity-Teotihuacan", 19.4326, -99.1332, 20000, 180, "en", "americas"),
    ("GT-Tikal-Antigua", 17.2220, -89.6237, 20000, 140, "en", "americas"),
    ("BO-Tiwanaku", -16.5547, -68.6736, 18000, 120, "en", "americas"),
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
    cleaned = []
    for p in places:
        if not isinstance(p, dict):
            continue
        lat = p.get("lat")
        lon = p.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        item = dict(p)
        item["lat"] = round(float(lat), 6)
        item["lon"] = round(float(lon), 6)
        if not item.get("region"):
            item["region"] = "global"
        cleaned.append(item)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(JS_PATH, "w", encoding="utf-8") as f:
        f.write("window.NAVRE_SEED_PLACES = ")
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    os.makedirs(CHUNKS_DIR, exist_ok=True)
    grouped = {}
    for p in cleaned:
        reg = re.sub(r"[^a-z0-9-]", "", str(p.get("region", "global")).lower()) or "global"
        grouped.setdefault(reg, []).append(p)

    for reg, items in grouped.items():
        chunk_file = os.path.join(CHUNKS_DIR, f"{reg}.json")
        with open(chunk_file, "w", encoding="utf-8") as cf:
            json.dump(items, cf, ensure_ascii=False, indent=2)
            cf.write("\n")


def fetch_geosearch(lang, lat, lon, radius, limit):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lon}",
        "gsradius": min(radius, 10000),
        "gslimit": min(limit, 500),
        "format": "json",
    }
    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": "NAVRE-GPT-OSS-Curator/1.1 (https://navre.app)"},
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
            headers={"User-Agent": "NAVRE-GPT-OSS-Curator/1.1 (https://navre.app)"},
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


def ask_groq_curate(items_batch, api_key: str):
    payload = [
        {"idx": i, "title": it["title"], "extract": it["extract"][:180]}
        for i, it in enumerate(items_batch)
    ]

    system_prompt = (
        "You curate physical historical and cultural heritage places for a discovery map app. "
        "Keep genuinely interesting historical or cultural landmarks, monuments, palaces, castles, "
        "museums, temples, mosques, churches, synagogues, monasteries, ruins, archaeological sites, "
        "cisterns, aqueducts, tombs, towers, and historic bridges. "
        "Reject events/battles/attacks/sieges/massacres, hotels/lodges, modern schools, universities, "
        "hospitals, stations, airports, stadiums, malls, parks, neighborhoods, villages, rivers, or mountains. "
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

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY ortam değişkeni tanımlı değil.")

    cache = load_cache()
    places = [] if args.reset_places else load_json_list(JSON_PATH)

    seen_coords = set()
    for p in places:
        if isinstance(p, dict) and isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lon"), (int, float)):
            seen_coords.add((
                str(p.get("name", "")).strip().lower(),
                round(float(p["lat"]), 3),
                round(float(p["lon"]), 3),
            ))

    candidates = []
    seen_cand = set()

    for hub_name, lat, lon, radius, limit, lang, region in WORLD_HUBS:
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
                    "region": region,
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
    print(f"Aday: {len(candidates)} | Önbellekte: {len(candidates) - len(uncached)} | Sorulacak: {len(uncached)}")

    for i in range(0, len(uncached), args.batch_size):
        batch = uncached[i : i + args.batch_size]
        try:
            decisions = ask_groq_curate(batch, api_key=api_key)
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
            print(f"[{min(i + len(batch), len(uncached))}/{len(uncached)}] Paket tamamlandı.")
        except Exception as e:
            print(f"[AI Uyarı] {e} — 5 sn sonra devam...")
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
            "region": c["region"],
            "wikiTitle": c["title"],
        })

    merged = final_places if args.reset_places else (places + final_places)
    save_places(merged)
    print(f"Bitti! Toplam nitelikli kayıt: {len(merged)} | Önbellekteki toplam karar: {len(cache)}")


if __name__ == "__main__":
    main()
