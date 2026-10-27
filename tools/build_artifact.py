# -*- coding: utf-8 -*-
"""클로드 링크(아티팩트)용 한 파일짜리 앱 만들기
index.html + data.json + 유튜브 썸네일(작게 줄여서 안에 넣음) → build/artifact.html
사용법: python tools/build_artifact.py [앱 폴더]"""
import sys, os, re, io, json, base64, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

APP = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(APP, "index.html"), encoding="utf-8").read()
data = json.load(open(os.path.join(APP, "data.json"), encoding="utf-8"))

YT = re.compile(r"(?:youtu\.be/|[?&]v=|shorts/|embed/)([\w-]{11})")
ids = [v["id"] for k in ("videos", "cams", "mvs") for v in data.get(k, []) if v.get("id")]
for b in data.get("blip", []):
    for l in b.get("lk", []):
        m = YT.search(l.get("u", ""))
        if m and "영상" in l.get("l", ""): ids.append(m.group(1))
ids = list(dict.fromkeys(ids))

def thumb(i):
    try:
        req = urllib.request.Request(f"https://i.ytimg.com/vi/{i}/mqdefault.jpg", headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=20).read()
        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((288, 162), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=58, optimize=True, progressive=True)
        return i, "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return i, ""

with ThreadPoolExecutor(12) as ex:
    data["thumbs"] = {i: u for i, u in ex.map(thumb, ids) if u}
print("thumbs", len(data["thumbs"]), "/", len(ids))

head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
head = "\n".join(l for l in head.splitlines()
                 if not re.search(r'charset=|name="viewport"|rel="manifest"|rel="icon"|apple-|mobile-web-app|theme-color', l))
body = body.replace('const MODE = "pwa";', 'const MODE = "artifact";', 1)
body = re.sub(r"let D = null \|\| \{.*?\};", lambda _: "let D = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";", body, count=1)
assert 'MODE = "artifact"' in body and '"thumbs"' in body

os.makedirs(os.path.join(APP, "build"), exist_ok=True)
out = os.path.join(APP, "build", "artifact.html")
open(out, "w", encoding="utf-8").write(head.strip() + "\n" + body.strip() + "\n")
print("saved", out, round(os.path.getsize(out) / 1024), "KB")
