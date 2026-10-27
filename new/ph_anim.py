"""Живые шапки «Электромопедов» и «Выданных авто» (Юрий 27.10.2026, вариант 1): мопед и прицеп с машиной въезжают в кадр,
колёса крутятся и останавливаются; мопед чуть качается и включает фару, машина на прицепе качается на подвеске.

Из вырезанной картинки new/src/ph_<имя>.png собирается docs/img/ph/<имя>.svg: сама картинка, поверх колёс — их развёртка,
которая вращается внутри эллипса колеса (то, что колесо закрывает — вилка, тормоз, — дорисовано с других углов того же
колеса и закрыто маской), и анимации SMIL. Въезд в кадр — CSS (.phv .drive в s.css), обе части стартуют по загрузке картинки.
Запуск: python3 new/ph_anim.py [--debug] — debug рисует эллипсы и маски в /tmp/yz/ph_<имя>_dbg.png."""
import base64
import io
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

NEW = Path(__file__).resolve().parent
SRC = NEW / "src"
OUT = NEW.parent / "docs" / "img" / "ph"

DUR = 1.6                     # въезд и вращение колёс, с — как .drive в s.css
SPLINE = ".2 .7 .25 1"        # то же замедление, что cubic-bezier въезда

# колесо: центр, полуоси, наклон эллипса (°), обороты за въезд (целые — колесо встаёт как на фото), закрывающие его детали
SCENES = {
    "mopedy": {
        "wheels": [{"c": (468, 796.5), "rx": 96, "ry": 119, "tilt": 13, "turns": 3, "rmax": .57,   # крутится тормозной диск: обод однотонный, а его тень от света крутиться не должна
                    "occ": [[(496, 676), (541, 676), (530, 742), (549, 746), (556, 772), (549, 832), (504, 834), (478, 824),
                             (468, 806), (474, 782), (486, 744)],
                            [(340, 600), (620, 600), (620, 690), (560, 688), (470, 686), (400, 688), (340, 696)]]}],   # вилка с тормозом; крыло
        "sway": {"c": (760, 935), "deg": [0, -1.3, .65, -.25, 0], "begin": DUR - .1, "dur": 1.3},
        "lamp": {"c": (557, 293), "r": 120},
        "shadow": {"c": (750, 940), "rx": 400, "ry": 22},
    },
    "vydannye": {
        "wheels": [{"c": (1031.3, 749.1), "rx": 36, "ry": 90, "tilt": 5.6, "turns": 4, "occ": []},
                   {"c": (1128.8, 709.5), "rx": 28, "ry": 83, "tilt": -2.1, "turns": 4, "occ": []}],
        "body": {"poly": [(235, 140), (1265, 140), (1265, 500), (1240, 545), (1235, 560), (1215, 585), (1170, 588), (1140, 570),
                          (1130, 545), (960, 555), (930, 560), (918, 600), (905, 650), (880, 680), (845, 690), (810, 680),
                          (790, 650), (782, 610), (720, 622), (600, 630), (500, 615), (330, 605), (255, 580), (232, 520)],
                 "c": (1190, 585), "deg": [0, -.7, .35, -.14, 0], "begin": DUR - .15, "dur": 1.2},
        "shadow": {"c": (1080, 832), "rx": 190, "ry": 18},
    },
}


def b64(im, fmt="WEBP", **kw):
    buf = io.BytesIO()
    im.save(buf, fmt, **kw)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def poly_mask(size, polys):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon(p, fill=255)
    return np.array(m) > 0


