# -*- coding: utf-8 -*-
"""띵동! 보넥도 자동 수집기
블립 일정 + 공식 유튜브 + 뮤비 + 멤버별 직캠 + 구글 뉴스 + 생일카페 → data.json
사용법: python collect.py [출력경로]   (파이썬 기본 기능만 사용)"""
import re, sys, json, urllib.request, urllib.parse, datetime as dt, email.utils as eu, xml.etree.ElementTree as ET

OUT = sys.argv[1] if len(sys.argv) > 1 else "data.json"
K = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(K)
MEMS = ["성호", "리우", "명재현", "태산", "이한", "운학"]
MEM_EN = {"성호": "SUNGHO", "리우": "RIWOO", "명재현": "JAEHYUN", "태산": "TAESAN", "이한": "LEEHAN", "운학": "WOONHAK"}

def get(url, tries=2):
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            pass
    return ""

def mems_in(text):
    t = text.upper()
    return [m for m in MEMS if m in text or MEM_EN[m] in t]

# ---------- 블립 일정 ----------
def blip_month(y, m):
    h = get(f"https://blip.kr/artists/BOYNEXTDOOR/schedule?year={y}&month={m}")
    ch = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', h, re.S)
    d = ""
    for c in ch:
        try: d += json.loads('"' + c + '"')
        except Exception: pass
    dec = json.JSONDecoder(); out = {}
    for mm in re.finditer(r'\{"scheduleId":', d):
        try:
            o, _ = dec.raw_decode(d, mm.start()); out[o["scheduleId"]] = o
        except Exception:
            pass
    return out

def label_for(url, line):
    who = next((n for n in MEMS if n in line.split("http")[0]), "")
    if "youtu" in url: kind = "영상"
    elif "weverse" in url: kind = "위버스 공지"
    elif "x.com" in url or "twitter.com" in url: kind = "X"
    else: kind = "홈페이지"
    return (who + " " + kind).strip() if who else kind

def blip():
    allv = {}
    for i in range(-1, 5):
        mm = NOW.month + i; yy = NOW.year + (mm - 1) // 12; mm = (mm - 1) % 12 + 1
        allv.update(blip_month(yy, mm))
    rows = []
    for o in sorted(allv.values(), key=lambda o: o["startTime"]):
        s = dt.datetime.fromisoformat(o["startTime"].replace("Z", "+00:00")).astimezone(K)
        e = dt.datetime.fromisoformat(o["endTime"].replace("Z", "+00:00")).astimezone(K) if o.get("endTime") else s
        msg = o.get("message") or ""
        links, seen = [], set()
        for line in msg.split("\n"):
            for u in re.findall(r"https?://[^\s)]+", line):
                if u in seen: continue
                seen.add(u); lab = label_for(u, line)
                if any(x["l"] == lab for x in links): continue
                links.append({"l": lab, "u": u})
        note = ""
        for line in msg.split("\n"):
            t = line.strip()
            if not t or t.startswith("*") or "http" in t or t.startswith("🔗") or t.startswith("※"): continue
            note = t[:90]; break
        rows.append({"s": s.strftime("%Y-%m-%d"), "e": max(e, s).strftime("%Y-%m-%d"),
                     "tm": "" if o["isAllday"] else s.strftime("%H:%M"), "ty": o["typeId"],
                     "t": o["title"].strip(), "w": ((o.get("extField") or {}).get("value") or "").strip(),
                     "m": [x["name"] for x in o.get("members", [])], "n": note, "lk": links[:6]})
    return rows

# ---------- 유튜브 ----------
def clean_title(t):
    t = re.sub(r"\s*#\S+", "", t)
    t = re.sub("[\U00013000-\U0001343F\u0591-\u05C7\u066D\u0336]", "", t)
    return re.sub(r"\s{2,}", " ", t).strip()

def rel2iso(txt):
    m = re.search(r"(\d+)\s*(초|분|시간|일|주|개월|년)", txt or "")
    if not m: return ""
    n = int(m.group(1)); u = m.group(2)
    sec = {"초": 1, "분": 60, "시간": 3600, "일": 86400, "주": 604800, "개월": 2592000, "년": 31536000}[u] * n
    return (NOW - dt.timedelta(seconds=sec)).isoformat(timespec="minutes")

