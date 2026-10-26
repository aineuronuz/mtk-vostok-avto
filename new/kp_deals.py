"""Машины из КП «Авто» после 06.10.2026 — сделки ~/auto-china/kp_v3/deals/<код>.py — для «Авто в Китае» и ленты на главной
(Юрий 26.10.2026: выложить все КП после 06.10, каждое новое КП — на сайт сразу). Сделку не правим: файл исполняется как модуль,
его переменные — данные машины (CAR, PHOTOS, KP_DATE, RF_NAME) и расчёта КП (car_cny, delivery_cny, loading_cny, ENGINE_CC,
DUTY_EUR_CC / DUTY_PCT, VAT_PCT, EXCISE, recycle, ONE_INVOICE). Цена на сегодня — price.calc_deal (формула gen_kp_v3.py).
Фото — снимки сделки с табличкой «ВОСТОК-АВТО» на месте номера (углы — kp_v3/plates_kp.json, как в КП МТК), кэш CACHE.
Имя клиента на сайт не идёт. Одна и та же машина в нескольких КП — одна карточка, по последнему КП.
"""
import json
import re
from datetime import date
from pathlib import Path

AC = Path.home() / "auto-china"
DEALS = AC / "kp_v3" / "deals"
PLATES = AC / "kp_v3" / "plates_kp.json"
CACHE = Path.home() / "yurazol-sites" / "cache" / "kp_deals"     # фото с табличкой, вне репозитория
MAX_PHOTOS = 12                                                 # фото на машину: сайт и его копия на GitHub Pages не больше 1 ГБ
MONTHS = {m: i for i, m in enumerate(("январ", "феврал", "март", "апрел", "ма", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"), 1)}


def _made(car):
    """(год, месяц) выпуска: «ноябрь 2025», «9 февраля 2023», «08.2022», «2022–2023», «2022»; месяц None, если не известен."""
    s = (car.get("made") or "").lower()
    y = re.search(r"(20\d\d)", s)
    year = int(y.group(1)) if y else int(re.search(r"20\d\d", str(car.get("year"))).group(0))
    m = re.search(r"\b(\d{1,2})\.(20\d\d)", s)
    if m and "–" not in s:
        return year, int(m.group(1))
    for k, v in sorted(MONTHS.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"\b\d*\s*{k}", s):
            return year, v
    return year, None


def _num(s):
    m = re.search(r"\d[\d  ]*", s or "")
    return int(re.sub(r"\D", "", m.group(0))) if m else None


def _kind(car):
    e = (car.get("engine") or "").lower() + " " + (car.get("sub") or "").lower()
    if "электромотор" in e and ("генератор" in e or "erev" in e):
        return "erev", "Гибрид EREV"
    if "электромотор" in e or "электромобиль" in e:
        return "ev", "Электро"
    if "гибрид" in e or "hybrid" in e:
        return "hybrid", "Гибрид"
    return "ice", "Бензин"


def _plated(src, code):
    """Фото с табличкой «ВОСТОК-АВТО» (углы из plates_kp.json), иначе — само фото."""
    import plate_tool                                          # ~/auto-china/catalog — путь добавляет load()
    q = _PL.get(f"{src.parent.name}/{src.name}")
    if not q:
        return src
    dst = CACHE / code / src.name
    if not dst.exists() or dst.stat().st_mtime < max(src.stat().st_mtime, PLATES.stat().st_mtime):
        from PIL import Image
        dst.parent.mkdir(parents=True, exist_ok=True)
        plate_tool.overlay(Image.open(src), q, aspect=3.14).save(dst, "JPEG", quality=90)
    return dst


_PL = {}


def load(slugify):
    """Записи в формате kp_cars.json + "deal" (данные расчёта) — по одной на машину; ошибки сделок печатаются и пропускаются."""
    import sys
    global _PL
    if not DEALS.exists():
        return []
    sys.path.insert(0, str(AC / "catalog"))
    import plate_tool
    plate_tool.TEXT = "ВОСТОК-АВТО"                            # табличка МТК, как в КП МТК (gen_kp_mtk.py)
    _PL = json.loads(PLATES.read_text()) if PLATES.exists() else {}
    best = {}
    for f in sorted(DEALS.glob("*.py")):
        ns = {"ROOT": AC, "Path": Path, "HERE": AC / "kp_v3"}
        try:
            exec(compile(f.read_text(encoding="utf-8"), str(f), "exec"), ns)
            car = ns["CAR"]
            year, month = _made(car)
            kind, fuel = _kind(car)
            d, mth, y = (int(x) for x in ns["KP_DATE"].split("."))
            batt = re.search(r"батарея ([\d,]+) кВт", car.get("engine") or "")
            rng = re.search(r"запас хода до (\d+) км", car.get("extras") or "")
            photos = [_plated(Path(p), f.stem) for p in (ns.get("PHOTOS") or [])[:MAX_PHOTOS] if Path(p).exists()]
            rec = {
                "slug": slugify(ns.get("FILE_NAME") or f.stem), "title": car["title"].replace(" · ", " "),
                "brand": (ns.get("MODEL") or car["title"]).split()[0], "model": " ".join((ns.get("MODEL") or car["title"]).split()[1:]),
                "trim": None, "year": year, "month": month, "mileage_km": _num(car.get("mileage")),
                "kind": kind, "fuel_label": fuel, "power_hp": _num(car.get("power")), "power_kw": None,
                "volume_cc": ns.get("ENGINE_CC"), "battery_kwh": float(batt.group(1).replace(",", ".")) if batt else None,
                "range_km": int(rng.group(1)) if rng else None, "drive": car.get("drive"), "awd": "полный" in (car.get("drive") or ""),
                "transmission": car.get("gear"), "body": None, "color": None, "cond": car.get("condition"),
                "car_cny": ns["car_cny"], "photos": [str(p) for p in photos], "kp_date_iso": date(y, mth, d).isoformat(),
                "catalog_name": ns.get("RF_NAME"), "source": "deal", "kp": {"deal": f.stem, "kp_date": ns["KP_DATE"]},
                "deal": {"car_cny": ns["car_cny"], "delivery_cny": ns["delivery_cny"], "loading_cny": ns["loading_cny"],
                         "one_invoice": ns.get("ONE_INVOICE", True) is not False, "duty_pct": ns.get("DUTY_PCT"),
                         "engine_cc": ns.get("ENGINE_CC"), "duty_eur_cc": ns.get("DUTY_EUR_CC"), "vat_pct": ns.get("VAT_PCT") or 0,
                         "excise": ns.get("EXCISE") or 0, "recycle": ns["recycle"]},
            }
        except Exception as e:  # noqa: BLE001
            print("КП", f.stem, "не прочитана:", repr(e))
            continue
        key = (rec["title"], rec["year"], rec["mileage_km"], rec["deal"]["car_cny"] + rec["deal"]["delivery_cny"])
        if key not in best or best[key]["kp_date_iso"] <= rec["kp_date_iso"]:
            best[key] = rec
    return list(best.values())