def wheel(A, w):
    """Развёртка колеса в круг радиуса R и маска его видимой части на картинке."""
    H, W = A.shape[:2]
    cx, cy = w["c"]
    rx, ry, t = w["rx"], w["ry"], math.radians(w["tilt"])
    R = int(round(max(rx, ry)))
    yy, xx = np.mgrid[0:H, 0:W]
    dx, dy = xx - cx, yy - cy
    u = (dx * math.cos(t) + dy * math.sin(t)) / rx           # в осях эллипса
    v = (-dx * math.sin(t) + dy * math.cos(t)) / ry
    rm = w.get("rmax", 1)                                   # крутится только середина колеса (диск)
    inside = u * u + v * v <= rm * rm
    occ = poly_mask((W, H), w["occ"]) if w["occ"] else np.zeros((H, W), bool)
    vis = inside & (A[..., 3] > 200) & ~occ
    # развёртка: пиксель круга (i, j) → точка картинки
    jj, ii = np.meshgrid(np.arange(2 * R) + .5 - R, np.arange(2 * R) + .5 - R)
    uu, vv = jj / R, ii / R
    disk = uu * uu + vv * vv <= rm * rm
    sx = cx + uu * rx * math.cos(t) - vv * ry * math.sin(t)
    sy = cy + uu * rx * math.sin(t) + vv * ry * math.cos(t)
    tex = np.zeros((2 * R, 2 * R, 4), np.float32)
    for k in range(4):
        tex[..., k] = ndimage.map_coordinates(A[..., k].astype(np.float32), [sy - .5, sx - .5], order=1, mode="nearest")
    known = ndimage.map_coordinates(vis.astype(np.float32), [sy - .5, sx - .5], order=0) > .5
    known &= disk
    # закрытое (вилка, тормоз) — тем же колесом, повёрнутым на шаг рисунка диска (20°), сначала с противоположной стороны
    r, ph = np.hypot(uu, vv), np.arctan2(vv, uu)
    todo = disk & ~known
    for k in sorted(range(20, 360, 20), key=lambda a: abs(a - 180)):
        if not todo.any():
            break
        a = ph + math.radians(k)
        si = np.clip(np.round(r * np.sin(a) * R + R - .5).astype(int), 0, 2 * R - 1)
        sj = np.clip(np.round(r * np.cos(a) * R + R - .5).astype(int), 0, 2 * R - 1)
        ok = todo & known[si, sj]
        tex[ok] = tex[si[ok], sj[ok]]
        todo &= ~ok
        known |= ok
    tyre = np.median(tex[disk & known & (r > .9 * rm)][:, :3], axis=0)    # что не нашлось или прозрачно — цветом шины
    bad = disk & (todo | (tex[..., 3] < 200))
    tex[bad, :3] = tyre
    tex[..., 3] = np.where(disk, 255, 0)
    return Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8), "RGBA"), R, vis


