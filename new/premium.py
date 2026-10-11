"""Страница «Новые премиальные автомобили из Китая» (Юрий 11.10.2026: отдельная вкладка, фильтр европейские, японские,
корейские, американские, китайские). Готовит данные и фото, страницу рисует site.py (premium_page) из data/premium.json.

Модели — премиум-каталог МТК СПб: ~/auto-china/catalog/cars_prem26/<марка>.json, марки, порядок и исключения —
GROUPS, ORDER и SKIP из gen_catalog_prem_mtk.py (одна карточка на модель, как в каталоге).
Фото — ~/auto-china/catalog/site_photos/final/<модель>.jpg (Wikimedia Commons, авторы и лицензии — sources.json):
окно 17:10 вокруг машины (рамка rembg, кэш data/premium_bbox.json), только обрезка и уменьшение, номера не трогаются.
Цена «от» (Юрий 11.10.2026: «цены возьми из каталога») — младшая строка карточки в PDF премиум-каталога на PRICE_DATE
(catalog/out/Katalog-MTK-Premium-*-SPB-telefon-<дата>.pdf); ставится, только если совпадает с расчётом prem26_calc.py
по тем же версиям, что в каталоге. Нет в PDF или расходится — карточка без цены.
Запуск: python3 new/premium.py (после — python3 new/site.py --offline)
"""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "new" / "data"
OUT_IMG = ROOT / "docs" / "img" / "p"
CAT = Path.home() / "auto-china" / "catalog"
PREM = CAT / "cars_prem26"
PHOTOS = CAT / "site_photos" / "final"
SOURCES = CAT / "site_photos" / "sources.json"
BBOX = DATA / "premium_bbox.json"
W, H = 640, 376                                         # 17:10, как .card .im

# группа фильтра — по стране марки (решение «Авто» 11.10.2026); Lotus — британская марка, Volvo — шведская
ORIGINS = [("eu", "Европейские"), ("jp", "Японские"), ("kr", "Корейские"), ("us", "Американские"), ("cn", "Китайские")]
ORIGIN = {"mercedes": "eu", "bmw": "eu", "audi": "eu", "porsche": "eu", "volvo": "eu", "jaguar": "eu", "landrover": "eu",
          "lotus": "eu", "polestar": "eu", "lexus": "jp", "infiniti": "jp", "genesis": "kr", "cadillac": "us", "tesla": "us",
          "liauto": "cn", "xiaomi": "cn", "zeekr": "cn", "nio": "cn", "avatr": "cn", "voyah": "cn", "aito": "cn",
          "denza": "cn", "yangwang": "cn", "hongqi": "cn", "im": "cn"}


def catalog_rules():
    """GROUPS (первое присваивание), ORDER и SKIP из генератора премиум-каталога — без его запуска."""
    tree = ast.parse((CAT / "gen_catalog_prem_mtk.py").read_text())
    got = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("GROUPS", "ORDER", "SKIP", "PRICE_DATE") and name not in got:
                try:
                    got[name] = ast.literal_eval(node.value)
                except ValueError:
                    pass
    return got["GROUPS"], got["ORDER"], got["SKIP"], got["PRICE_DATE"]


def models():
    groups, order, skip, _ = catalog_rules()
    brands = [b for _, _, bs in groups for b in bs]
    out = []
    for b in brands:
        f = PREM / f"{b}.json"
        if not f.exists():
            continue
        fams = {}
        for m in json.loads(f.read_text()):
            k = m.get("family") or m["model"]
            if k not in skip:
                fams.setdefault(k, []).append(m)
        o = order.get(b, [])
        keys = sorted(fams, key=lambda k: (o.index(k) if k in o else len(o), min(v["msrp_cny"] for x in fams[k] for v in x["versions"])))
        for k in keys:
            out.append({"vs": calc_rows(fams[k]), "key": k, "name": fams[k][0]["model"].split(" PHEV")[0], "cn": fams[k][0].get("cn") or "", "brand": b,
                        "origin": ORIGIN[b]})
    rank = {k: i for i, (k, _) in enumerate(ORIGINS)}
    out.sort(key=lambda m: rank[m["origin"]])         # sort устойчивый: внутри группы — порядок марок и моделей каталога
    return out