def yt_page_items(url):
    h = get(url)
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", h, re.S)
    out = []
    if not m: return out
    def walk(o):
        if isinstance(o, dict):
            if "lockupViewModel" in o:
                v = o["lockupViewModel"]
                try:
                    md = v["metadata"]["lockupMetadataViewModel"]
                    title = md["title"]["content"]; ago = ""
                    for row in md.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", []):
                        for part in row.get("metadataParts", []):
                            t = part.get("text", {}).get("content", "")
                            if "전" in t: ago = t
                    if v.get("contentId"): out.append({"id": v["contentId"], "t": title, "ago": ago})
                except Exception:
                    pass
            if "shortsLockupViewModel" in o:
                v = o["shortsLockupViewModel"]
                vid = v.get("onTap", {}).get("innertubeCommand", {}).get("reelWatchEndpoint", {}).get("videoId")
                t = v.get("overlayMetadata", {}).get("primaryText", {}).get("content", "")
                if vid: out.append({"id": vid, "t": t, "ago": "", "short": True})
            if "videoRenderer" in o:
                v = o["videoRenderer"]
                out.append({"id": v["videoId"], "t": "".join(r.get("text", "") for r in v.get("title", {}).get("runs", [])),
                            "ago": (v.get("publishedTimeText") or {}).get("simpleText", "")})
            for val in o.values(): walk(val)
        elif isinstance(o, list):
            for val in o: walk(val)
    try: walk(json.loads(m.group(1)))
    except Exception: return []
    return out

def official_rss():
    x = get("https://www.youtube.com/feeds/videos.xml?channel_id=UChhKBlh_wvspTh5n4mL0b5g", tries=1)
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    out, seen = [], set()
    try:
        r = ET.fromstring(x)
        for e in r.findall("a:entry", ns):
            title = e.find("a:title", ns).text or ""
            pub = dt.datetime.fromisoformat(e.find("a:published", ns).text).astimezone(K)
            vid = e.find("yt:videoId", ns).text; seen.add(vid)
            out.append({"id": vid, "t": clean_title(title) or title, "ch": "BOYNEXTDOOR",
                        "p": pub.isoformat(timespec="minutes"), "k": "official", "m": mems_in(title), "short": "#" in title})
    except Exception:
        pass
    vids = yt_page_items("https://www.youtube.com/@BOYNEXTDOOR_official/videos")
    shorts = yt_page_items("https://www.youtube.com/@BOYNEXTDOOR_official/shorts")
    for v in vids[:30]:
        if v["id"] in seen: continue
        seen.add(v["id"])
        out.append({"id": v["id"], "t": clean_title(v["t"]) or v["t"], "ch": "BOYNEXTDOOR", "p": rel2iso(v["ago"]), "k": "official", "m": mems_in(v["t"]), "short": False})
    for i, v in enumerate(shorts[:24]):
        if v["id"] in seen: continue
        seen.add(v["id"])
        out.append({"id": v["id"], "t": clean_title(v["t"]) or v["t"], "ch": "BOYNEXTDOOR", "p": "", "k": "official", "m": mems_in(v["t"]), "short": True, "rank": i})
    return out

OK_CH = ["BOYNEXTDOOR", "HYBE", "Mnet", "M2", "MBC", "KBS", "SBS", "STUDIO CHOOM", "스튜디오 춤", "dingo", "딩고",
         "Arirang", "JTBC", "1theK", "원더케이", "GENIE", "Melon", "멜론", "it's Live", "THE SHOW", "Show Champion"]
def yt_search(q, by_date=True, n=15):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + ("&sp=CAI%253D" if by_date else "")
    h = get(url)
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", h, re.S)
    out = []
    if not m: return out
    def walk(o):
        if len(out) >= 40: return
        if isinstance(o, dict):
            if "videoRenderer" in o:
                v = o["videoRenderer"]
                out.append({"id": v["videoId"], "t": "".join(r.get("text", "") for r in v.get("title", {}).get("runs", [])),
                            "ch": "".join(r.get("text", "") for r in v.get("ownerText", {}).get("runs", [])),
                            "ago": (v.get("publishedTimeText") or {}).get("simpleText", "")})
            for val in o.values(): walk(val)
        elif isinstance(o, list):
            for val in o: walk(val)
    try: walk(json.loads(m.group(1)))
    except Exception: return []
    return [v for v in out if any(c.lower() in v["ch"].lower() for c in OK_CH)][:n]

def fancams():
    out = []
    for m in MEMS:
        for v in yt_search(f"보이넥스트도어 {m} 직캠", True, 8):
            if m in v["t"] or MEM_EN[m] in v["t"].upper():
                out.append({"id": v["id"], "t": v["t"], "ch": v["ch"], "p": rel2iso(v["ago"]), "k": "fancam", "m": [m]})
    for v in yt_search("보이넥스트도어 무대", True, 12):
        if "보이넥스트도어" in v["t"] or "BOYNEXTDOOR" in v["t"].upper():
            out.append({"id": v["id"], "t": v["t"], "ch": v["ch"], "p": rel2iso(v["ago"]), "k": "stage", "m": mems_in(v["t"])})
    return out