def mask_img(m):
    """Маска SVG (белое — видно) по рамке видимой части, края на полпикселя мягче."""
    ys, xs = np.nonzero(m)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    im = Image.fromarray((m[y0:y1, x0:x1] * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(.6))
    return im, x0, y0, x1 - x0, y1 - y0


def build(name, debug=False):
    sc = SCENES[name]
    src = Image.open(SRC / f"ph_{name}.png").convert("RGBA")
    W, H = src.size
    A = np.array(src)
    defs, top = [], []
    spline = f'calcMode="spline" keyTimes="0;1" keySplines="{SPLINE}"'
    if sc.get("shadow"):
        s = sc["shadow"]
        defs.append('<filter id="sh" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="12"/></filter>')
        top.append(f'<ellipse cx="{s["c"][0]}" cy="{s["c"][1]}" rx="{s["rx"]}" ry="{s["ry"]}" fill="#000" opacity=".42" filter="url(#sh)"/>')
    top.append(f'<image href="{b64(src, quality=82, method=6)}" width="{W}" height="{H}"/>')
    if sc.get("body"):                                             # машина на прицепе — отдельным слоем, качается на подвеске
        b = sc["body"]
        m = poly_mask((W, H), [b["poly"]]) & (A[..., 3] > 0)
        ys, xs = np.nonzero(m)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        lay = src.crop((x0, y0, x1, y1))
        al = np.array(lay)
        al[..., 3] = np.where(m[y0:y1, x0:x1], al[..., 3], 0)
        lay = Image.fromarray(al, "RGBA")
        vals = ";".join(f'{d} {b["c"][0]} {b["c"][1]}' for d in b["deg"])
        kt = ";".join(f"{i / (len(b['deg']) - 1):.3f}" for i in range(len(b["deg"])))
        top.append(f'<g><animateTransform attributeName="transform" type="rotate" values="{vals}" keyTimes="{kt}" begin="{b["begin"]}s" dur="{b["dur"]}s" fill="freeze"/>'
                   f'<image href="{b64(lay, quality=84, method=6)}" x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}"/></g>')
    dbg = src.copy() if debug else None
    for n, w in enumerate(sc["wheels"]):
        tex, R, vis = wheel(A, w)
        mi, mx, my, mw, mh = mask_img(vis)
        deg = -360 * w["turns"]                                    # едут влево — колёса против часовой
        defs.append(f'<mask id="m{n}" maskUnits="userSpaceOnUse" x="{mx}" y="{my}" width="{mw}" height="{mh}">'
                    f'<image href="{b64(mi, "PNG", optimize=True)}" x="{mx}" y="{my}" width="{mw}" height="{mh}"/></mask>')
        top.append(f'<g mask="url(#m{n})"><animate attributeName="opacity" values="1;0" begin="{DUR}s" dur=".3s" fill="freeze"/>'
                   f'<g transform="translate({w["c"][0]} {w["c"][1]}) rotate({w["tilt"]}) scale({w["rx"] / R:.4f} {w["ry"] / R:.4f})"><g>'
                   f'<animateTransform attributeName="transform" type="rotate" values="0;{deg}" {spline} dur="{DUR}s" fill="freeze"/>'
                   f'<image href="{b64(tex, quality=86, method=6)}" x="{-R}" y="{-R}" width="{2 * R}" height="{2 * R}"/></g></g></g>')
        if debug:
            ov = Image.new("RGBA", src.size, (0, 0, 0, 0))
            ov.putalpha(Image.fromarray((vis * 110).astype(np.uint8)))
            ov = Image.composite(Image.new("RGBA", src.size, (255, 0, 0, 255)), ov, Image.fromarray((vis * 110).astype(np.uint8)))
            dbg.alpha_composite(ov)
            tex.save(f"/tmp/yz/ph_{name}_tex{n}.png")
    if sc.get("lamp"):                                             # фара загорается, когда мопед встал
        l = sc["lamp"]
        defs.append('<radialGradient id="lg"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".22" stop-color="#eaf4ff" stop-opacity=".75"/>'
                    '<stop offset=".5" stop-color="#cfe6ff" stop-opacity=".22"/><stop offset="1" stop-color="#cfe6ff" stop-opacity="0"/></radialGradient>')
        top.append(f'<circle cx="{l["c"][0]}" cy="{l["c"][1]}" r="{l["r"]}" fill="url(#lg)" opacity="0">'
                   f'<animate attributeName="opacity" values="0;1;.35;1" keyTimes="0;.3;.55;1" begin="{DUR - .2}s" dur=".5s" fill="freeze"/></circle>')
    body = "".join(top)
    if sc.get("sway"):                                             # мопед встал и чуть качнулся
        s = sc["sway"]
        vals = ";".join(f'{d} {s["c"][0]} {s["c"][1]}' for d in s["deg"])
        kt = ";".join(f"{i / (len(s['deg']) - 1):.3f}" for i in range(len(s["deg"])))
        body = (f'<g><animateTransform attributeName="transform" type="rotate" values="{vals}" keyTimes="{kt}" begin="{s["begin"]}s" dur="{s["dur"]}s" fill="freeze"/>'
                f'{body}</g>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs>{"".join(defs)}</defs>{body}</svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg)
    if debug:
        d = ImageDraw.Draw(dbg)
        for w in sc["wheels"]:
            t = math.radians(w["tilt"])
            d.line([(w["c"][0] + w["rx"] * math.cos(a) * math.cos(t) - w["ry"] * math.sin(a) * math.sin(t),
                     w["c"][1] + w["rx"] * math.cos(a) * math.sin(t) + w["ry"] * math.sin(a) * math.cos(t)) for a in np.linspace(0, 2 * math.pi, 90)],
                   fill=(0, 255, 255, 255), width=1)
            for p in w["occ"]:
                d.polygon(p, outline=(0, 255, 0, 255))
        if sc.get("body"):
            d.polygon(sc["body"]["poly"], outline=(255, 255, 0, 255))
        bg = Image.new("RGBA", dbg.size, (20, 40, 110, 255))
        bg.alpha_composite(dbg)
        bg.convert("RGB").save(f"/tmp/yz/ph_{name}_dbg.png")
    return OUT / f"{name}.svg"


def fresh(name):
    """Собрать, если svg нет или он старше картинки или этого файла."""
    dst, src = OUT / f"{name}.svg", SRC / f"ph_{name}.png"
    if not dst.exists() or dst.stat().st_mtime < max(src.stat().st_mtime, Path(__file__).stat().st_mtime):
        build(name)
    return dst


if __name__ == "__main__":
    for n in SCENES:
        p = build(n, debug="--debug" in sys.argv)
        print(p, f"{p.stat().st_size / 1e3:.0f} КБ")
