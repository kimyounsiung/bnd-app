# -*- coding: utf-8 -*-
"""앱 아이콘 만들기: 파란 밤하늘 위 아치형 문 + 노란 손잡이 (PIL 필요)
사용법: python tools/make_icons.py [앱 폴더]"""
import sys, os
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024

def icon():
    im = Image.new("RGB", (S, S))
    px = im.load()
    top, bot = (76, 104, 255), (22, 30, 120)
    for y in range(S):
        t = y / (S - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(S):
            px[x, y] = c
    d = ImageDraw.Draw(im, "RGBA")
    # 은은한 빛
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((180, 60, 844, 620), fill=(160, 180, 255, 120))
    im.paste(glow.filter(ImageFilter.GaussianBlur(120)), (0, 0), glow.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(im, "RGBA")
    # 문 (안전 영역 안쪽 약 62%)
    L, R, T, B = 322, 702, 250, 800
    r = (R - L) // 2
    d.ellipse((L, T, R, T + 2 * r), fill=(255, 255, 255, 255))
    d.rectangle((L, T + r, R, B), fill=(255, 255, 255, 255))
    # 문 안쪽 패널 선
    i = 34
    d.arc((L + i, T + i, R - i, T + 2 * r - i), 180, 360, fill=(47, 75, 255, 60), width=10)
    d.line((L + i, T + r, L + i, B - 2), fill=(47, 75, 255, 60), width=10)
    d.line((R - i, T + r, R - i, B - 2), fill=(47, 75, 255, 60), width=10)
    # 바닥 그림자 · 손잡이
    d.rectangle((L - 40, B, R + 40, B + 14), fill=(255, 255, 255, 90))
    d.ellipse((598, 540, 650, 592), fill=(255, 200, 61, 255))
    return im

base = icon()
for name, size in [("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180)]:
    base.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, name), optimize=True)
    print("saved", name)