def mvs():
    try:
        base = json.load(open(__file__.rsplit("/", 1)[0] + "/mvs.json" if "/" in __file__ else "mvs.json", encoding="utf-8"))
    except Exception:
        base = []
    have = {x["id"] for x in base}
    for v in yt_search("보이넥스트도어 Official MV", True, 10):
        tl = v["t"].lower()
        if "hybe" in v["ch"].lower() and "official mv" in tl and "teaser" not in tl and v["id"] not in have:
            mt = re.search(r"'([^']+)'", v["t"])
            base.insert(0, {"song": mt.group(1) if mt else v["t"], "d": "NEW", "id": v["id"], "title": v["t"]}); have.add(v["id"])
    return base

# ---------- 구글 뉴스 ----------
OK_SRC = {"TopStarNews", "Chosunbiz", "OSEN", "MBC", "KBS", "SBS", "JTBC", "Soompi", "Kstyle", "MHN", "TV Report"}
def news():
    out, seen = [], set()
    for q in ["보이넥스트도어 when:7d", "보넥도 when:7d"] + [f"보이넥스트도어 {m} when:7d" for m in MEMS]:
        x = get("https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=ko&gl=KR&ceid=KR:ko")
        try: r = ET.fromstring(x)
        except Exception: continue
        for it in r.findall(".//item"):
            src = (it.find("source").text or "").strip() if it.find("source") is not None else ""
            title = it.find("title").text or ""
            if src and title.endswith(" - " + src): title = title[: -len(src) - 3]
            title = re.sub(r"\s+-\s+[^-]{1,30}$", "", title).strip()
            if not re.search(r"보이넥스트도어|보넥도|BOYNEXTDOOR", title, re.I): continue
            if src.lower() == "youtube": continue
            if not re.search(r"[가-힣]", src) and src not in OK_SRC: continue
            key = re.sub(r"[^가-힣A-Za-z0-9]", "", title)[:28]
            if key in seen: continue
            seen.add(key)
            d = eu.parsedate_to_datetime(it.find("pubDate").text).astimezone(K)
            out.append({"t": title, "src": src, "u": it.find("link").text, "p": d.isoformat(timespec="minutes"), "m": mems_in(title)})
    out.sort(key=lambda n: n["p"], reverse=True)
    return out[:60]

# ---------- 생일카페 ----------
def cafes():
    ids = {43: "성호", 44: "리우", 45: "명재현", 46: "태산", 47: "이한", 48: "운학", 549: "단체"}
    allc = []
    for pg in range(1, 10):
        try:
            j = json.loads(get(f"https://api.offmate.kr/birthday-cafe?location=&page={pg}&limit=50"))
            b = j["data"]["birthdayCafes"]
        except Exception:
            break
        allc += b
        if len(b) < 50: break
    today = NOW.strftime("%Y-%m-%d"); merged = {}
    for c in allc:
        if c["artist"]["id"] not in ids: continue
        s, e = [x.strip().replace(".", "-") for x in c["eventDuration"].split("~")]
        if e < today: continue
        key = (c["name"].strip(), c["cafeAddressName"].strip(), s, e)
        m = merged.setdefault(key, {"t": c["name"].strip(), "c": c["cafeAddressName"].strip(), "a": c["cafeAddress"].strip(),
             "s": s, "e": e, "lat": round(c["cafeAddressLat"], 6), "lng": round(c["cafeAddressLng"], 6),
             "x": (c["twitterId"] or "").lstrip("@") if c["snsType"] == "twitter" else "",
             "ig": (c["instagramId"] or "").lstrip("@") if c["snsType"] == "instagram" else "", "m": []})
        n = ids[c["artist"]["id"]]
        if n not in m["m"]: m["m"].append(n)
    order = MEMS + ["단체"]
    out = sorted(merged.values(), key=lambda r: (r["s"], r["e"], r["t"]))
    for r in out: r["m"].sort(key=order.index)
    return out

# ---------- 실행 (실패한 항목은 이전 값 유지) ----------
try:
    old = json.load(open(OUT, encoding="utf-8"))
except Exception:
    old = {}
data = {"at": NOW.isoformat(timespec="minutes")}
for name, fn in [("blip", blip), ("videos", official_rss), ("cams", fancams), ("mvs", mvs), ("news", news), ("cafes", cafes)]:
    try:
        v = fn()
    except Exception as ex:
        print("FAIL", name, ex); v = []
    if not v and old.get(name):
        v = old[name]; print("keep old", name)
    data[name] = v; print(name, len(v))
json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("saved", OUT)
