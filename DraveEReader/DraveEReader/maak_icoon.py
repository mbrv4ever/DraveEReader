# -*- coding: utf-8 -*-
"""
maak_icoon.py - DraveEReader

Maakt uit assets/logo.png:
  - assets/logo.ico   (multi-resolutie icoon voor de .exe en het venster;
                       donkere afgeronde tegel met zilveren draak, goed leesbaar
                       op zowel een donkere taakbalk als een witte Verkenner)
  - assets/app.ico    (zelfde icoon; naam zoals in de huisstijl-bundel)
  - assets/logo_t.png (zilveren draak op transparant, voor weergave in de app)

Vereist alleen Pillow.
"""
import os, sys
try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow ontbreekt. Installeer met: pip install pillow"); sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SRC = os.path.join(ASSETS, "logo.png")
TEGEL = (22, 22, 27, 255)      # PANEL #16161b
ZILVER = (212, 212, 212)       # TEXT/zilver
RAND = (111, 163, 214, 255)    # ACCENT staalblauw


def lijnwerk_naar_alpha(im, drempel=232):
    g = im.convert("L"); w, h = g.size
    alpha = Image.new("L", (w, h), 0); ap = alpha.load(); gp = g.load()
    for y in range(h):
        for x in range(w):
            v = gp[x, y]
            if v < drempel:
                ap[x, y] = min(255, int((drempel - v) * 255 / drempel) + 40)
    return alpha


def main():
    if not os.path.exists(SRC):
        print("assets/logo.png niet gevonden."); sys.exit(1)
    im = Image.open(SRC)
    alpha = lijnwerk_naar_alpha(im)
    bbox = alpha.getbbox()
    if bbox: alpha = alpha.crop(bbox)
    w, h = alpha.size
    draak = Image.new("RGBA", (w, h), ZILVER + (0,)); draak.putalpha(alpha)

    # transparante zilveren versie voor in de app
    zij = int(max(w, h) * 1.12)
    canvas = Image.new("RGBA", (zij, zij), (0, 0, 0, 0))
    canvas.paste(draak, ((zij - w) // 2, (zij - h) // 2), draak)
    canvas.resize((256, 256), Image.LANCZOS).save(os.path.join(ASSETS, "logo_t.png"))
    print("Geschreven: assets/logo_t.png")

    # icoon: donkere afgeronde tegel + accent-rand + zilveren draak
    basis = 256
    tile = Image.new("RGBA", (basis, basis), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile); r = int(basis * 0.22)
    d.rounded_rectangle([0, 0, basis - 1, basis - 1], radius=r, fill=TEGEL)
    d.rounded_rectangle([2, 2, basis - 3, basis - 3], radius=r, outline=RAND, width=4)
    if w >= h:
        nw, nh = int(basis * 0.74), int(basis * 0.74 * h / w)
    else:
        nw, nh = int(basis * 0.74 * w / h), int(basis * 0.74)
    dd = draak.resize((nw, nh), Image.LANCZOS)
    tile.paste(dd, ((basis - nw) // 2, (basis - nh) // 2), dd)
    maten = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    for naam in ("logo.ico", "app.ico"):
        tile.save(os.path.join(ASSETS, naam), format="ICO", sizes=maten)
        print("Geschreven: assets/" + naam)


if __name__ == "__main__":
    main()
