"""Цена под ключ НА СЕГОДНЯ для машин из КП (new/data/kp_cars.json) — по тем же правилам, по которым считались КП.

Правила — ~/auto-china/CONTEXT.md, формулы пошлины, сбора и утильсбора — ~/auto-china/calc.py (импортируется, не копируется).
calc(c, vtb, cny, eur, today) -> dict(total, cny, eur, vtb, date, lines, age, ...)
  vtb — курс юаня для оплаты машины (ВТБ), cny/eur — курсы ЦБ (база пошлины), today — дата расчёта.

Состав цены (как в КП, эталон kp_v3 «Как каталог»):
  машина × ВТБ, доставка автовозом 20 000 ¥ × ВТБ, погрузка и доставка по Китаю 1 300 ¥ × ВТБ, комиссия ВТБ 2% от (машина + доставка);
  таможня от суммы инвойса «машина + доставка автовозом» по курсу ЦБ (Юрий 29.10.2026, с 30.10; до того от цены машины без доставки):
    бензин, HEV, PHEV — единая ставка calc.custom_duty (по возрасту: до 3 лет — % от стоимости, не менее €/см³; 3–5 и старше 5 — €/см³);
    электро, EREV, e-POWER — СТП: пошлина 15% + акциз по 30-мин мощности + НДС 22% от (стоимость + пошлина + акциз);
  таможенный сбор calc.custom_fee, утильсбор calc.recycle (бензин — по мощности ДВС, HEV/PHEV — по системной, электро — по 30-мин);
  СВХ, оформление 80 000 ₽, подбор и сопровождение — тарифы города выдачи на сегодня.
Возраст — на дату прибытия: сегодня + 50…65 дней (срок по договору). Если на этом отрезке (или из-за неизвестного месяца
выпуска) возрастная категория может быть разной, берётся более дорогой вариант.
"""
import importlib.util
from datetime import date, timedelta
from pathlib import Path