def calc_rows(mdls):
    """Цены строк карточки каталога, как в load_group (gen_catalog_prem_mtk.py): три версии, по цене под ключ."""
    if str(CAT) not in sys.path:
        sys.path.insert(0, str(CAT))
    import prem26_calc as C
    vs = sorted((v for x in mdls for v in x["versions"]), key=lambda v: v["msrp_cny"])
    vs = vs if len(vs) <= 3 else [vs[0], vs[len(vs) // 2], vs[-1]]
    return sorted(C.up10k(C.price(v)["total"]) for v in vs)


def pdf_prices(names, date):
    """Цены строк каждой модели из телефонных PDF премиум-каталога на дату: {модель: [цены по порядку]}."""
    pdfs = sorted((CAT / "out").glob(f"Katalog-MTK-Premium-*-SPB-telefon-{date}.pdf"))
    out, cur = {}, None
    for f in pdfs:
        txt = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True, check=True).stdout
        for ln in txt.splitlines():
            s = ln.strip()
            if s in names:
                cur = s
                out.setdefault(cur, [])
                continue
            m = re.match(r"^(БАЗОВАЯ|СРЕДНЯЯ|МАКСИМАЛЬНАЯ|ВЕРСИЯ)\s+([\d\s]+)₽", s)
            if m and cur:
                out[cur].append(int(re.sub(r"\D", "", m.group(2))))
    return out, [f.name for f in pdfs]


def bbox(src, im):
    db = json.loads(BBOX.read_text()) if BBOX.exists() else {}
    key = f"{src.name}:{im.width}x{im.height}"
    if key not in db:
        from rembg import new_session, remove
        global _RB
        if "_RB" not in globals():
            _RB = new_session("u2net")
        sm = im.copy()
        sm.thumbnail((640, 640))
        m = remove(sm, session=_RB, only_mask=True).point(lambda v: 255 if v > 128 else 0)
        k = im.width / sm.width
        db[key] = [round(v * k) for v in (m.getbbox() or (0, 0, sm.width, sm.height))]
        BBOX.write_text(json.dumps(db, indent=0))
    return db[key]


def crop_box(size, bb):
    """Окно 17:10 вокруг машины: машина ~88% ширины окна, не больше кадра, увеличение не больше 1,6 раза.
    Если машина в такое окно не входит (выходит за край больше чем на 5%), окно — машина с полями 3% и столько фона,
    сколько даёт кадр: фото другой пропорции, в карточке вписывается целиком (fit = True)."""
    w, h = size
    R = W / H
    x0, y0, x1, y1 = max(bb[0], 0), max(bb[1], 0), min(bb[2], w), min(bb[3], h)
    full = min(w, h * R)
    cw = max((x1 - x0) / 0.88, (y1 - y0) * 1.25 * R, full / 1.6, W)
    cw = min(cw, full)
    ch = cw / R
    if (x1 - x0) <= cw * 1.05 and (y1 - y0) <= ch * 1.05:
        L = min(max((x0 + x1) / 2 - cw / 2, 0), w - cw)
        T = min(max((y0 + y1) / 2 - ch / 2, 0), h - ch)
        return (round(L), round(T), round(L + cw), round(T + ch)), False
    mx, my = (x1 - x0) * 0.03, (y1 - y0) * 0.03
    cw, ch = min(x1 - x0 + 2 * mx, w), min(y1 - y0 + 2 * my, h)
    if cw / ch > R:
        ch = min(cw / R, h)
    else:
        cw = min(ch * R, w)
    L = min(max((x0 + x1) / 2 - cw / 2, 0), w - cw)
    T = min(max((y0 + y1) / 2 - ch / 2, 0), h - ch)
    return (round(L), round(T), round(L + cw), round(T + ch)), True


def edge_colors(im):
    """Цвет полей вокруг вписанного фото — средний цвет его краёв (верх и низ или лево и право)."""
    wide = im.width / im.height > W / H
    k = max(2, round((im.height if wide else im.width) * 0.04))
    a = im.crop((0, 0, im.width, k) if wide else (0, 0, k, im.height)).resize((1, 1), Image.BOX).getpixel((0, 0))
    b = im.crop((0, im.height - k, im.width, im.height) if wide else (im.width - k, 0, im.width, im.height)).resize((1, 1), Image.BOX).getpixel((0, 0))
    return "to bottom" if wide else "to right", "#%02x%02x%02x" % a, "#%02x%02x%02x" % b


def main():
    src = json.loads(SOURCES.read_text())
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    cards, nophoto, fitted, noprice = [], [], [], []
    ms = models()
    date = catalog_rules()[3]
    pdf, pdfs = pdf_prices({m["name"] for m in ms}, date)
    for m in ms:
        rows = m.pop("vs")
        m["price"] = rows[0] if pdf.get(m["name"]) == rows else None
        p = PHOTOS / f"{m['key']}.jpg"
        s = src.get(m["key"])
        if not p.exists() or not s:
            nophoto.append(m["name"])
            continue
        im = Image.open(p).convert("RGB")
        box, fit = crop_box(im.size, bbox(p, im))
        slug = m["key"].lower()
        im = im.crop(box)
        k = min(W / im.width, H / im.height) if fit else W / im.width
        im = im.resize((round(im.width * k), round(im.height * k)) if fit else (W, H), Image.LANCZOS)
        im.save(OUT_IMG / f"{slug}.webp", quality=72, method=6)
        if fit:
            fitted.append(m["name"])
        if m["price"] is None:
            noprice.append(m["name"])
        cards.append(dict(m, img=f"img/p/{slug}.webp", size=list(im.size), bg=list(edge_colors(im)) if fit else None,
                          author=s["author"], license=s["license"], license_url=s["license_url"], page=s["page"]))
    live = {Path(c["img"]).name for c in cards}
    for f in OUT_IMG.glob("*.webp"):
        if f.name not in live:
            f.unlink()
    (DATA / "premium.json").write_text(json.dumps({"origins": ORIGINS, "price_date": date, "pdfs": pdfs, "cards": cards, "nophoto": nophoto, "noprice": noprice}, ensure_ascii=False, indent=1))
    by = {k: sum(c["origin"] == k for c in cards) for k, _ in ORIGINS}
    size = sum(f.stat().st_size for f in OUT_IMG.glob("*.webp"))
    print(f"PDF: {pdfs}; цены на {date}: с ценой {len(cards) - len(noprice)}, без цены {noprice}")
    print(f"карточек {len(cards)}: {by}; без фото: {nophoto}; вписаны целиком: {len(fitted)} {fitted}; фото {size / 1e6:.1f} МБ")


if __name__ == "__main__":
    main()
