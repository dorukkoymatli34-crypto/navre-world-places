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
    r"havalimanı|stadyumu|stadyum|oteli|hotel|lodge|resort|hostel|avm|alışveriş merkezi|shopping mall|"
    r"istasyon|metro|marmaray|metrobüs|tramvay|durak|gar|terminal|iskele|otogar|"
    r"parkı|parki|park|otopark|korusu|koru|high school|school|university|hospital|airport|stadium|"
    r"siege of|massacre|attack|battle of|bombing|earthquake|election|treaty of|assassination)\b",
    re.IGNORECASE,
)

# KATMAN 1: Dünyanın ve Türkiye'nin en ikonik tarihi merkezleri (tek bir ikon bile kaçmasın diye önce taranır)
ICONIC_ANCHORS = [
    # Türkiye - İkonik & Tarihi Odaklar
    ("TR-Istanbul-Sultanahmet-Fatih", 41.0082, 28.9784, 10000, 500, "tr", "middle-east-anatolia"),
    ("TR-Istanbul-Beyoglu-Besiktas-Uskudar", 41.0369, 28.9850, 10000, 400, "tr", "middle-east-anatolia"),
    ("TR-Edirne", 41.6771, 26.5557, 10000, 350, "tr", "middle-east-anatolia"),
    ("TR-Bursa", 40.1885, 29.0610, 10000, 350, "tr", "middle-east-anatolia"),
    ("TR-Iznik", 40.4286, 29.7211, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Canakkale-Truva-Gelibolu", 39.9575, 26.2389, 10000, 300, "tr", "middle-east-anatolia"),
    ("TR-Assos-Behramkale", 39.4906, 26.3367, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Bergama-Pergamon", 39.1325, 27.1842, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Selcuk-Efes", 37.9497, 27.3686, 10000, 350, "tr", "middle-east-anatolia"),
    ("TR-Pamukkale-Hierapolis", 37.9250, 29.1264, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Afrodisias", 37.7089, 28.7236, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Bodrum-Halikarnas", 37.0344, 27.4305, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Fethiye-Xanthos-Patara", 36.3561, 29.3186, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Myra-Demre", 36.2592, 29.9853, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Antalya-Kaleici-Perge", 36.8841, 30.7056, 10000, 300, "tr", "middle-east-anatolia"),
    ("TR-Aspendos-Side", 36.7667, 31.3889, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Konya", 37.8714, 32.4846, 10000, 350, "tr", "middle-east-anatolia"),
    ("TR-Catalhoyuk", 37.6675, 32.8283, 10000, 150, "tr", "middle-east-anatolia"),
    ("TR-Goreme-Kapadokya", 38.6431, 34.8289, 10000, 400, "tr", "middle-east-anatolia"),
    ("TR-Hattusas-Bogazkale", 40.0194, 34.6156, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Safranbolu", 41.2508, 32.6942, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Amasya", 40.6499, 35.8353, 10000, 250, "tr", "middle-east-anatolia"),
    ("TR-Divrigi", 39.3711, 38.1172, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Nemrut", 37.9806, 38.7408, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Gobeklitepe-Sanliurfa", 37.2231, 38.9225, 10000, 300, "tr", "middle-east-anatolia"),
    ("TR-Harran", 36.8650, 39.0314, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Mardin-Dara", 37.3131, 40.7350, 10000, 300, "tr", "middle-east-anatolia"),
    ("TR-Midyat-MorGabriel", 37.4167, 41.3667, 10000, 220, "tr", "middle-east-anatolia"),
    ("TR-Hasankeyf", 37.7122, 41.4125, 10000, 200, "tr", "middle-east-anatolia"),
    ("TR-Diyarbakir-Surlar", 37.9144, 40.2306, 10000, 300, "tr", "middle-east-anatolia"),
    ("TR-Ani-Kars", 40.5067, 43.5722, 10000, 220, "tr", "middle-east-anatolia"),
    ("TR-IshakPasa-Dogubayazit", 39.5206, 44.1292, 10000, 180, "tr", "middle-east-anatolia"),
    ("TR-Van-Akdamar", 38.3408, 43.0369, 10000, 220, "tr", "middle-east-anatolia"),
    ("TR-Sumela-Macka", 40.6903, 39.6583, 10000, 200, "tr", "middle-east-anatolia"),

    # Dünya İkonları - Avrupa
    ("IT-Rome-Historic", 41.8902, 12.4922, 10000, 500, "en", "europe"),
    ("IT-Vatican", 41.9022, 12.4539, 10000, 350, "en", "europe"),
    ("IT-Florence", 43.7696, 11.2558, 10000, 450, "en", "europe"),
    ("IT-Venice", 45.4340, 12.3388, 10000, 450, "en", "europe"),
    ("IT-Pompeii-Herculaneum", 40.7509, 14.4869, 10000, 350, "en", "europe"),
    ("IT-Naples", 40.8518, 14.2681, 10000, 350, "en", "europe"),
    ("IT-Milan", 45.4642, 9.1900, 10000, 350, "en", "europe"),
    ("IT-Pisa", 43.7228, 10.4017, 10000, 250, "en", "europe"),
    ("IT-Siena", 43.3188, 11.3308, 10000, 280, "en", "europe"),
    ("IT-Agrigento-ValleyOfTemples", 37.2906, 13.5856, 10000, 220, "en", "europe"),
    ("GR-Athens-Acropolis", 37.9715, 23.7257, 10000, 500, "en", "europe"),
    ("GR-Delphi", 38.4824, 22.5010, 10000, 220, "en", "europe"),
    ("GR-Olympia", 37.6383, 21.6300, 10000, 200, "en", "europe"),
    ("GR-Mycenae-Epidaurus", 37.7308, 22.7561, 10000, 220, "en", "europe"),
    ("GR-Meteora", 39.7217, 21.6306, 10000, 220, "en", "europe"),
    ("GR-Knossos", 35.2979, 25.1632, 10000, 250, "en", "europe"),
    ("FR-Paris-Center", 48.8566, 2.3522, 10000, 500, "en", "europe"),
    ("FR-Versailles", 48.8049, 2.1204, 10000, 250, "en", "europe"),
    ("FR-MontSaintMichel", 48.6361, -1.5115, 10000, 200, "en", "europe"),
    ("FR-Carcassonne", 43.2066, 2.3639, 10000, 220, "en", "europe"),
    ("FR-Loire-Chambord", 47.6161, 1.5170, 10000, 220, "en", "europe"),
    ("ES-Madrid", 40.4168, -3.7038, 10000, 450, "en", "europe"),
    ("ES-Barcelona", 41.3874, 2.1686, 10000, 450, "en", "europe"),
    ("ES-Granada-Alhambra", 37.1773, -3.5986, 10000, 400, "en", "europe"),
    ("ES-Cordoba", 37.8882, -4.7794, 10000, 350, "en", "europe"),
    ("ES-Seville", 37.3891, -5.9845, 10000, 380, "en", "europe"),
    ("ES-Toledo", 39.8628, -4.0273, 10000, 320, "en", "europe"),
    ("ES-Segovia", 40.9429, -4.1088, 10000, 250, "en", "europe"),
    ("PT-Lisbon-Belem", 38.6979, -9.2064, 10000, 350, "en", "europe"),
    ("PT-Sintra", 38.7875, -9.3906, 10000, 250, "en", "europe"),
    ("UK-London", 51.5072, -0.1276, 10000, 500, "en", "europe"),
    ("UK-Stonehenge-Salisbury", 51.1789, -1.8262, 10000, 220, "en", "europe"),
    ("UK-Edinburgh", 55.9486, -3.1999, 10000, 350, "en", "europe"),
    ("UK-Oxford", 51.7520, -1.2577, 10000, 300, "en", "europe"),
    ("DE-Berlin", 52.5200, 13.4050, 10000, 400, "en", "europe"),
    ("DE-Neuschwanstein-Fussen", 47.5576, 10.7498, 10000, 200, "en", "europe"),
    ("DE-Cologne", 50.9413, 6.9583, 10000, 280, "en", "europe"),
    ("AT-Vienna", 48.2082, 16.3738, 10000, 450, "en", "europe"),
    ("CZ-Prague", 50.0909, 14.4005, 10000, 450, "en", "europe"),
    ("HU-Budapest", 47.4979, 19.0402, 10000, 380, "en", "europe"),
    ("PL-Krakow", 50.0647, 19.9450, 10000, 350, "en", "europe"),
    ("HR-Dubrovnik", 42.6412, 18.1083, 10000, 300, "en", "europe"),
    ("RO-Bran-Brasov", 45.5149, 25.3672, 10000, 250, "en", "europe"),
    ("GE-Tbilisi-Mtskheta", 41.7151, 44.8271, 10000, 320, "en", "europe"),
    ("AM-Geghard-Garni", 40.1406, 44.7986, 10000, 240, "en", "europe"),

    # Dünya İkonları - Orta Doğu, Afrika, Asya, Amerika
    ("EG-Giza-Pyramids", 29.9792, 31.1342, 10000, 450, "en", "middle-east-anatolia"),
    ("EG-Cairo-Islamic-Coptic", 30.0444, 31.2357, 10000, 500, "en", "middle-east-anatolia"),
    ("EG-Luxor-Karnak-ValleyOfKings", 25.7188, 32.6573, 10000, 450, "en", "middle-east-anatolia"),
    ("EG-AbuSimbel", 22.3372, 31.6258, 10000, 180, "en", "middle-east-anatolia"),
    ("JO-Petra", 30.3285, 35.4444, 10000, 350, "en", "middle-east-anatolia"),
    ("JO-Jerash", 32.2746, 35.8961, 10000, 250, "en", "middle-east-anatolia"),
    ("LB-Baalbek", 34.0069, 36.2039, 10000, 220, "en", "middle-east-anatolia"),
    ("IR-Persepolis", 29.9352, 52.8916, 10000, 300, "en", "middle-east-anatolia"),
    ("IR-Isfahan", 32.6575, 51.6775, 10000, 350, "en", "middle-east-anatolia"),
    ("UZ-Samarkand", 39.6542, 66.9597, 10000, 350, "en", "asia"),
    ("UZ-Bukhara", 39.7747, 64.4286, 10000, 320, "en", "asia"),
    ("MA-Marrakesh", 31.6295, -7.9811, 10000, 350, "en", "africa"),
    ("MA-Fes", 34.0617, -4.9778, 10000, 350, "en", "africa"),
    ("ET-Lalibela", 12.0319, 39.0475, 10000, 240, "en", "africa"),
    ("TN-Carthage", 36.8531, 10.3233, 10000, 280, "en", "africa"),
    ("IN-Agra-TajMahal", 27.1751, 78.0421, 10000, 380, "en", "asia"),
    ("IN-Delhi", 28.6139, 77.2090, 10000, 420, "en", "asia"),
    ("IN-Jaipur", 26.9124, 75.7873, 10000, 350, "en", "asia"),
    ("IN-Hampi", 15.3350, 76.4600, 10000, 320, "en", "asia"),
    ("IN-Ellora-Ajanta", 20.0268, 75.1771, 10000, 220, "en", "asia"),
    ("KH-AngkorWat", 13.4125, 103.8670, 10000, 420, "en", "asia"),
    ("ID-Borobudur-Prambanan", -7.6079, 110.2038, 10000, 260, "en", "asia"),
    ("MM-Bagan", 21.1717, 94.8585, 10000, 280, "en", "asia"),
    ("TH-Ayutthaya", 14.3692, 100.5877, 10000, 300, "en", "asia"),
    ("CN-Beijing-ForbiddenCity", 39.9163, 116.3972, 10000, 500, "en", "asia"),
    ("CN-GreatWall-Badaling", 40.3598, 116.0200, 10000, 220, "en", "asia"),
    ("CN-Xian-Terracotta", 34.3841, 109.2785, 10000, 350, "en", "asia"),
    ("JP-Kyoto", 35.0116, 135.7681, 10000, 500, "en", "asia"),
    ("JP-Nara", 34.6851, 135.8048, 10000, 380, "en", "asia"),
    ("JP-Himeji", 34.8394, 134.6939, 10000, 240, "en", "asia"),
    ("KR-Gyeongju", 35.8562, 129.2247, 10000, 300, "en", "asia"),
    ("PE-MachuPicchu", -13.1631, -72.5450, 10000, 300, "en", "americas"),
    ("PE-Cusco", -13.5319, -71.9675, 10000, 380, "en", "americas"),
    ("MX-Teotihuacan", 19.6925, -98.8438, 10000, 280, "en", "americas"),
    ("MX-ChichenItza", 20.6843, -88.5678, 10000, 220, "en", "americas"),
    ("MX-MexicoCity", 19.4326, -99.1332, 10000, 450, "en", "americas"),
    ("GT-Tikal", 17.2220, -89.6237, 10000, 260, "en", "americas"),
    ("CL-EasterIsland", -27.1127, -109.3497, 10000, 200, "en", "americas"),
]

# KATMAN 2: Ücra ve keşfedilmemiş bölgeler dahil tüm dünyayı tarayan enlem-boylam grid'i
GLOBAL_GRID_BANDS = [
    # Türkiye ve çevresi (sık tarama)
    ("middle-east-anatolia", "tr", 35.8, 42.2, 0.55, 25.8, 44.8, 0.65, 10000, 250),
    # Avrupa
    ("europe", "en", 35.0, 63.0, 1.25, -10.0, 45.0, 1.45, 10000, 220),
    # Orta Doğu & Kuzey Afrika
    ("middle-east-anatolia", "en", 20.0, 38.0, 1.4, -13.0, 62.0, 1.6, 10000, 200),
    # Sahra altı Afrika
    ("africa", "en", -35.0, 20.0, 2.2, -18.0, 51.0, 2.2, 10000, 160),
    # Asya
    ("asia", "en", -10.0, 54.0, 1.8, 50.0, 146.0, 2.0, 10000, 200),
    # Amerika
    ("americas", "en", -54.0, 50.0, 2.0, -125.0, -34.0, 2.2, 10000, 180),
]


def classify_region(lat: float, lon: float, default_region: str) -> str:
    if 35.5 <= lat <= 42.5 and 25.5 <= lon <= 45.0:
        return "middle-east-anatolia"
    if 34.5 <= lat <= 71.0 and -25.0 <= lon <= 45.0:
        return "europe"
    if 18.0 <= lat <= 37.5 and -17.0 <= lon <= 62.0:
        return "middle-east-anatolia"
    if -36.0 <= lat < 18.0 and -18.0 <= lon <= 52.0:
        return "africa"
    if -12.0 <= lat <= 70.0 and 45.0 < lon <= 180.0:
        return "asia"
    if -56.0 <= lat <= 72.0 and -170.0 <= lon <= -30.0:
        return "americas"
    return default_region


def build_all_hubs():
    hubs = list(ICONIC_ANCHORS)
    idx = 0
    for region, lang, lat_min, lat_max, lat_step, lon_min, lon_max, lon_step, radius_m, limit in GLOBAL_GRID_BANDS:
        lat = lat_min
        while lat <= lat_max + 1e-9:
            lon = lon_min
            while lon <= lon_max + 1e-9:
                idx += 1
                hubs.append((
                    f"G{idx}-{lang}-{round(lat,2)}-{round(lon,2)}",
                    round(lat, 4),
                    round(lon, 4),
                    radius_m,
                    limit,
                    lang,
                    classify_region(lat, lon, region),
                ))
                lon += lon_step
            lat += lat_step
    return hubs


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
    seen_ids = set()
    for p in places:
        if not isinstance(p, dict):
            continue
        lat = p.get("lat")
        lon = p.get("lon")
        name = (p.get("name") or "").strip()
        if not name or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        if HARD_BLOCK_REGEX.search(name):
            continue
        pid = str(p.get("id") or "")
        if pid and pid in seen_ids:
            continue
        if pid:
            seen_ids.add(pid)
        item = dict(p)
        item["lat"] = round(float(lat), 6)
        item["lon"] = round(float(lon), 6)
        item["region"] = classify_region(item["lat"], item["lon"], item.get("region") or "global")
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

    return cleaned


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
        headers={"User-Agent": "NAVRE-GPT-OSS-Curator/2.0 (https://navre.app)"},
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
            "exchars": 260,
            "titles": "|".join(chunk),
            "format": "json",
        }
        resp = requests.get(
            url,
            params=params,
            headers={"User-Agent": "NAVRE-GPT-OSS-Curator/2.0 (https://navre.app)"},
            timeout=20,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for p in pages.values():
            t = (p.get("title") or "").strip().lower()
            if t:
                out[t] = (p.get("extract") or "").strip()
        time.sleep(0.12)
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
        {"idx": i, "title": it["title"], "extract": it["extract"][:200]}
        for i, it in enumerate(items_batch)
    ]

    system_prompt = (
        "You are a strict, expert historical & cultural heritage curator for NAVRE, a global discovery map app. "
        "Users browse both world-famous landmarks and remote, lesser-known historical treasures. "
        "Set keep=true ONLY for tangible, physical historical or cultural heritage sites: "
        "ancient ruins, archaeological sites, castles, fortresses, palaces, historic mosques, churches, "
        "synagogues, monasteries, temples, heritage/history/art museums, cisterns, aqueducts, historic tombs, "
        "mausoleums, historic towers, historic bridges, caravanserais, madrasas, and significant monuments. "
        "Set keep=false for historical events/battles/attacks/sieges/massacres/treaties, hotels/lodges/resorts, "
        "modern schools, universities, hospitals, transit stations, airports, stadiums, shopping malls, "
        "ordinary city parks, administrative districts, neighborhoods, villages, cities, rivers, lakes, or mountains. "
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


def rebuild_and_save(places, candidates, cache, reset_places=False):
    seen_coords = set()
    base = [] if reset_places else list(places)
    for p in base:
        if isinstance(p, dict) and isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lon"), (int, float)):
            seen_coords.add((
                str(p.get("name", "")).strip().lower(),
                round(float(p["lat"]), 3),
                round(float(p["lon"]), 3),
            ))

    added = []
    for c in candidates:
        decision = cache.get(c["ckey"])
        if not decision or not decision.get("keep"):
            continue
        dkey = (c["title"].lower(), round(c["lat"], 3), round(c["lon"], 3))
        if dkey in seen_coords:
            continue
        seen_coords.add(dkey)
        cat = decision.get("category")
        if cat not in ALLOWED_CATEGORIES:
            cat = "monument"
        added.append({
            "id": f"w-{c['lang']}/{c['pageid'] or len(base) + len(added) + 1}",
            "name": c["title"],
            "category": cat,
            "lat": c["lat"],
            "lon": c["lon"],
            "region": c["region"],
            "wikiTitle": c["title"],
        })

    return save_places(base + added)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--reset-places", action="store_true")
    parser.add_argument("--max-new-per-run", type=int, default=3000)
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY ortam değişkeni tanımlı değil.")

    cache = load_cache()
    places = [] if args.reset_places else load_json_list(JSON_PATH)
    hubs = build_all_hubs()

    candidates = []
    seen_cand = set()

    print(f"Toplam tarama noktası (İkonik + Küresel Grid): {len(hubs)}")
    for idx_h, (hub_name, lat, lon, radius, limit, lang, region) in enumerate(hubs, 1):
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

        if idx_h % 100 == 0:
            print(f"  Hub ilerlemesi: {idx_h}/{len(hubs)} | Biriken benzersiz aday: {len(candidates)}")
        time.sleep(0.1)

    uncached = [c for c in candidates if c["ckey"] not in cache]
    if args.max_new_per_run > 0:
        uncached = uncached[: args.max_new_per_run]

    print(f"Aday: {len(candidates)} | Önbellekte: {len(candidates) - len(uncached)} | Bu turda AI'a sorulacak: {len(uncached)}")

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

            if (i // args.batch_size + 1) % 5 == 0:
                merged_mid = rebuild_and_save(places, candidates, cache, reset_places=args.reset_places)
                print(f"[{min(i + len(batch), len(uncached))}/{len(uncached)}] Ara kayıt yapıldı -> Toplam nitelikli yer: {len(merged_mid)}")
            else:
                print(f"[{min(i + len(batch), len(uncached))}/{len(uncached)}] Paket tamamlandı.")
        except Exception as e:
            print(f"[AI Uyarı] {e} — 5 sn sonra devam...")
            time.sleep(5)
        time.sleep(1.2)

    merged = rebuild_and_save(places, candidates, cache, reset_places=args.reset_places)
    print(f"Bitti! Toplam nitelikli kayıt: {len(merged)} | Önbellekteki toplam karar: {len(cache)}")


if __name__ == "__main__":
    main()