_AC = Path.home() / "auto-china"
_spec = importlib.util.spec_from_file_location("auto_china_calc", _AC / "calc.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

# тарифы — одни для всех городов (Юрий 26.10.2026: на сайте без городов, подбор и сопровождение 90 000 ₽, СВХ 20 500 ₽ везде;
# до того по городу выдачи: Глеб/СПб 90 000 и 20 500, Иван/Екб 80 000 и 9 248 за 5 суток)
TARIFF = {"services": 90_000, "svh": 20_500, "svh_label": "Склад временного хранения"}
CLEARANCE = 80_000            # оформление: растаможка, СБКТС, ЭПТС
DELIVERY_CNY = 20_000         # доставка автовозом из Китая
LOADING_CNY = 1_300           # погрузка и доставка по Китаю
BANK_FEE = 0.02               # комиссия ВТБ от суммы «машина + доставка»
ARRIVAL_DAYS = (50, 65)       # срок от оплаты до выдачи по договору (CONTEXT.md, 04.10.2026)
UTIL_2027 = date(2027, 1, 1)  # с 01.01.2027 коммерческий утильсбор +10%, льготный прежний (Юрий 27.10.2026)
EV_DUTY = 0.15
VAT = 0.22
# акциз 2026 (ст. 193 НК РФ), ₽ за л.с. 30-минутной мощности, ставка бэнда на всю мощность
AKCIZ = [(90, 0), (150, 64), (200, 613), (300, 1004), (400, 1711), (500, 1771), (None, 1829)]
AGE_RU = {"less-then-three": "до 3 лет", "three-five": "3–5 лет", "more-then-five": "старше 5 лет"}
_ORDER = {"less-then-three": 0, "three-five": 1, "more-then-five": 2}


def _n(v):
    return f"{round(v):,}".replace(",", " ")


def _add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:                      # 29 февраля
        return d.replace(year=d.year + n, day=28)


def _cat(made, arrive):
    if arrive < _add_years(made, 3):
        return "less-then-three"
    if arrive < _add_years(made, 5):
        return "three-five"
    return "more-then-five"


def age_categories(c, today):
    """Возможные возрастные категории на дату прибытия: выпуск — месяц (или весь год, если месяц не известен)."""
    y, m = c.get("year"), c.get("month")
    if not y:
        return ["three-five"]
    if m:
        made0 = date(y, m, 1)
        made1 = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    else:
        made0, made1 = date(y, 1, 1), date(y, 12, 31)
    a0, a1 = today + timedelta(days=ARRIVAL_DAYS[0]), today + timedelta(days=ARRIVAL_DAYS[1])
    return sorted({_cat(made1, a0), _cat(made0, a1)}, key=_ORDER.get)


def rec_on_arrival(rec, today):
    """Утильсбор на дату прибытия: если окно прибытия (сегодня + 50…65 дней) задевает 2027 год — коммерческий × 1,1."""
    if today and rec > 5_200 and today + timedelta(days=ARRIVAL_DAYS[1]) >= UTIL_2027:
        return round(rec * 1.1)
    return rec


def util_label(rec, today):
    if rec <= 5_200:
        return "Утилизационный сбор — льготный"
    return "Утилизационный сбор" + (" — ставка 2027 года" if today and today + timedelta(days=ARRIVAL_DAYS[1]) >= UTIL_2027 else "")


def akciz_rate(hp):
    for top, rate in AKCIZ:
        if top is None or hp <= top:
            return rate


def _one(c, vtb, cny, eur, age, t, today=None):
    rates = {"CNY": 1 / cny, "EUR": 1 / eur}           # формат calc.py: валюта за 1 ₽
    car_cny = c["car_cny"]
    dcny = c.get("delivery_cny") or DELIVERY_CNY
    lcny = c.get("loading_cny") or LOADING_CNY
    car_rub = round(car_cny * vtb)
    deliv_rub = round(dcny * vtb)
    load_rub = round(lcny * vtb)
    bank = round((car_rub + deliv_rub) * BANK_FEE)
    cost_rub = C.cny_to_rub(car_cny + dcny, rates)      # таможенная стоимость: машина + доставка по курсу ЦБ (Юрий 29.10.2026)
    fee = C.custom_fee(cost_rub)
    lines = [(f"Автомобиль в Китае ({_n(car_cny)} ¥ × {vtb:.2f})".replace(".", ","), car_rub),
             (f"Доставка автовозом ({_n(dcny)} ¥)", deliv_rub),
             (f"Погрузка и доставка по Китаю ({_n(lcny)} ¥)", load_rub),
             ("Комиссия банка ВТБ 2%", bank)]
    if c.get("tax") == "ev":
        duty = round(cost_rub * EV_DUTY)
        hp = c.get("akciz_hp") or 0
        akciz = round(hp * akciz_rate(hp))
        vat = round((cost_rub + duty + akciz) * VAT)
        rec, coef = C.recycle(0, c["util_kw"], age, "electric")
        rec = rec_on_arrival(rec, today)
        lines.append(("Таможенная пошлина 15%", duty))
        if akciz:
            lines.append((f"Акциз ({hp} л.с.)", akciz))
        lines.append(("НДС 22%", vat))
        extra = akciz + vat
    else:
        duty_v, kind = C.custom_duty(cost_rub, c["volume_cc"], age, rates)
        duty = round(duty_v)
        kw = c.get("util_kw") or c["power_hp"] * 0.7355
        rec, coef = C.recycle(c["volume_cc"], kw, age, c.get("util_table") or "gasoline")
        rec = rec_on_arrival(rec, today)
        if kind == "vol":
            per_cc = f"{duty_v * rates['EUR'] / c['volume_cc']:.2f}".rstrip("0").rstrip(".").replace(".", ",")   # € за см³
            lines.append((f"Таможенная пошлина ({c['volume_cc']} см³ × {per_cc} €)", duty))
        else:
            lines.append(("Таможенная пошлина (% от стоимости)", duty))
        extra = 0
    lines += [("Таможенный сбор", fee),
              (util_label(rec, today), rec),
              (t["svh_label"], t["svh"]),
              ("Оформление: растаможка, СБКТС, ЭПТС", CLEARANCE),
              ("Подбор автомобиля и сопровождение сделки", t["services"])]
    total = car_rub + deliv_rub + load_rub + bank + duty + extra + fee + rec + t["svh"] + CLEARANCE + t["services"]
    assert total == sum(v for _, v in lines)
    return {"total": total, "lines": lines, "age": age, "age_ru": AGE_RU[age], "duty": duty, "customs_fee": fee,
            "recycle": rec, "recycle_coef": coef}


def calc(c, vtb, cny, eur, today):
    """Цена под ключ машины c на дату today: vtb — курс юаня ВТБ, cny/eur — курсы ЦБ (₽ за 1 ¥ / 1 €)."""
    t = TARIFF
    best = None
    for age in age_categories(c, today):
        r = _one(c, vtb, cny, eur, age, t, today)
        if best is None or r["total"] > best["total"]:
            best = r
    best.update(vtb=vtb, cny=cny, eur=eur, date=today.isoformat())
    return best


if __name__ == "__main__":                              # проверка: python3 new/price.py
    import json
    import sys
    cars = json.loads((Path(__file__).parent / "data" / "kp_cars.json").read_text())
    k = json.loads((Path(__file__).parent / "data" / "rates.json").read_text())
    vtb = float(sys.argv[1]) if len(sys.argv) > 1 else 12.65
    for c in cars[:5]:
        r = calc(c, vtb, k["cny"], k["eur"], date.today())
        print(c["slug"], r["total"], r["age_ru"])


def calc_deal(c, vtb, cny, eur, today):
    """Цена под ключ на сегодня машины из КП после 06.10.2026 (~/auto-china/kp_v3/deals/*.py, данные — c["deal"], kp_deals.py):
    формула КП gen_kp_v3.py — один контракт и инвойс (Юрий 18.10: таможенная стоимость — машина + доставка; с 30.10 и в старых сделках
    с ONE_INVOICE = False — Юрий 29.10.2026, там это только две строки вместо одной), пошлина (% или €/см³), акциз, НДС и утильсбор — как в сделке; курсы — дня; оформление, СВХ и услуги — TARIFF.
    Возрастная категория — та, что в сделке на дату КП."""
    d, t = c["deal"], TARIFF
    car_rub, deliv_rub, load_rub = round(d["car_cny"] * vtb), round(d["delivery_cny"] * vtb), round(d["loading_cny"] * vtb)
    bank = round((car_rub + deliv_rub) * BANK_FEE)
    cv = round((d["car_cny"] + d["delivery_cny"]) * cny)   # таможенная стоимость: машина + доставка по курсу ЦБ
    duty = round(cv * d["duty_pct"]) if d["duty_pct"] else round(d["engine_cc"] * d["duty_eur_cc"] * eur)
    excise = d["excise"] or 0
    vat = round((cv + duty + excise) * (d["vat_pct"] or 0))
    fee = C.custom_fee(cv)
    rec = rec_on_arrival(d["recycle"], today)
    r = f"{vtb:.2f}".replace(".", ",")
    if d["one_invoice"]:
        lines = [(f"Автомобиль с доставкой ({_n(d['car_cny'] + d['delivery_cny'])} ¥ × {r})", car_rub + deliv_rub)]
    else:
        lines = [(f"Автомобиль в Китае ({_n(d['car_cny'])} ¥ × {r})", car_rub), (f"Доставка автовозом ({_n(d['delivery_cny'])} ¥)", deliv_rub)]
    lines += [(f"Погрузка и доставка по Китаю ({_n(d['loading_cny'])} ¥)", load_rub), ("Комиссия банка ВТБ 2%", bank)]
    if d["duty_pct"]:
        lines.append((f"Таможенная пошлина {d['duty_pct'] * 100:.0f}% от стоимости", duty))
    else:
        lines.append((f"Таможенная пошлина ({d['engine_cc']} см³ × {str(d['duty_eur_cc']).replace('.', ',')} €)", duty))
    if excise:
        lines.append(("Акциз", excise))
    if vat:
        lines.append((f"НДС {d['vat_pct'] * 100:.0f}%", vat))
    lines += [("Таможенный сбор", fee), (util_label(rec, today), rec),
              (t["svh_label"], t["svh"]), ("Оформление: растаможка, СБКТС, ЭПТС", CLEARANCE),
              ("Подбор автомобиля и сопровождение сделки", t["services"])]
    total = sum(v for _, v in lines)
    return {"total": total, "lines": lines, "vtb": vtb, "cny": cny, "eur": eur, "date": today.isoformat()}
