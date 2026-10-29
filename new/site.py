"""Новый многостраничный сайт МТК Восток-Авто (Юрий 05.10.2026: «как mercedes-benz.com», сине-белый, многостраничный,
каталог с фильтрами, машины из КП с ценой на сегодня, частые вопросы).

Собирает docs/ — основной адрес mtk-vostok-avto.ru (Юрий одобрил 06.10.2026; до того был /new/, закрыт от поиска) из:
  ~/auto-china/catalog/cars_data.py — модели каталога (цены «Авто», 109 на 20.10.2026);
  new/data/models.json — описания моделей; new/data/kp_cars.json + new/price.py — машины из КП и расчёт под ключ;
  new/data/faq.json — частые вопросы; new/src/s.css, s.js — оформление.
Курс: ЦБ — cbr-xml-daily.ru; курс юаня для расчёта — ВТБ на сегодня (day_rate(), «Авто» 11.10.2026), записывается
в new/data/kurs_dnya.json — оттуда его берут КП. Цены всех трёх разделов (Каталог, Авто в Китае, Премиум) — по нему.
«Мопеды» — электромопеды «Восток-Мото» из выгрузки проекта «Мото» (moto_page), цены в ней уже в рублях.
Запуск: python3 new/site.py [--offline]
"""
import hashlib
import html
import importlib.util
import json
import math
import os
import random
import re
import shutil
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent          # репозиторий mtk-vostok-avto.ru
NEW = ROOT / "new"
DATA = NEW / "data"
OUT = ROOT / "docs"                                    # docs/foto/, docs/assets/, CNAME — не трогаются
IMG = OUT / "img"
BASE = "/"
SITE = "https://mtk-vostok-avto.ru"
PREVIEW = False                                         # True — noindex, для пробной версии
SEARCH = json.loads((DATA / "search.json").read_text()) if (DATA / "search.json").exists() else {}   # ключ IndexNow и коды подтверждения Яндекс Вебмастера, Google и Bing
VERIFY = "".join(f'<meta name="{n}" content="{SEARCH[k]}">' for k, n in (("google", "google-site-verification"), ("yandex", "yandex-verification"), ("bing", "msvalidate.01")) if SEARCH.get(k))
METRIKA_SNIP = '<!-- Yandex.Metrika counter -->\n<script type="text/javascript">\n    (function(m,e,t,r,i,k,a){\n        m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};\n        m[i].l=1*new Date();\n        for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}\n        k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)\n    })(window, document,\'script\',\'https://mc.yandex.ru/metrika/tag.js?id=@@ID@@\', \'ym\');\n\n    ym(@@ID@@, \'init\', {ssr:true, webvisor:true, clickmap:true, ecommerce:"dataLayer", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true});\n</script>\n<noscript><div><img src="https://mc.yandex.ru/watch/@@ID@@" style="position:absolute; left:-9999px;" alt="" /></div></noscript>\n<!-- /Yandex.Metrika counter -->'
METRIKA = METRIKA_SNIP.replace("@@ID@@", SEARCH["metrika"]) + "\n" if SEARCH.get("metrika") else ""   # счётчик Яндекс Метрики 113843035 (Юрий 28.10.2026) — на всех страницах, кроме пробной версии
AC = Path.home() / "auto-china"
CARS = AC / "catalog" / "cars"
CARS_MTK = AC / "catalog" / "cars_plate_mtk"           # те же фото с номером «ВОСТОК-АВТО», как в каталоге МТК
MTK = AC / "mtk"
MOTO = Path.home() / "KATE" / "мото" / "catalog"          # выгрузка «Мото» для сайта: out/site/mopedy.json и out/site/foto/, логотип «Восток-Мото»
MAIN_IMG = ROOT / "docs" / "assets" / "img"            # фото основного сайта (выданные, специалисты)
BOOKMAN = "/usr/share/fonts/opentype/urw-base35/URWBookman-Demi.otf"
TODAY = date.today()
E = html.escape

sys.path.insert(0, str(AC / "catalog"))
import cars_data  # noqa: E402

_spec = importlib.util.spec_from_file_location("mtk_build", ROOT / "build.py")
_mb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mb)
TEAM = _mb.TEAM
MAX_HREF = "https://max.ru/u/f9LHodD0cOLQzwPoUyWBoejqc5iq940FAYmSIsMAm8Hr1FcNu85zWG126zY"
CHANNEL = "https://t.me/mtk_vostok_avto"
# «Получить КП в Telegram / в MAX» (Сергей и «Авто» 28.10.2026): кнопка открывает бота заявок со ссылкой на машину, бот сразу присылает
# расчёт под ключ (new/data/bot_cars.json — те же цифры, что на странице), потом просит согласие и номер. Бот — tools/mtk-zayavki/bot.py.
# Кнопки и ссылка на политику в подвале включены 29.10.2026: Юрий «Запускай сразу» («Авто» 29.10), оператор — ИП Золотарев,
# база бота — на сервере Рины в Москве. Выключить — KP_ON = False.
KP_ON = True
TG_BOT = "vostokavto_zayavki_bot"                       # создал Юрий 28.10.2026
MAX_BOT = ""                                            # бота МТК в MAX нет (28.10.2026)
OPERATOR = "ИП Золотарев Юрий Николаевич, ИНН 183474446770"   # оператор персональных данных (Юрий 29.10.2026)
OPERATOR_RKN = ", в&nbsp;реестре операторов Роскомнадзора под&nbsp;№&nbsp;18-25-028274"   # номер в реестре РКН («Анализ» через KATE 28.10.2026)
# марки по-русски в заголовках и описаниях страниц: так их ищут в Яндексе и Google — «Чанган Q05», «Джили из Китая» (Юрий 28.10.2026, индексация)
BRAND_RU = {"Arcfox": "Аркфокс", "Audi": "Ауди", "BMW": "БМВ", "BYD": "БИД", "Changan": "Чанган", "Chery": "Чери", "Chevrolet": "Шевроле",
            "Dongfeng": "Донгфенг", "Exeed": "Эксид", "Ford": "Форд", "GAC": "ГАК", "GWM": "Грейт Вол", "Geely": "Джили", "Haval": "Хавал",
            "Honda": "Хонда", "Hyundai": "Хендай", "Jetour": "Джетур", "Jetta": "Джетта", "Jinbei": "Джинбей", "Kia": "Киа", "Leapmotor": "Липмотор",
            "Lexus": "Лексус", "Livan": "Ливан", "Lixiang": "Лисян", "MG": "МГ", "Mazda": "Мазда", "Mercedes-Benz": "Мерседес", "Mitsubishi": "Мицубиси",
            "NIO": "Нио", "Nissan": "Ниссан", "Roewe": "Роеве", "Skoda": "Шкода", "Subaru": "Субару", "Toyota": "Тойота", "Venucia": "Венусия",
            "VW": "Фольксваген", "Volkswagen": "Фольксваген", "Voyah": "Воя", "Wuling": "Вулинг", "Xiaomi": "Сяоми"}


def ru_brand(brand):
    """« (Чанган)» — марка по-русски в скобках, пусто для марки без русского написания."""
    return f" ({BRAND_RU[brand]})" if brand in BRAND_RU else ""


MENU = [("katalog/", "Каталог"), ("avto/", "Авто в Китае"), ("premium/", "Премиум-авто"), ("vydannye/", "Выданные авто"), ("mopedy/", "Электромопеды"),
        ("stoimost/", "Стоимость"), ("kalkulyator/", "Калькулятор"), ("kak-kupit/", "Как купить"), ("voprosy/", "Вопросы"), ("kontakty/", "Контакты")]   # порядок, «Премиум-авто» и «Электромопеды» — Юрий 26.10.2026 («Авто» 26.10); «Калькулятор» отдельно от «Стоимости» — Юрий 27.10.2026
PAGES = []                                              # (путь, приоритет) — для sitemap.xml
MIN_YEAR = 2022                                         # машины 2021 года не показывать (Юрий 06.10.2026)


# ---------- мелочи ----------
def nb(s):
    return s.replace(" ", "&nbsp;")


def rub(v):
    return f"{round(v):,}".replace(",", "&nbsp;") + "&nbsp;₽"


def nf(v):
    """Число с неразрывными пробелами между тысячами: 20&nbsp;000."""
    return f"{round(v):,}".replace(",", "&nbsp;")


def mln(v):
    return f"{v / 1e6:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def price_range(a, b):
    return f"от {mln(a)}" + (f" до {mln(b)}" if b else "") + "&nbsp;млн&nbsp;₽"


def lo_price(m):
    """Самая низкая цена модели: у электро с двумя ценами — б/у («Авто» 15.10.2026)."""
    return min(x for x in (m.get("bu_from"), m["from"]) if x)


def price_lines(m):
    """[(подпись, цена)]: у электро сначала б/у, потом новый («Авто» 15.10.2026), б/у нет — «цена по запросу»; у остальных одна цена."""
    if "bu_label" not in m:
        return [(None, price_range(m["from"], m["to"]))]
    return [(m["bu_label"], price_range(m["bu_from"], None) if m.get("bu_from") else None), ("Новый", price_range(m["from"], m["to"]))]


def price_html(m):
    return "".join(f'<span class="pl"><i>{E(t)}</i>{v or "<em>цена по&nbsp;запросу</em>"}</span>' if t else v for t, v in price_lines(m))


def price_text(m):
    return ", ".join(f"{t.lower()} {v or 'цена по запросу'}" if t else v for t, v in ((t, v and html.unescape(v)) for t, v in price_lines(m)))


def ddmm(d):
    return d.strftime("%d.%m.%Y")


def plural(n, one, few, many):
    n = abs(n) % 100
    if 10 < n < 20:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


def slugify(s):
    tr = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))
    s = "".join(tr.get(c, c) for c in s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def deck_src(k):
    """Фото блока на главной: первый кадр его ролика (new/src/deck<k>.jpg), если ролик есть, иначе фото из каталога."""
    p = NEW / "src" / f"deck{k}.jpg"
    return p if p.exists() else CARS / f"hero_sec{k}.jpg"


TILE_SCALE = {1: 0.76, 2: 0.86, 3: 0.98}   # машины плиток Каталога в одном масштабе с Changan Q05 на «Электро» (Юрий 27.10.2026; замер rembg)


def deck_img(k, dst, w=1100, q=76):
    """Фото блока главной и плитки Каталога: машина уменьшена в TILE_SCALE[k] раз, по краям — продолжение фона
    (крайние пиксели кадра, размытые) с мягким швом. Ролики блоков уменьшает так же tools/deck_scale.py."""
    src = deck_src(k)
    if dst.exists() and dst.stat().st_mtime >= max(Path(src).stat().st_mtime, Path(__file__).stat().st_mtime):
        return
    import numpy as np
    from PIL import ImageFilter
    im = Image.open(src).convert("RGB")
    w = min(w, im.width)
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    sc = TILE_SCALE.get(k, 1)
    if sc < 1:
        W, H = im.size
        sw, sh = round(W * sc), round(H * sc)
        x0, y0 = (W - sw) // 2, (H - sh) // 2
        small = np.asarray(im.resize((sw, sh), Image.LANCZOS))
        pad = np.pad(small, ((y0, H - sh - y0), (x0, W - sw - x0), (0, 0)), mode="edge")
        pad[y0 + sh:] = small[-1].mean(axis=0).astype(np.uint8)   # низ — ровный цвет пола: в крайнем ряду отражение машины
        bg = Image.fromarray(pad).filter(ImageFilter.GaussianBlur(28))
        f = round(min(sw, sh) * 0.08)
        mask = Image.new("L", (sw, sh), 0)
        mask.paste(255, (f, f, sw - f, sh - f))
        mask = mask.filter(ImageFilter.GaussianBlur(f / 2))
        bg.paste(Image.fromarray(small), (x0, y0), mask)
        im = bg
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, quality=q, method=6)


def webp(src, dst, w, q=74, crop=None, alpha=False):
    """Картинка в webp не шире w; пересобирается, только если исходник новее. alpha — с прозрачностью."""
    dst = Path(dst)
    if dst.exists() and dst.stat().st_mtime >= Path(src).stat().st_mtime:
        with Image.open(dst) as im:
            return im.size
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGBA" if alpha else "RGB")
    if crop:
        im = im.crop(crop)
    if im.width > w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(dst, quality=q, method=6)
    return im.size


def u(path=""):
    return BASE + path


# ---------- курс ----------
def cbr_rates(offline=False):
    """ЦБ: юань, евро и доллар (для цен мопедов) на сегодня; при сбое — последние сохранённые."""
    keep = DATA / "rates.json"
    if not offline:
        try:
            with urllib.request.urlopen("https://www.cbr-xml-daily.ru/daily_json.js", timeout=20) as r:
                d = json.load(r)
            res = {"date": d["Date"][:10], "cny": d["Valute"]["CNY"]["Value"] / d["Valute"]["CNY"]["Nominal"],
                   "eur": d["Valute"]["EUR"]["Value"], "usd": d["Valute"]["USD"]["Value"]}
            keep.write_text(json.dumps(res, ensure_ascii=False, indent=1))
            return res
        except Exception as e:  # noqa: BLE001
            print("ЦБ недоступен:", e)
    return json.loads(keep.read_text())


VTB_URL = "https://www.vtb.ru/api/currencyrates/table?category=3&type=1"   # интернет- и мобильный банк
VTB_CA = DATA / "russian_trusted_root_ca.pem"          # сертификат ВТБ — от Минцифры, в системных корневых его нет
VTB_K = 1.0211                                          # запасной: ЦБ × 1,0211 — разница ВТБ и ЦБ на 11.10 (12,9415 / 12,6739)
KURS = DATA / "kurs_dnya.json"                          # курс дня для сайта и КП: дата, курс, источник


def vtb_cny():
    """Продажа юаня ВТБ в интернет- и мобильном банке, строка «до 100.00» (поле offer), и время, с которого он действует."""
    import ssl
    req = urllib.request.Request(VTB_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*", "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": "https://www.vtb.ru/personal/platezhi-i-perevody/obmen-valjuty/"})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context(cafile=str(VTB_CA))) as r:
        d = json.load(r)
    row = next(x for x in d["rates"] if x["currency1"]["code"] == "CNY" and x.get("tooltip") == "до 100.00")
    return float(row["offer"]), d.get("dateFrom", "")[:16].replace("T", " ")


def day_rate(cbr, offline=False):
    """Курс юаня для расчёта на сегодня (задача «Авто» 11.10.2026): ВТБ; если ВТБ не ответил или его курс отличается
    от ЦБ больше чем на 5% — ЦБ × 1,0211. Записывается в kurs_dnya.json. --offline: курс, записанный сегодня, иначе запасной."""
    if offline:
        k = json.loads(KURS.read_text()) if KURS.exists() else {}
        if k.get("date") == TODAY.isoformat():
            return k["vtb"], k["source"]
        return round(cbr["cny"] * VTB_K, 4), f"ЦБ {cbr['cny']:.4f} × {VTB_K} (без сети)"
    why = ""
    try:
        v, since = vtb_cny()
        if abs(v / cbr["cny"] - 1) <= 0.05:
            rate, src = v, f"ВТБ, интернет- и мобильный банк, продажа юаня до 100 ¥, курс действует с {since} по данным ВТБ"
        else:
            why = f"курс ВТБ {v} отличается от ЦБ {cbr['cny']:.4f} больше чем на 5%"
    except Exception as e:  # noqa: BLE001
        why = f"ВТБ не ответил: {e}"
    if why:
        rate, src = round(cbr["cny"] * VTB_K, 4), f"ЦБ {cbr['cny']:.4f} × {VTB_K} ({why})"
    KURS.write_text(json.dumps({"date": TODAY.isoformat(), "vtb": rate, "source": src, "cbr_cny": cbr["cny"], "cbr_eur": cbr["eur"],
                                "cbr_date": cbr["date"], "at": datetime.now().strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False, indent=1))
    return rate, src


# ---------- оформление ----------
def fonts():
    from fontTools import subset
    (OUT / "fonts").mkdir(parents=True, exist_ok=True)
    uni = (list(range(0x20, 0x7F)) + list(range(0xA0, 0x100)) + list(range(0x400, 0x460))
           + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x201E, 0x2026, 0x2116, 0x20BD, 0x2192, 0x2190, 0x2009, 0x202F, 0x2713, 0x00D7, 0x2212])
    for src, name in ((Path.home() / ".fonts/gf/GolosText[wght].ttf", "golos"), (Path.home() / ".fonts/gf/Inter[opsz,wght].ttf", "inter")):
        dst = OUT / "fonts" / f"{name}.woff2"
        if dst.exists():
            continue
        o = subset.Options()
        o.flavor = "woff2"
        o.layout_features = ["kern", "liga", "calt", "tnum", "case"]
        f = subset.load_font(str(src), o)
        s = subset.Subsetter(o)
        s.populate(unicodes=uni)
        s.subset(f)
        subset.save_font(f, str(dst), o)


def brand():
    """Круглый логотип и надпись как на обложке КП: «ВОСТОК-АВТО» (Bookman) и под ней в ту же ширину
    «МЕЖДУНАРОДНАЯ ТРАНСПОРТНАЯ КОМПАНИЯ» — синяя для белой шапки и белая для тёмной."""
    lg = Image.open(MTK / "logo" / "colors" / "MTK-logo-cvet-03-krupnee.png").convert("RGBA")
    lg = lg.crop(lg.getchannel("A").point(lambda v: 255 if v > 200 else 0).getbbox())
    for px in (64, 128, 192):
        lg.resize((px, px), Image.LANCZOS).save(IMG / f"logo{px}.webp", quality=90, method=6)
    lg.resize((128, 128), Image.LANCZOS).save(IMG / "logo128.png", optimize=True)
    lg.resize((64, 64), Image.LANCZOS).save(OUT / "favicon.png", optimize=True)
    ti = Image.new("RGBA", (180, 180), (245, 247, 251, 255))
    ti.alpha_composite(lg.resize((164, 164), Image.LANCZOS), (8, 8))
    ti.convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)

    W = 840                                           # 3× от 280 px на экране
    nm = Image.open(MTK / "kp" / "nazvanie" / "vostok-avto-gradient.png").convert("RGBA")
    nm = nm.resize((W, round(nm.height * W / nm.width)), Image.LANCZOS)
    text = "МЕЖДУНАРОДНАЯ ТРАНСПОРТНАЯ КОМПАНИЯ"
    f = ImageFont.truetype(BOOKMAN, round(W * 0.0405))
    ls = (W - f.getlength(text)) / (len(text) - 1)
    top, bot = f.getbbox("М")[1], f.getbbox("М")[3]
    gap = round(W * 0.03)
    H = nm.height + gap + (bot - top) + 4
    for name, col in (("b", None), ("w", (255, 255, 255, 255))):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if col:
            wn = Image.new("RGBA", nm.size, col)
            wn.putalpha(nm.getchannel("A"))
            im.alpha_composite(wn)
        else:
            im.alpha_composite(nm)
        d = ImageDraw.Draw(im)
        for i, c in enumerate(text):
            d.text((f.getlength(text[:i]) + i * ls, nm.height + gap - top), c, font=f, fill=col or (0x2b, 0x57, 0x97, 255))
        im.save(IMG / f"name_{name}.png", optimize=True)
    return W // 3, round(H / 3)


NW = NH = 0


def logo_html(cls="logo"):
    return (f'<a class="{cls}" href="{u()}" aria-label="МТК Восток-Авто — на главную"><picture><source type="image/webp" srcset="{u("img/logo64.webp")} 1x, {u("img/logo128.webp")} 2x, {u("img/logo192.webp")} 3x">'
            f'<img class="lg" src="{u("img/logo128.png")}" alt="" width="64" height="64"></picture>'
            f'<span class="nm"><img class="w" src="{u("img/name_w.png")}" alt="Восток-Авто — международная транспортная компания" width="{NW}" height="{NH}">'
            f'<img class="b" src="{u("img/name_b.png")}" alt="" width="{NW}" height="{NH}"></span></a>')


ASSET_V = ""


def page(path, title, desc, body, active=None, jsonld=None, og=None, prio="0.6", noindex=False):
    canon = SITE + u(path)
    menu = "".join(f'<a href="{u(p)}"{" class=\"on\"" if p == active else ""}>{t}</a>' for p, t in MENU)
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    og_img = SITE + u(og or "img/og_yu7.jpg")
    cat_links = "".join(f'<a href="{u("katalog/?cat=" + k)}">{t}</a>' for k, t, *_ in DIRS)
    team_links = "".join(f'<a href="tel:+{re.sub(r"[^0-9]", "", p["tel"])}">{p["name"].split()[0]}: {nb(p["tel"])}</a>' for p in TEAM)
    s = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
{'<meta name="robots" content="noindex,nofollow">' if PREVIEW or noindex else ''}{VERIFY if path == "" else ''}
{'' if PREVIEW else METRIKA}<link rel="canonical" href="{canon}">
<meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="МТК Восток-Авто">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}"><meta property="og:image" content="{og_img}">
<meta name="theme-color" content="#0b1f45">
<link rel="icon" type="image/png" href="{u("favicon.png")}"><link rel="apple-touch-icon" href="{u("apple-touch-icon.png")}">
<link rel="preload" href="{u("fonts/golos.woff2")}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{u("s.css")}?v={ASSET_V}">
{ld}
</head>
<body>
<header class="hdr" id="hdr"><div class="hrow">{logo_html()}<nav class="menu">{menu}</nav><a class="cta" href="{u("kontakty/")}">Написать специалисту</a>
<button class="burger" type="button" aria-label="Меню"><i></i><i></i><i></i></button></div></header>
<nav class="drawer"><a href="{u()}">Главная</a>{menu}<a class="btn w" href="{u("kontakty/")}">Написать специалисту</a></nav>
<main>
{body}
</main>
<footer><div class="wrap">
<div class="fcols">
<div>{logo_html()}<p class="fabout">Привозим новые и&nbsp;б/у автомобили из&nbsp;Китая под&nbsp;ключ: подбор, проверка, договор, доставка, растаможка и&nbsp;электронный ПТС. Работаем с&nbsp;Китаем с&nbsp;2016 года.</p></div>
<div><h4>Разделы</h4><nav>{"".join(f'<a href="{u(p)}">{t}</a>' for p, t in MENU)}</nav></div>
<div><h4>Каталог</h4><nav>{cat_links}<a href="{u("avto/")}">Авто в Китае</a></nav></div>
<div><h4>Связаться</h4><nav>{team_links}<a href="{CHANNEL}">Telegram-канал</a></nav></div>
</div>
<div class="fbot"><span>© {TODAY.year} МТК Восток-Авто · Международная транспортная компания</span><span>{f'<a href="{u("politika/")}">Политика обработки данных</a> · ' if KP_ON else ""}Цены под ключ пересчитаны {ddmm(TODAY)}</span></div>
</div></footer>
<a class="totop" href="#" aria-label="Наверх"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5.5 11.5L12 5l6.5 6.5"/></svg></a>
<script src="{u("s.js")}?v={ASSET_V}" defer></script>
</body>
</html>
"""
    dst = OUT / path / "index.html"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(s)
    if not noindex:
        PAGES.append((path, prio))


def bot_key(slug):
    """Код машины в ссылке на бота: start в Telegram — до 64 знаков, латиница, цифры, _ и -."""
    return slug if len(slug) <= 60 else slug[:51] + "-" + hashlib.md5(slug.encode()).hexdigest()[:8]


def kp_btns(start, light=False, calc=False):
    """Кнопки «Получить КП в Telegram» и «в MAX» (MAX — когда будет бот)."""
    a = (" data-kpcalc" if calc else "") + f' data-ym="{SEARCH.get("metrika", "")}"'
    b = f'<a class="btn {"w" if light else "b"}" href="https://t.me/{TG_BOT}?start={start}" data-kpm="tg"{a}>Получить КП в&nbsp;Telegram</a>'
    if MAX_BOT:
        b += f'<a class="btn {"o" if light else "ob"}" href="https://max.ru/{MAX_BOT}?start={start}" data-kpm="max"{a}>Получить КП в&nbsp;MAX</a>'
    return b


def kp_note(light=False):
    """Под кнопками «Получить КП» — ссылка на политику обработки данных («Анализ» 28.10.2026)."""
    return f'<p class="kpn{" l" if light else ""}">Расчёт придёт в&nbsp;мессенджер сразу. <a href="{u("politika/")}">Политика обработки данных</a></p>'


def crumbs(*items):
    out = [f'<a href="{u()}">Главная</a>']
    for href, t in items:
        out.append(f'<span><a href="{u(href)}">{t}</a></span>' if href else f'<span>{t}</span>')
    return f'<nav class="crumbs" aria-label="Навигация">{"".join(out)}</nav>'


def bc_ld(*items):
    el = [{"@type": "ListItem", "position": 1, "name": "Главная", "item": SITE + u()}]
    for i, (href, t) in enumerate(items, 2):
        el.append({"@type": "ListItem", "position": i, "name": html.unescape(re.sub("<[^>]+>", "", t)), "item": SITE + u(href)})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": el}


ARROWS = ('<div class="arrows"><button type="button" data-reel="{id}" data-d="-1" aria-label="Назад"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M15 5l-7 7 7 7"/></svg></button>'
          '<button type="button" data-reel="{id}" data-d="1" aria-label="Вперёд"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M9 5l7 7-7 7"/></svg></button></div>')
SVG_L = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 5l-7 7 7 7"/></svg>'
SVG_R = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 5l7 7-7 7"/></svg>'


# ---------- данные: каталог ----------
# направление каталога: ключ, подпись, категория cars_data, фото раздела, топливо
DIRS = [("ev", "Электро", "ЭЛЕКТРО", 0, "ev"), ("hyb", "Гибриды", "ГИБРИДЫ", 1, "hybrid"),
        ("fwd", "Бензин", "МОНОПРИВОД", 2, "petrol"), ("awd", "Полный привод", "ПОЛНЫЙ ПРИВОД", 3, "petrol")]
DIR_TEXT = {"ev": "У&nbsp;каждой модели две цены: б/у и&nbsp;новый. Все проходят по&nbsp;льготному утильсбору: 30-минутная мощность мотора до&nbsp;58,84&nbsp;кВт.",
            "hyb": "Toyota Corolla / Levin Hybrid и&nbsp;Honda Envix e:HEV с&nbsp;пробегом 3–5 лет: мощность системы до&nbsp;160&nbsp;л.с., утильсбор льготный.",
            "fwd": "Бензиновые машины 3–5 лет до&nbsp;160&nbsp;л.с.: Volkswagen, Toyota, Honda, Mazda, BMW, Audi, китайские Chery, Geely, Haval, Jetour и&nbsp;другие.",
            "awd": "Полный привод до&nbsp;160&nbsp;л.с. с&nbsp;пробегом 3–5 лет: Subaru и&nbsp;Mitsubishi под&nbsp;льготный утильсбор."}
FUEL_RU = {"ev": "Электро", "erev": "Гибрид EREV", "hybrid": "Гибрид", "petrol": "Бензин", "ice": "Бензин"}


UPDATE = "update_2026_10_20_160.py"                   # файл «Авто», от курсов которого посчитан cars_data.py (задача «Авто» 20.10.2026)
# модели моложе 3 лет (в cars_data "cond": "НОВЫЙ"): юани «от» и «до», объём, утильсбор. Расчёт как в КП 18.10 — один инвойс
# «машина + доставка 20 000 ¥», пошлина 48% от него по ЦБ, не меньше 3,5 €/см³; формула и проверка — docstring
# ~/auto-china/catalog/update_2026_10_20_pravki.py («Авто» 20.10.2026)
NEW3 = {"Volkswagen Tharu XR": ((90_000, 97_000), 1498, 3_400)}


def catalog_recalc(rates):
    """Пересчёт цен «Каталога» на курсы дня (задача «Авто» 11.10.2026) тем же методом, каким «Авто» пересчитывает каталог
    (~/auto-china/catalog/update_2026_10_20_160.py — с 20.10.2026, до того update_2026_10_15_bu.py; функции total и reverse из recalc_catalog.py): известные юани — прямой
    расчёт, остальные — обратным методом от цены каталога; цены «от» с Drom не пересчитываются. Электро — по юаням рынка
    из EV и ev_total того же файла: б/у и новый («Авто» 15.10.2026). База — курсы, по которым посчитан cars_data.py (NEW
    в том же файле). Возвращает f(имя, "from"|"to"|"bu_from", цена, электро) -> цена на сегодня."""
    import ast
    cat = AC / "catalog"
    src = (cat / "recalc_catalog.py").read_text()
    ns = {}
    exec(src[:src.index("# --- ТОЧНО ПО КП")], ns)   # noqa: S102 — R, total, reverse, floor10 без остального скрипта
    vol = next(ast.literal_eval(n.value) for n in ast.parse(src).body
               if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "VOL")
    up = ast.parse((cat / UPDATE).read_text()).body
    lit = {n.targets[0].id: n.value for n in up if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    vol.update(next(ast.literal_eval(n.value.args[0]) for n in up if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == "VOL.update"))
    drom, yuan = ast.literal_eval(lit["DROM"]), ast.literal_eval(lit["YUAN"])
    R, total, reverse, floor10 = ns["R"], ns["total"], ns["reverse"], ns["floor10"]
    base = R(*[ast.literal_eval(a) for a in lit["NEW"].args])
    day = R(rates["vtb"], rates["cny"], rates["eur"])
    evs = ast.literal_eval(lit["EV"])                   # имя -> (новый от, до, б/у, подпись б/у, б/у старше 3 лет)
    ev_fn = next(n for n in up if isinstance(n, ast.FunctionDef) and n.name == "ev_total")

    def ev_total(r):                                    # ev_total «Авто» (надбавка UP, утиль б/у старше 3 лет) на курсах r
        ns = {"total": total, "UP": ast.literal_eval(lit["UP"]), "NEW": r}
        exec(compile(ast.Module([ev_fn], []), UPDATE, "exec"), ns)  # noqa: S102
        return ns["ev_total"]
    ev_base, ev_day = ev_total(base), ev_total(day)

    def new3_total(y, vl, rec, r):                      # под ключ в СПб для машины моложе 3 лет, как в КП (kp_v3/gen_kp_v3.py)
        car, dl, load = round(y * r.vtb), round(20_000 * r.vtb), round(1_300 * r.vtb)
        cv = round((y + 20_000) * r.cny)
        duty = max(round(cv * 0.48), round(vl * 3.5 * r.eur))
        return car + dl + load + round((car + dl) * 0.02) + duty + ns["C"].custom_fee(cv) + rec + 80_000 + 90_000 + 20_500

    def f(name, k, v, ev):
        if v is None or (k == "from" and drom.get(name) == v):
            return v
        if name in NEW3:                                # моложе 3 лет — своя формула; цена не из неё — оставляем каталожную
            ys, vl, rec = NEW3[name]
            y = ys[0 if k == "from" else 1]
            return floor10(new3_total(y, vl, rec, day)) if floor10(new3_total(y, vl, rec, base)) == v else v
        if ev and name in evs:
            nf, nt, bu, _, old3 = evs[name]
            y = {"from": nf, "to": nt, "bu_from": bu}[k]
            a = (y, old3) if k == "bu_from" else (y,)
            if y and floor10(ev_base(*a)) == v:
                return floor10(ev_day(*a))
        i = 0 if k == "from" else 1
        kind, vl = ("ev", 0) if ev else ("ice", vol[name][i])
        y = yuan.get(name, (None, None))[i]
        if y and not ev and floor10(total(y, kind, vl, base)) == v:
            return floor10(total(y, kind, vl, day))
        y = reverse(v + 5_000, kind, vl, base)          # разница дня к цене каталога: на ступенях пошлины обратный метод
        return floor10(v + 5_000 + total(y, kind, vl, day) - total(y, kind, vl, base))   # иначе сдвигает цену и при тех же курсах
    f.evs = evs
    return f


def load_models(rates=None):
    extra = json.loads((DATA / "models.json").read_text()) if (DATA / "models.json").exists() else {}
    out, seen = [], set()
    rc = catalog_recalc(rates) if rates else None
    for key, label, cat, _, fuel in DIRS:
        c = next(x for x in cars_data.CATEGORIES if x["cat"] == cat)
        cond = c.get("cond", "")
        cond = "Б/у и новые" if "Б/У" in cond and "НОВ" in cond else "Новые" if "НОВ" in cond else "С пробегом 3–5 лет"
        for p in c["pages"]:
            for m in p["cars"]:
                x = extra.get(m["name"], {})
                slug = x.get("slug") or slugify(m["name"])
                while slug in seen:
                    slug += "-2"
                seen.add(slug)
                f = fuel
                if "EREV" in m["engine"]:
                    f = "ev erev"
                cond_m = "Новый" if "НОВ" in m.get("cond", "") else cond   # плашка модели в cars_data: Tharu XR — «НОВЫЙ» («Авто» 20.10.2026)
                photo = CARS_MTK / m["photo"] if (CARS_MTK / m["photo"]).exists() else CARS / m["photo"]
                brand_ = x.get("brand") or m["name"].split()[0]
                if rc:
                    try:
                        m = dict(m, **{k: rc(m["name"], k, m[k], cat == "ЭЛЕКТРО") for k in ("from", "to", "bu_from") if k in m})
                    except Exception as e:  # noqa: BLE001
                        print("Каталог: цена не пересчитана, оставлена из каталога —", m["name"], e)
                    m["bu_old"] = rc.evs.get(m["name"], (None,) * 5)[4]
                out.append(dict(m, slug=slug, dir=key, dir_label=label, fuel=f, cond=cond_m, awd=key == "awd", brand=brand_,
                                body=x.get("body"), size=x.get("size"), seats=x.get("seats"), china=x.get("china_name"),
                                desc=x.get("desc"), points=x.get("points") or [], src=photo, stem=Path(m["photo"]).stem))
    return out


def model_imgs(m):
    webp(m["src"], IMG / "m" / f'{m["stem"]}_c.webp', 720, 74)
    webp(m["src"], IMG / "m" / f'{m["stem"]}.webp', 1400, 78)


def model_card(m, vt=True):
    sp = " · ".join(x for x in (m["engine"], m["power"]) if x)
    tag = m["dir_label"] if m["dir"] != "fwd" else (m.get("body") or "Бензин").capitalize()
    return (f'<a class="card" href="{u("katalog/" + m["slug"] + "/")}"{" data-vt" if vt else ""} data-cat="{m["dir"]}" data-fuel="{m["fuel"]}" data-feat="{"awd" if m["awd"] else ""}" data-body="{E(m.get("body") or "")}"'
            f' data-brand="{E(m["brand"])}" data-price="{lo_price(m)}" data-name="{E(m["name"])}" data-q="{E((m["name"] + " " + (m.get("china") or "") + " " + m["plant"]).lower())}">'
            f'<div class="im"><img src="{u("img/m/" + m["stem"] + "_c.webp")}" alt="{E(m["name"])}" loading="lazy" width="720" height="424"><span class="tag">{E(tag)}</span></div>'
            f'<div class="t"><h3>{E(m["name"])}</h3><div class="sp">{E(sp)}</div>'
            f'<div class="pr{" pr2" if "bu_label" in m else ""}">{price_html(m)}<small>ориентир под ключ</small></div></div></a>')


# ---------- данные: машины из КП ----------

# Электро и EREV с льготным утильсбором — только модели, у которых 30-мин мощность ниже порога подтверждена (Юрий 27.10.2026):
# Q05 — 74 л.с. в ЭПТС ввезённых, Yuan UP 301 — экспертное заключение 35 кВт, A06 — мотор как у Q05, Aion Y Plus 70 — решение Юрия 23.09.
# Toyota bZ3X не прошла: 额定 45 кВт, а по российской 30-мин ~65 кВт — утиль, вероятно, коммерческий. С коммерческим утилем идут все.
UTIL_OK = ("changan qiyuan q05", "changan qiyuan a06", "gac aion y plus", "byd yuan up")


def util_ok(c):
    if c.get("kind") not in ("ev", "erev"):
        return True
    rec = next((v for k, v in c["price"]["lines"] if k.startswith("Утилизац")), 0)
    return rec > 5_200 or c["title"].lower().startswith(UTIL_OK)


def load_kp(rates):
    """Машины из КП: июнь–сентябрь — new/data/kp_cars.json, с 06.10.2026 — сделки kp_v3 «Авто» (kp_deals.py, каждое утро
    и при каждой сборке берутся все, новые — сразу; Юрий 26.10.2026). Одна машина в обоих списках — по сделке.
    И объявления che168, по 5 в день (che_feed.py, data/che_cars.json; Юрий 26.10.2026)."""
    p = DATA / "kp_cars.json"
    spec = importlib.util.spec_from_file_location("mtk_price", NEW / "price.py")
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    import kp_deals
    deals = kp_deals.load(slugify)
    key = lambda c: (re.sub(r"[^a-z0-9]", "", c["title"].lower()), c.get("year"), c.get("mileage_km"))
    seen = {key(c) for c in deals}
    allold = json.loads(p.read_text()) if p.exists() else []
    was = {key(c): c["slug"] for c in allold}                  # та же машина была в старом списке — адрес страницы прежний
    old = [c for c in allold if key(c) not in seen]
    slugs = {c["slug"] for c in old}
    for c in deals:
        c["slug"] = was.get(key(c), c["slug"])
    extra = json.loads((DATA / "models.json").read_text()) if (DATA / "models.json").exists() else {}
    for c in deals:
        while c["slug"] in slugs:
            c["slug"] += "-2"
        slugs.add(c["slug"])
        c["body"] = (extra.get(c.get("catalog_name") or "") or {}).get("body")
    che = json.loads((DATA / "che_cars.json").read_text()) if (DATA / "che_cars.json").exists() else []   # объявления che168 (che_feed.py)
    cars = [c for c in old + deals + che if not c.get("year") or c["year"] >= MIN_YEAR]
    for c in cars:
        r = (pm.calc_deal if c.get("deal") else pm.calc)(c, rates["vtb"], rates["cny"], rates["eur"], TODAY)
        c["price"] = r
        c["total"] = r["total"]
        c["fuel_key"] = {"ice": "petrol", "hybrid": "hybrid", "ev": "ev", "erev": "erev"}.get(c.get("kind"), "petrol")
    cars = [c for c in cars if util_ok(c)]
    cars.sort(key=lambda c: c["total"])
    return cars


def card_img(src, dst, W=720, H=424):
    """Фото карточки 17:10 без обрезанной машины (Юрий 27.10.2026): горизонтальное фото (1,3–2,0) — по центру во весь кадр,
    вертикальное, квадратное или слишком широкое — целиком по центру, по краям то же фото, размытое и затемнённое."""
    from PIL import ImageFilter, ImageEnhance
    dst = Path(dst)
    if dst.exists() and dst.stat().st_mtime >= Path(src).stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    r = im.width / im.height
    cover = lambda x: x.resize((max(W, round(H * r)), max(H, round(W / r))), Image.LANCZOS)
    if 1.3 <= r <= 2.0:
        c = cover(im)
        out = c.crop(((c.width - W) // 2, (c.height - H) // 2, (c.width - W) // 2 + W, (c.height - H) // 2 + H))
    else:
        c = cover(im)
        bg = c.crop(((c.width - W) // 2, (c.height - H) // 2, (c.width - W) // 2 + W, (c.height - H) // 2 + H)).filter(ImageFilter.GaussianBlur(26))
        out = ImageEnhance.Brightness(bg).enhance(0.72)
        fg = im.copy()
        fg.thumbnail((W, H), Image.LANCZOS)
        out.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    out.save(dst, quality=74, method=6)


def kp_imgs(c):
    d = IMG / "kp" / c["slug"]
    ph = [Path(x) for x in c.get("photos", []) if Path(x).exists()]
    c["imgs"] = []
    for i, src in enumerate(ph, 1):
        webp(src, d / f"{i}.webp", 1400, 72)
        webp(src, d / f"t{i}.webp", 320, 66)
        c["imgs"].append(i)
    if ph:                                                       # карточка 17:10 — машина целиком, без обрезки (Юрий 27.10.2026)
        card_img(ph[0], d / "k.webp")
        if (d / "c.webp").exists():
            (d / "c.webp").unlink()
    c["card"] = "k.webp"
    if not ph and d.exists():                                    # исходники пропали — страница остаётся с уже сделанными фото
        c["imgs"] = sorted(int(x.stem) for x in d.glob("*.webp") if x.stem.isdigit())
        c["card"] = "k.webp" if (d / "k.webp").exists() else "c.webp"
        return
    for x in (d.glob("*.webp") if d.exists() else []):          # фото сверх нынешних (в сделке их стало меньше)
        n = x.stem.lstrip("t")
        if n.isdigit() and int(n) > len(ph):
            x.unlink()


def kp_line(c):
    bits = []
    if c.get("mileage_km") is not None:
        bits.append(f'{c["mileage_km"]:,} км'.replace(",", " "))
    if c.get("kind") in ("ev", "erev"):
        if c.get("power_hp"):
            bits.append(f'{c["power_hp"]} л.с.')
        if c.get("range_km"):
            bits.append(f'{c["range_km"]} км хода')
    else:
        if c.get("volume_cc"):
            bits.append(f'{c["volume_cc"]} см³')
        if c.get("power_hp"):
            bits.append(f'{c["power_hp"]} л.с.')
    bits.append(c.get("fuel_label") or FUEL_RU.get(c["fuel_key"], ""))
    if c.get("drive"):
        bits.append(c["drive"] + " привод")
    return ", ".join(b for b in bits if b)


def che_date(c):
    return ddmm(date.fromisoformat(c["che"]["added"]))


def kp_card(c, vt=True):
    """Карточка машины из КП: без города выдачи (Юрий 26.10.2026 — доставляем в любой город России)."""
    return (f'<a class="card" href="{u("avto/" + c["slug"] + "/")}"{" data-vt" if vt else ""} data-fuel="{c["fuel_key"]}" data-feat="{"awd" if c.get("awd") else ""}"'
            f' data-brand="{E(c.get("brand") or "")}" data-price="{c["total"]}" data-year="{c.get("year") or 0}" data-km="{c.get("mileage_km") or 0}" data-pop="{c.get("pop", 0)}"'
            f' data-name="{E(c["title"])}" data-q="{E((c["title"] + " " + (c.get("brand") or "")).lower())}">'
            f'<div class="im"><img src="{u("img/kp/" + c["slug"] + "/" + c.get("card", "k.webp"))}" alt="{E(c["title"])}" loading="lazy" width="720" height="424">'
            + (f'<span class="tag">Объявление в&nbsp;Китае от&nbsp;{che_date(c)}</span>' if c.get("source") == "che168" else "") + '</div>'
            f'<div class="t"><h3>{E(c["title"])} <span class="yr">{c.get("year") or ""}</span></h3><div class="sp">{E(kp_line(c))}</div>'
            f'<div class="pr">{rub(c["total"])}<small>под ключ на&nbsp;{ddmm(TODAY)}</small></div></div></a>')


# ---------- общие блоки ----------
# шаги: номер, заголовок, текст, платёж, фото, бесплатный (зелёный). 01 и 02 — бесплатные подбор и видеоосмотр, как в КП (Юрий 26.10.2026)
STEPS = [
    ("01", "Бесплатный подбор автомобиля", "Выбираете модель из каталога или предлагаете свою, называете бюджет. Мы бесплатно ищем оптимальный вариант и присылаем несколько предложений на выбор.", None, None, True),
    ("02", "Бесплатный видеоосмотр", "Когда Вы выбрали конкретную машину, бесплатно присылаем видео: замер толщиномером по всему кузову, салон и крупным планом всё, что требует внимания. "
     "Проверяем историю машины по базам Китая. Дополнительно можно заказать независимый осмотр специалистом с отчётом за 1&nbsp;300&nbsp;¥.", None, "k_1", True),
    ("03", "Договор и оплата", "Высылаем договор, контракт и инвойс. Оплата через банк ВТБ.", "Оплата 1 — предоплата 50 000 ₽<br>Оплата 2 — автомобиль, доставка, погрузка и комиссия банка", None, False),
    ("04", "Доставка", "Погрузка на автовоз, доставка до границы и дальше — в Ваш город.", None, "d_yaris_1", False),
    ("05", "Документы", "Оформляем СБКТС и электронный ПТС.", None, None, False),
    ("06", "Таможня", "Растаможиваем автомобиль: помогаем оплатить пошлину и сборы, подсказываем суммы и реквизиты.", "Оплата 3 — пошлина, сборы, СВХ и оформление документов", "d_coolray_1", False),
    ("07", "Выдача", "Получаете ключи, ЭПТС и таможенные документы и ставите машину на учёт.", "Оплата 4 — остаток 40 000 ₽ за подбор и сопровождение", "d_xrv_1", False),
]
DELIV = [("xrv", "Honda XR-V 1.5 Comfort", "2022 · 33 889 км · бензин, 131 л.с.", "Санкт-Петербург", 1769998),
         ("q05", "Changan Qiyuan Q05 506Max", "2025 · 7 000 км · электро, 163 л.с.", "Ижевск", 2214339),
         ("yaris", "Toyota Yaris L 1.5", "2022 · 66 000 км · бензин, 107 л.с.", "Пермь", 1390144),
         ("coolray", "Geely Coolray 1.4T", "2022 · 13 500 км · бензин, 141 л.с.", "Санкт-Петербург", 1247044)]


def nbs(s):
    return s.replace(" — ", "&nbsp;— ").replace(" 000", "&nbsp;000").replace(" ₽", "&nbsp;₽")


def steps_track():
    out = []
    for n, h, p, pay, ph, free in STEPS:
        fr = " free" if free else ""
        if ph:
            out.append(f'<div class="step ph{fr}"><img src="{u("img/" + ph + ".webp")}" alt="" loading="lazy"><div><div class="n">{n}</div><h3>{h}</h3><p>{nbs(p)}</p></div></div>')
        else:
            out.append(f'<div class="step{fr}"><div class="n">{n}</div><h3>{h}</h3><p>{nbs(p)}</p>' + (f'<div class="pay">{nbs(pay)}</div>' if pay else "") + '</div>')
    return "".join(out)


def deliv_cards():
    return "".join(
        f'<article class="dc rv"><img src="{u("img/d_" + k + "_1.webp")}" alt="{E(n)}" loading="lazy"><img src="{u("img/d_" + k + "_2.webp")}" alt="" loading="lazy">'
        f'<div class="t"><div><h3>{n}</h3><div class="sp">{s} · выдача: {c}</div></div><div class="pr">{rub(p)}<small>итог под ключ</small></div></div></article>'
        for k, n, s, c, p in DELIV)


def team_cards():
    out = []
    for p in TEAM:
        bt = f'<a href="https://t.me/{p["tg"]}">Telegram</a><a href="https://wa.me/{p["wa"]}">WhatsApp</a>'
        if p["mx"] and p["mx"] != "phone":
            bt += f'<a href="{MAX_HREF}">MAX</a>'
        tel = "+" + re.sub(r"\D", "", p["tel"])
        mx = '<span class="mx">Этот же номер — в MAX</span>' if p["mx"] == "phone" else ""
        out.append(f'<div class="who rv"><img src="{u("img/" + p["img"] + ".webp")}" alt="{p["name"]}" loading="lazy" width="96" height="96">'
                   f'<h3>{p["name"]}</h3><div class="r">{p["note"]}</div><a class="ph" href="tel:{tel}">{nb(p["tel"])}</a>{mx}<div class="bt">{bt}</div></div>')
    return "".join(out)


CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
# этапы оплаты: перед ними зелёный шаг без цифры — бесплатные подбор и видеоосмотр, как в КП (Юрий 26.10.2026)
PAYS = f"""<div class="pays" id="pays">
<div class="pay4 free"><div class="c">{CHECK}</div><h3>Бесплатно</h3><ul><li><b>Подбор автомобиля</b>: поиск оптимального варианта, несколько предложений на&nbsp;выбор</li><li><b>Видеоосмотр</b> после выбора конкретного автомобиля</li></ul></div>
<div class="pay4"><div class="c">1</div><h3>Предоплата</h3><div class="s">50&nbsp;000&nbsp;₽</div><p>При подписании договора&nbsp;— в&nbsp;счёт подбора и&nbsp;сопровождения сделки (всего 90&nbsp;000&nbsp;₽).</p></div>
<div class="pay4"><div class="c">2</div><h3>Оплата автомобиля</h3><div class="s">По&nbsp;курсу ВТБ</div><p>Через ВТБ по&nbsp;контракту и&nbsp;инвойсу. С&nbsp;этой оплаты автомобиль Ваш.</p><ul><li><b>Автомобиль</b> в&nbsp;Китае</li><li><b>Доставка</b> автовозом в&nbsp;Россию</li><li><b>Погрузка</b> и&nbsp;доставка по&nbsp;Китаю</li><li><b>Комиссия банка</b> 2%</li></ul></div>
<div class="pay4"><div class="c">3</div><h3>Таможня</h3><div class="s">По&nbsp;прибытии</div><p>Пошлина, сборы, склад временного хранения и&nbsp;оформление документов.</p><ul><li><b>Утильсбор</b> льготный: 3&nbsp;400&nbsp;₽ до&nbsp;3&nbsp;лет, 5&nbsp;200&nbsp;₽ от&nbsp;3 до&nbsp;5</li><li><b>СБКТС и ЭПТС</b>, растаможка&nbsp;— 80&nbsp;000&nbsp;₽</li><li><b>СВХ</b>&nbsp;— 20&nbsp;500&nbsp;₽ за&nbsp;первые сутки, обычно их&nbsp;хватает</li></ul></div>
<div class="pay4"><div class="c">4</div><h3>При выдаче</h3><div class="s">40&nbsp;000&nbsp;₽</div><p>Остаток за&nbsp;подбор и&nbsp;сопровождение. Получаете ключи, ЭПТС и&nbsp;таможенные документы.</p></div>
</div>"""


# образцы документов сделки на «Как купить» — превью из КП «Авто» (kp_v3/docs_light: данные покупателя и продавца скрыты), Юрий 27.10.2026
DOCS = [("kontrakt", "Контракт купли-продажи с&nbsp;продавцом в&nbsp;Китае", "Договор_p1"), ("dop-soglashenie", "Дополнительное соглашение к&nbsp;контракту", "ДопСоглашение_p1"),
        ("invoys", "Инвойс продавца", "Инвойс_p1"), ("chek-vtb", "Чек об&nbsp;оплате через ВТБ", "Чек_p1")]


# ---------- шапки разделов: справа видео, фото или небольшой интерактив по теме (Юрий 26.10.2026) ----------
PH_VIS = {"katalog": ("video", "ph_katalog", "fit"), "premium": ("video", "ph_premium", "zoom"),   # ролики syntx.ai от Юрия; сборка — tools/ph_video.py (27.10)
          "vydannye": ("studio", "ph/vydannye.svg", "anim"), "mopedy": ("studio", "ph/mopedy.svg", "anim"),   # фото Юрия из Nano Banana на синем фоне (27.10); въезжают в кадр — ph_anim.py (27.10, ночь)
          "voprosy": ("img", "road.webp"), "kontakty": ("studio", "ph/kontakty.webp")}            # «Авто в Китае» — витрина ph_show() (Юрий 27.10)


def phv(key):
    kind, src, *cls = PH_VIS[key]
    if kind == "video":
        vd = OUT / "assets" / "video"
        if not (vd / f"{src}.mp4").exists():
            return ""
        vv = lambda n: u(f"assets/video/{n}") + "?v=" + hashlib.md5((vd / n).read_bytes()).hexdigest()[:8]
        return (f'<div class="{" ".join(["phv", "vid", *cls])}" aria-hidden="true"><video muted loop playsinline preload="none" poster="{vv(src + ".webp")}"'
                f' data-src="{vv(src + ".mp4")}" data-src-m="{vv(src + "_m.mp4")}"></video></div>')
    if not (IMG / src).exists():
        return ""
    if "anim" in cls:                                    # въезд в кадр начинается, когда картинка загрузилась (s.css .phv.anim); SVG грузит s.js — каждый раз заново
        v = hashlib.md5((IMG / src).read_bytes()).hexdigest()[:8]
        return (f'<div class="phv {kind} anim" aria-hidden="true"><img data-svg="{u("img/" + src)}?v={v}" alt="" decoding="async" onload="this.classList.add(\'go\')">'
                f'{PH_TAGS.get(key, "")}</div>')
    return f'<div class="phv{" " + kind if kind != "img" else ""}" aria-hidden="true"><img src="{u("img/" + src)}" alt="" decoding="async"></div>'


PH_TAGS = {"mopedy": '<ul class="mtags"><li>Без ОСАГО</li><li>Права M, A, B или&nbsp;C</li><li>Без учёта в&nbsp;ГИБДД</li><li>Ездить можно с&nbsp;16&nbsp;лет</li></ul>'}   # плашки по очереди вокруг мопеда (Юрий 27.10.2026, вариант 3)
FCLOSE = ('<div class="fxw"><button class="fx" type="button" data-fclose aria-label="Закрыть фильтры"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
          '<path d="M6 6l12 12M18 6L6 18"/></svg></button></div>')   # крестик панели фильтров на телефоне (Юрий 27.10.2026)


POPULAR = {"mazda", "kia", "toyota", "geely", "honda", "hyundai", "haval", "chery", "changan", "nissan"}   # вперёд в «Авто в Китае» (Юрий 27.10.2026)


def added(c):
    """Когда машина появилась на сайте: объявление che168 — день добавления, сделка «Авто» — дата КП."""
    return (c.get("che") or {}).get("added") or c.get("kp_date_iso") or ""


def pop_rank(kp):
    """Сортировка «Популярные» (Юрий 27.10.2026): сначала популярные марки, затем остальные; внутри — каждый день новый порядок."""
    rnd = random.Random("pop" + TODAY.isoformat())
    hot = [c for c in kp if (c.get("brand") or "").lower() in POPULAR]
    rest = [c for c in kp if c not in hot]
    rnd.shuffle(hot)
    rnd.shuffle(rest)
    for i, c in enumerate(hot + rest):
        c["pop"] = i
    return hot + rest


def ph_show(kp):
    """«Авто в Китае»: живая витрина справа — машины, добавленные последними, карточки сменяют друг друга (Юрий 27.10.2026;
    счётчик «N машин, +N сегодня» убран — Юрий 27.10.2026, вечер)."""
    today = TODAY.isoformat()
    fresh = sorted(kp, key=lambda c: (added(c), c["total"]), reverse=True)[:8]
    when = lambda c: "Новая сегодня" if added(c) == today else f'Добавлена {ddmm(date.fromisoformat(added(c)))}' if added(c) else "В&nbsp;продаже"
    cards = "".join(f'<a class="shc" href="{u("avto/" + c["slug"] + "/")}"><img src="{u("img/kp/" + c["slug"] + "/" + c.get("card", "k.webp"))}" alt="{E(c["title"])}" loading="lazy">'
                    f'<div class="t"><span class="nw">{when(c)}</span><h3>{E(c["title"])} <i>{c.get("year") or ""}</i></h3><b>{rub(c["total"])}</b><small>под ключ на&nbsp;{ddmm(TODAY)}</small></div></a>'
                    for c in fresh)
    return f'<div class="phshow"><div class="shstack" data-show>{cards}</div></div>'


def ph_route():
    """«Как купить»: маршрут Китай → граница → ваш город, 45–65 дней — по линии едет машинка капотом вперёд (Юрий 27.10.2026: бирюзовый вместо жёлтого;
    рисунок отражён — капот слева, а движение по линии вправо). С 28.10.2026 весь маршрут зеркально (Юрий: Китай восточнее России) —
    путь, точки и машинка в группе с отражением, Китай справа внизу, «Ваш город» слева; подписи не отражаются."""
    path = "M40 230 C 170 120, 300 270, 430 170 S 640 60, 720 110"
    return f"""<div class="phroute" aria-hidden="true"><svg viewBox="0 0 760 300" fill="none">
<defs><linearGradient id="rtg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3fe8c8"/><stop offset=".6" stop-color="#2fd2e6"/><stop offset="1" stop-color="#7fd3ff"/></linearGradient></defs>
<g transform="matrix(-1 0 0 1 760 0)"><path d="{path}" class="rt0"/><path d="{path}" class="rt1" stroke="url(#rtg)"/>
<g class="nd"><circle cx="40" cy="230" r="9"/><circle cx="430" cy="170" r="9"/><circle cx="720" cy="110" r="11"/></g>
<g class="car"><g transform="scale(-1.4 1.4) translate(0 -9)"><path class="bd" d="M-23 4v-6q1-4 6-4.5l8-1 6-6q2-1.5 5-1.5h8q3 0 5 3l4 4.5q5 1 5 5v6.5z"/>
<path class="gl" d="M-6.5-7.5l4.5-5h6v5zM5.5-7.5v-5h4q2 0 3 1.5l2.5 3.5z"/>
<circle class="wh" cx="-12" cy="4.5" r="4.6"/><circle class="wh" cx="12.5" cy="4.5" r="4.6"/></g>
<animateMotion dur="7s" repeatCount="indefinite" rotate="auto" keyPoints="0;1;1" keyTimes="0;.85;1" calcMode="linear" path="{path}"/></g></g>
<text x="720" y="272" text-anchor="middle">Китай</text><text x="330" y="212" text-anchor="middle">Граница</text><text x="40" y="70" text-anchor="middle">Ваш город</text>
</svg><div class="rtd"><b>45–65</b> дней от&nbsp;оплаты до&nbsp;выдачи</div></div>"""


def calc_data(rates):
    """Данные калькулятора под ключ: страница «Калькулятор» (data-calc) и бот заявок (new/data/bot_calc.json) считают по одним цифрам."""
    spec = importlib.util.spec_from_file_location("auto_china_calc_t", AC / "calc.py")   # таблицы сбора и пошлины «Авто»
    AC_CALC = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(AC_CALC)
    import price as PR
    tab = lambda t: sorted([k, v] for k, v in t.items() if k != "above")
    rec = json.loads((AC / "new_recycle.json").read_text())["individual"]
    d = {"vtb": rates["vtb"], "cny": rates["cny"], "eur": rates["eur"], "deliv": PR.DELIVERY_CNY, "load": PR.LOADING_CNY, "bank": PR.BANK_FEE,
         "fee": tab(AC_CALC.CUSTOM_FEE_TABLE), "feeTop": AC_CALC.CUSTOM_FEE_TABLE["above"],
         "lt3": tab(AC_CALC.PHYS_LESS_THAN_3), "lt3Top": AC_CALC.PHYS_LESS_THAN_3["above"],
         "gt3": tab(AC_CALC.PHYS_MORE_THAN_3), "gt3Top": [3.6, 5.7],   # свыше 3000 см³: 3–5 лет 3,6 €/см³, старше 5 — 5,7 (Решение ЕЭК № 107; в calc.py «Авто» 5,7 и для 3–5)
         "rec": {k: {a: [[r["max_kw"], r["coef"]] for r in v[a]] for a in ("less_3", "over_3")} for k, v in rec.items()},
         "akc": PR.AKCIZ, "svh": PR.TARIFF["svh"], "clr": PR.CLEARANCE, "svc": PR.TARIFF["services"], "k30": 0.45,
         "u27": PR.UTIL_2027.isoformat(), "arr": PR.ARRIVAL_DAYS[1]}   # с 2027 коммерческий утиль +10%, если машина может прийти в 2027 (Юрий 27.10.2026)
    return d


def ph_calc(rates):
    """«Стоимость»: калькулятор (Юрий 27.10.2026, подробнее): цена в Китае в юанях, двигатель, возраст, объём и мощность → ориентир под ключ
    и расшифровка. Как в КП «Авто»: один инвойс «машина + доставка», таможенная стоимость — он по курсу ЦБ (Юрий 29.10.2026, было без доставки); бензин и гибриды (HEV, PHEV) —
    пошлина по возрасту (до 3 лет — % или €/см³, 3–5 и старше 5 — €/см³), утильсбор по объёму и мощности; электро и EREV — пошлина 15%,
    акциз и утильсбор по 30-минутной мощности (нет в документах — 0,45 × максимальной), НДС 22% с акцизом в базе. Таблицы сборов,
    пошлин и утильсбора — calc.py и new_recycle.json «Авто», акциз — new/price.py (ставки 2026, «Авто» 27.10.2026)."""
    import price as PR
    d = calc_data(rates)
    return f"""<form class="phcalc" data-calc='{json.dumps(d)}' onsubmit="return false"><h3>Калькулятор</h3>
<label>Цена машины в&nbsp;Китае, ¥ — без&nbsp;доставки<input type="number" name="y" value="80000" min="10000" step="1000" inputmode="numeric"></label>
<p class="chint">Доставка автовозом {nf(PR.DELIVERY_CNY)}&nbsp;¥ и&nbsp;погрузка по&nbsp;Китаю уже включены&nbsp;— строками в&nbsp;«Подробнее». Пошлина и&nbsp;сбор&nbsp;— от&nbsp;суммы инвойса: цена машины вместе с&nbsp;доставкой, как в&nbsp;КП.</p>
<div class="two"><label>Двигатель<select name="t"><option value="ice">Бензин, гибрид</option><option value="ev">Электро</option><option value="erev">Гибрид EREV</option></select></label>
<label>Возраст<select name="a"><option value="0">До&nbsp;3 лет</option><option value="1" selected>3–5 лет</option><option value="2">Старше 5 лет</option></select></label></div>
<div class="two"><label class="cc">Объём, см³<input type="number" name="cc" value="1500" min="600" step="1" inputmode="numeric"></label>
<label><span data-pl>Мощность</span><span class="pw"><input type="number" name="p" value="150" min="20" step="1" inputmode="numeric"><select name="u" aria-label="Единицы"><option value="hp">л.с.</option><option value="kw">кВт</option></select></span></label></div>
<p class="chint" data-hint></p>
<div class="out"><small>Ориентир под&nbsp;ключ</small><b data-total>—</b><span class="ut" data-ut></span></div>
<div class="warn" data-warn hidden><p data-wt></p><a class="btn w sm" href="{u("kontakty/")}">Написать нам</a><a class="btn o sm" href="{CHANNEL}">Telegram-канал</a></div>
<details class="brkd"><summary>Подробнее</summary><table class="brk" data-brk></table></details>
<p>По&nbsp;курсу ВТБ на&nbsp;{ddmm(TODAY)}. Точную сумму на&nbsp;конкретный автомобиль посчитаем при&nbsp;подборе.</p></form>"""


def faq_items(items):
    """Ответ — абзацы; «more»: [адрес, текст] — ссылка под ответом (образцы документов на «Как купить», Юрий 27.10.2026)."""
    more = lambda q: f'<p><a class="more" href="{u(q["more"][0])}">{E(q["more"][1])} <span class="ar">→</span></a></p>' if q.get("more") else ""
    return "".join(f'<details class="qa"><summary>{E(q["q"])}</summary><div class="a">{"".join("<p>" + E(x) + "</p>" for x in q["a"].split(chr(10)) if x.strip())}{more(q)}</div></details>' for q in items)


def faq_ld(items):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in items]}


FIN_M_TOP = 520                                        # фон нижнего блока на телефоне: срезано небо сверху, пикселей исходника (Юрий 27.10.2026)


def fin_block():
    return f"""<section class="fin"><picture><source media="(max-width:760px)" srcset="{u("img/fin_m.webp")}"><img class="bg" id="finbg" src="{u("img/road.webp")}" alt="" loading="lazy"></picture>
<div class="wrap"><h2 class="rv">Ваш автомобиль<br>из&nbsp;Китая. Под&nbsp;ключ.</h2><p class="rv d1">Новые машины, подборки и&nbsp;выданные автомобили&nbsp;— в&nbsp;нашем Telegram-канале.</p>
<div class="btns rv d2"><a class="btn w" href="{CHANNEL}">Telegram-канал <span class="ar">→</span></a><a class="btn o" href="{u("kontakty/")}">Написать специалисту</a></div></div></section>"""


ORG = {"@context": "https://schema.org", "@type": "AutoDealer", "name": "МТК Восток-Авто", "alternateName": "Международная транспортная компания «Восток-Авто»",
       "url": SITE + "/", "logo": SITE + BASE + "img/logo192.webp", "foundingDate": "2016",
       "description": "Подбор, проверка, доставка и растаможка новых и б/у автомобилей из Китая под ключ для частных покупателей.",
       "areaServed": "RU", "telephone": TEAM[0]["tel"], "sameAs": [CHANNEL]}


# ---------- страницы ----------
def home(models, kp, rates, faq):
    decks = []
    for i, (key, label, cat, sec, _) in enumerate(DIRS):
        ms = [m for m in models if m["dir"] == key]
        deck_img(sec, IMG / f"sec{sec}.webp", 2200, 74)
        deck_img(sec, IMG / f"sec{sec}_m.webp", 1100, 74)
        vid = ""
        if (OUT / "assets" / "video" / f"deck{sec}.mp4").exists():   # живой блок: ролик из syntx.ai поверх фото (Юрий 18.10)
            vv = lambda n: u(f"assets/video/{n}") + "?v=" + hashlib.md5((OUT / "assets" / "video" / n).read_bytes()).hexdigest()[:8]   # новый ролик — новый адрес, мимо кэша
            vid = f'<video class="dv" muted loop playsinline preload="none" aria-hidden="true" data-src="{vv(f"deck{sec}.mp4")}" data-src-m="{vv(f"deck{sec}_m.mp4")}"></video>'
        names = "".join(f"<span>{E(m['name'])}</span>" for m in ms[:6])
        lo = min(lo_price(m) for m in ms)
        decks.append(f'<section class="deck"><picture><source media="(max-width:760px)" srcset="{u(f"img/sec{sec}_m.webp")}"><img src="{u(f"img/sec{sec}.webp")}" alt="{label}" loading="lazy"></picture>{vid}'
                     f'<div class="wrap"><div class="n">{i + 1:02d} / 04 · {len(ms)} {plural(len(ms), "модель", "модели", "моделей")}{" · б/у и новые" if any("bu_label" in m for m in ms) else ""}</div><h2>{label}</h2><p>{DIR_TEXT[key]}</p>'
                     f'<div class="ms">{names}</div><div class="row"><a class="btn w" href="{u("katalog/?cat=" + key)}">Смотреть {len(ms)} {plural(len(ms), "модель", "модели", "моделей")} <span class="ar">→</span></a>'
                     f'<div class="pr">от {mln(lo)} млн ₽<small>ориентир под ключ</small></div></div></div></section>')
    reel = ""
    if kp:
        pick = random.Random(TODAY.isoformat()).sample(kp, min(12, len(kp)))   # каждый день свой набор и порядок, в браузере ещё перемешиваются (Юрий 26.10.2026)
        reel = f"""<section class="sec dark" id="avto">
<div class="wrap shead"><div><p class="kick l rv">Авто в Китае</p><h2 class="h2 rv d1">Реальные машины<br><em>с&nbsp;ценой на&nbsp;сегодня</em></h2>
<p class="lead rv d2">Конкретные автомобили, которые мы нашли и&nbsp;посчитали для&nbsp;клиентов. Цена под&nbsp;ключ пересчитывается каждый день по&nbsp;курсу юаня.</p></div>{ARROWS.format(id="reel1")}</div>
<div class="reel" id="reel1" data-shuffle>{"".join(kp_card(c) for c in pick)}</div>
<div class="wrap"><a class="more" href="{u("avto/")}">Все {len(kp)} {plural(len(kp), "машина", "машины", "машин")} с&nbsp;ценой <span class="ar">→</span></a></div></section>"""
    faq5 = [q for q in faq if not q.get("confirm")][:6]
    body = f"""
<section class="hero" id="top">
  <video class="hv" id="hv" autoplay muted loop playsinline preload="auto" poster="{u("assets/video/yu7_hero.webp")}" aria-hidden="true">
    <source media="(max-width:760px)" src="{u("assets/video/yu7_hero_m.mp4")}" type="video/mp4"><source src="{u("assets/video/yu7_hero.mp4")}" type="video/mp4"></video><div class="shade"></div>
  <div class="wrap hc" id="hc">
    <p class="kick l">МТК Восток-Авто</p>
    <h1>Автомобили из&nbsp;Китая.<br><span>Под ключ.</span></h1>
    <p class="sub"><span>Новые и&nbsp;б/у под&nbsp;льготный утильсбор. Подбираем, проверяем,</span> <span>везём, растаможиваем и&nbsp;передаём Вам с&nbsp;электронным ПТС.</span></p>
    <div class="btns"><a class="btn w" href="{u("katalog/")}">Смотреть каталог <span class="ar">→</span></a><a class="btn o" href="{u("avto/")}">Авто в Китае</a></div>
    <a class="rate" href="{u("kalkulyator/")}"><i></i>Курс юаня для расчёта на&nbsp;{ddmm(TODAY)}: <b>{f"{rates['vtb']:.2f}".replace(".", ",")}&nbsp;₽</b></a>
  </div>
  <div class="hint" aria-hidden="true"></div>
</section>
<section class="intro"><div class="wrap">
  <p class="words" id="words">Автомобиль из&nbsp;Китая&nbsp;— это не&nbsp;только цена в&nbsp;объявлении. Это *проверка,* *договор,* *доставка,* *таможня* и&nbsp;*документы.* Всё это&nbsp;— наша работа: от&nbsp;выбора модели до&nbsp;выдачи ключей.</p>
  <div class="stats">
    <div class="rv"><b>45–65</b><span>дней от&nbsp;оплаты до&nbsp;выдачи&nbsp;— ориентир по&nbsp;договору</span></div>
    <div class="rv d1"><b data-n="{len(models)}">{len(models)}</b><span>моделей в&nbsp;каталоге под&nbsp;льготный утильсбор</span></div>
    <div class="rv d2"><b data-n="{len(kp) or 7}">{len(kp) or 7}</b><span>{"машин из&nbsp;Китая с&nbsp;ценой на&nbsp;сегодня" if kp else "этапов от&nbsp;выбора до&nbsp;постановки на&nbsp;учёт"}</span></div>
    <div class="rv d3"><b data-n="2016" data-from="1990">2016</b><span>с&nbsp;этого года работаем с&nbsp;Китаем</span></div>
  </div>
</div></section>
<div class="decks">{"".join(decks)}</div>
{reel}
<section class="grow" id="grow"><div class="st"><div class="fr" id="fr">
  <picture><source media="(max-width:760px)" srcset="{u("img/road_m.webp")}"><img src="{u("img/road.webp")}" alt="Дорога из Китая в Россию" loading="lazy"></picture>
  <div class="gt wrap"><p class="kick l">Доставка</p><h2>Из&nbsp;Китая&nbsp;—<br>в&nbsp;ваш город</h2><p>Доставим в&nbsp;любой город России.</p></div>
</div></div></section>
<section class="how" id="how"><div class="st">
  <div class="wrap hh"><div><p class="kick">Как проходит сделка</p><h2 class="h2">Семь шагов<br>от&nbsp;выбора <em>до&nbsp;ключей</em></h2></div>
  <p>Срок от&nbsp;оплаты до&nbsp;выдачи&nbsp;— обычно 45–65&nbsp;дней. <a class="more" href="{u("kak-kupit/")}">Подробно <span class="ar">→</span></a></p></div>
  <div class="track" id="track">{steps_track()}</div><div class="wrap"><div class="prog" id="prog"><i></i></div></div>
</div></section>
<section class="sec"><div class="wrap">
  <p class="kick rv">Стоимость</p><h2 class="h2 rv d1">Одна цена&nbsp;— <em>под&nbsp;ключ</em></h2>
  <p class="lead rv d2">Автомобиль, доставка, растаможка, документы и&nbsp;наши услуги. Оплата в&nbsp;четыре этапа по&nbsp;договору, без&nbsp;скрытых платежей.</p>
  {PAYS}
  <p class="note rv"><a class="more" href="{u("stoimost/")}">Из&nbsp;чего складывается цена и&nbsp;курс на&nbsp;сегодня <span class="ar">→</span></a></p>
</div></section>
<section class="sec bg" id="delivered"><div class="wrap">
  <div class="shead"><div><p class="kick rv">Наша работа</p><h2 class="h2 rv d1">Примеры выданных <em>автомобилей</em></h2></div><a class="more rv" href="{u("vydannye/")}">Больше выдач <span class="ar">→</span></a></div>
  <div class="dgrid">{deliv_cards()}</div>
</div></section>
<section class="sec"><div class="wrap">
  <div class="shead"><div><p class="kick rv">Вопросы</p><h2 class="h2 rv d1">Что спрашивают <em>чаще всего</em></h2></div><a class="more rv" href="{u("voprosy/")}">Все вопросы <span class="ar">→</span></a></div>
  <div class="faq rv">{faq_items(faq5)}</div>
</div></section>
<section class="sec bg" id="contacts"><div class="wrap">
  <p class="kick rv">Связаться</p><h2 class="h2 rv d1">Напишите <em>специалисту</em></h2>
  <p class="lead rv d2">Расскажите, какую машину и&nbsp;в&nbsp;какой город хотите,&nbsp;— подберём варианты и&nbsp;посчитаем стоимость под&nbsp;ключ.</p>
  <div class="tgrid">{team_cards()}</div>
</div></section>
{fin_block()}"""
    page("", "МТК Восток-Авто — автомобили из Китая под ключ: каталог, цены, доставка",
         f"Новые и б/у автомобили из Китая под льготный утильсбор: {len(models)} моделей в каталоге, реальные машины с ценой под ключ на сегодня, проверка, договор, доставка, растаможка, ЭПТС.",
         body, jsonld=[ORG, faq_ld(faq5)] if faq5 else [ORG], prio="1.0")


def catalog_page(models):
    # плитки — быстрый выбор того же, что в панели «Топливо» и «Привод» (Юрий 27.10.2026): Бензин — все бензиновые, Полный привод — все полноприводные
    to = {"ev": ("fuel", "ev"), "hyb": ("fuel", "hybrid"), "fwd": ("fuel", "petrol"), "awd": ("feat", "awd")}
    has = lambda m, f, v: (v in m["fuel"].split()) if f == "fuel" else m["awd"]
    tiles = "".join(f'<button class="tile" type="button" data-to="{to[k][0]}" data-v="{to[k][1]}" data-cat="{k}"><img src="{u(f"img/tile{sec}.webp")}" alt="" loading="lazy"><div><b>{t}</b>'
                    f'<small>{(n := sum(has(m, *to[k]) for m in models))} {plural(n, "модель", "модели", "моделей")}</small></div></button>'
                    for k, t, _, sec, _ in DIRS)
    fuels = [(k, t) for k, t in (("petrol", "Бензин"), ("hybrid", "Гибрид"), ("ev", "Электро")) if any(k in m["fuel"].split() for m in models)]
    bodies = sorted({m["body"] for m in models if m.get("body")}, key=lambda b: -sum(m.get("body") == b for m in models))
    brands = sorted({m["brand"] for m in models})
    pmax = math.ceil(max(m["from"] for m in models) / 1e5) * 1e5
    body = f"""
<section class="phead pkat">{phv("katalog")}<div class="wrap">{crumbs((None, "Каталог"))}
<h1 class="rv in">{len(models)} моделей <br class="kbr">под <em>льготный утильсбор</em></h1>
<p class="lead">Цена в&nbsp;карточке&nbsp;— ориентир под&nbsp;ключ. В&nbsp;неё входят доставка из&nbsp;Китая, таможенные платежи и&nbsp;оформление, получение СБКТС и&nbsp;электронного ПТС, подбор и&nbsp;сопровождение сделки. Точную сумму на&nbsp;конкретный автомобиль считаем по&nbsp;курсу дня. В&nbsp;каталоге только часть моделей, любую другую привезём из&nbsp;Китая под&nbsp;заказ.</p>
<div class="tiles">{tiles}</div></div></section>
<section class="sec tight"><div class="wrap lay">
<aside class="flt" aria-label="Фильтры">{FCLOSE}
<h4>Поиск</h4><input type="search" data-f="q" placeholder="Модель или марка">
<h4>Топливо</h4><div class="chips" data-f="fuel">{"".join(f'<button class="chip" type="button" data-v="{k}">{t}</button>' for k, t in fuels)}</div>
<h4>Привод</h4><div class="chips" data-f="feat"><button class="chip" type="button" data-v="awd">Только полный</button></div>
<h4>Кузов</h4><div class="chips" data-f="body">{"".join(f'<button class="chip" type="button" data-v="{E(b)}">{E(b.capitalize())}</button>' for b in bodies)}</div>
<h4>Марка</h4><select data-f="brand"><option value="">Любая</option>{"".join(f"<option>{E(b)}</option>" for b in brands)}</select>
<h4>Цена под ключ</h4><input type="range" data-f="price" min="1000000" max="{int(pmax)}" step="100000" value="{int(pmax)}"><div class="rng"><span>до</span><b data-out="price">любая</b></div>
<button class="btn ob sm reset" type="button" data-reset>Сбросить фильтры</button>
<button class="btn b sm reset fbtn" type="button" data-fopen>Показать</button>
</aside>
<div>
<div class="lhead"><span class="cnt">Найдено: <b id="cnt">{len(models)}</b></span><span style="display:flex;gap:10px"><button class="btn ob sm fbtn" type="button" data-fopen>Фильтры</button>
<select data-sort aria-label="Сортировка"><option value="price-asc">Сначала дешевле</option><option value="price-desc">Сначала дороже</option><option value="name-asc">По названию</option></select></span></div>
<div class="list" data-list>{"".join(model_card(m) for m in models)}</div>
<p class="empty" id="empty">По&nbsp;таким условиям моделей нет. <a class="more" href="#" data-reset>Сбросить фильтры</a></p>
<p class="note">Цены&nbsp;— ориентир под&nbsp;ключ: автомобиль, доставка, растаможка, документы и&nbsp;наши услуги. Пересчитаны {ddmm(TODAY)} по&nbsp;курсу юаня на&nbsp;сегодня; точную цену конкретной машины считаем при&nbsp;подборе. Доставим в&nbsp;любой город России.</p>
</div></div></section>
{fin_block()}"""
    ld = [bc_ld(("katalog/", "Каталог")),
          {"@context": "https://schema.org", "@type": "ItemList", "name": "Каталог автомобилей из Китая под льготный утильсбор",
           "itemListElement": [{"@type": "ListItem", "position": i, "url": SITE + u("katalog/" + m["slug"] + "/"), "name": m["name"]} for i, m in enumerate(models, 1)]}]
    page("katalog/", f"Каталог автомобилей из Китая под ключ — {len(models)} моделей под льготный утильсбор | МТК Восток-Авто",
         "Электромобили, гибриды, бензиновые и полноприводные машины из Китая с ценой под ключ: фильтры по кузову, марке и бюджету.",
         body, active="katalog/", jsonld=ld, prio="0.9")


def model_page(m, models, kp):
    found = [c for c in kp if c.get("catalog_name") == m["name"]]
    same = [x for x in models if x["dir"] == m["dir"] and x["slug"] != m["slug"]]
    same.sort(key=lambda x: abs(lo_price(x) - lo_price(m)))
    tags = [m["dir_label"] if m["dir"] != "fwd" else "Бензин", (m.get("body") or "").capitalize(), m["cond"], "Полный привод" if m["awd"] else None]
    if "erev" in m["fuel"]:
        tags[0] = "Электро и EREV"
    util = ("3&nbsp;400&nbsp;₽ — льготный: 30-минутная мощность мотора до&nbsp;58,84&nbsp;кВт" if m["dir"] == "ev"
            else "5&nbsp;200&nbsp;₽ — льготный: возраст 3–5 лет, до&nbsp;160&nbsp;л.с.")
    if m["dir"] != "ev" and m["cond"] == "Новый":
        util = "3&nbsp;400&nbsp;₽ — льготный: моложе 3&nbsp;лет, до&nbsp;160&nbsp;л.с."
    if m.get("bu_old"):
        util += ", у&nbsp;б/у старше 3&nbsp;лет&nbsp;— 5&nbsp;200&nbsp;₽"
    rows = [("Двигатель", E(m["engine"])), ("Мощность" + (" и запас хода" if m["dir"] == "ev" else ""), E(m["power"])),
            ("Производитель", E(m["plant"]).replace(E(m["brand"]), E(m["brand"]) + ru_brand(m["brand"]), 1)), ("Кузов", E((m.get("body") or "").capitalize()) or None),
            ("Мест", str(m["seats"]) if m.get("seats") else None), ("Состояние", m["cond"]), ("Утильсбор", util),
            ("Срок", "45–65 дней от&nbsp;оплаты до&nbsp;выдачи"), ("Цена под ключ", "<br>".join(f"{t}: {v or 'по&nbsp;запросу'}" if t else v for t, v in price_lines(m)))]
    spec = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows if v)
    desc = (f'<p class="desc">{E(m["desc"])}</p>' if m.get("desc") else
            f'<p class="desc">{E(m["name"])} — {m["dir_label"].lower()} из&nbsp;Китая под&nbsp;льготный утильсбор. Подберём конкретную машину, проверим и&nbsp;привезём под&nbsp;ключ.</p>')
    pts = "".join(f"<li>{E(p)}</li>" for p in m["points"])
    fblock = ""
    if found:
        fblock = f"""<section class="sec bg" id="found"><div class="wrap"><p class="kick rv">Авто в Китае</p>
<h2 class="h2 rv d1">{E(m["name"])}: <em>найденные машины</em></h2><p class="lead rv d2">Конкретные автомобили этой модели, которые мы нашли и&nbsp;посчитали. Цена под&nbsp;ключ&nbsp;— по&nbsp;курсу на&nbsp;{ddmm(TODAY)}.</p>
<div class="grid" style="margin-top:46px">{"".join(kp_card(c) for c in found[:6])}</div>
{f'<p class="note"><a class="more" href="{u("avto/?q=" + E(m["name"].split()[1].lower()))}">Все машины этой модели <span class="ar">→</span></a></p>' if len(found) > 6 else ""}</div></section>"""
    body = f"""
<section class="mhero"><div class="wrap">{crumbs(("katalog/", "Каталог"), ("katalog/?cat=" + m["dir"], m["dir_label"]), (None, E(m["name"])))}
<div class="mgrid"><div>
<h1>{E(m["name"])}</h1>{f'<p class="cn">{E(m["china"])}</p>' if m.get("china") else f'<p class="cn">{E(m["plant"])}</p>'}
<div class="tags">{"".join(f"<span>{E(t)}</span>" for t in tags if t)}</div>
<div class="big{" pr2" if "bu_label" in m else ""}">{price_html(m)}<small>ориентир под&nbsp;ключ</small></div>
<div class="btns">{kp_btns("m_" + bot_key(m["slug"]), light=True) if KP_ON else f'<a class="btn w" href="{u("kontakty/")}">Подобрать такую машину <span class="ar">→</span></a>'}{f'<a class="btn o" href="#found">Найденные машины · {len(found)}</a>' if found else ""}</div>{kp_note(True) if KP_ON else ""}
</div><div class="mpic"><img src="{u("img/m/" + m["stem"] + ".webp")}" alt="{E(m["name"])}" width="1400" height="824"></div></div>
</div></section>
<section class="sec"><div class="wrap cols">
<div class="rv">{desc}<ul class="pts">{pts}</ul>
<p class="note">Фото&nbsp;— пример модели. Цвет, комплектация и&nbsp;год конкретной машины&nbsp;— по&nbsp;Вашему запросу: присылаем фото, отчёт о&nbsp;проверке и&nbsp;итог до&nbsp;рубля.</p></div>
<div class="rv d1"><table class="spec">{spec}</table></div>
</div></section>
{fblock}
<section class="sec"><div class="wrap"><div class="shead"><div><p class="kick rv">Похожие модели</p><h2 class="h2 rv d1">{m["dir_label"]}: <em>ещё варианты</em></h2></div>
<a class="more rv" href="{u("katalog/?cat=" + m["dir"])}">Весь раздел <span class="ar">→</span></a></div>
<div class="grid" style="margin-top:46px">{"".join(model_card(x) for x in same[:3])}</div></div></section>
{fin_block()}"""
    ld = [bc_ld(("katalog/", "Каталог"), ("katalog/" + m["slug"] + "/", m["name"])),
          {"@context": "https://schema.org", "@type": "Product", "name": m["name"] + " из Китая под ключ", "brand": {"@type": "Brand", "name": m["brand"]},
           "image": SITE + u("img/m/" + m["stem"] + ".webp"), "description": html.unescape(re.sub("<[^>]+>", "", m.get("desc") or DIR_TEXT[m["dir"]])),
           "category": m["dir_label"],
           "offers": {"@type": "AggregateOffer", "priceCurrency": "RUB", "lowPrice": lo_price(m), "highPrice": m["to"] or m["from"],
                      "offerCount": max(1, len(found)), "availability": "https://schema.org/PreOrder", "seller": {"@type": "Organization", "name": "МТК Восток-Авто"}}}]
    page(f'katalog/{m["slug"]}/', f'{m["name"]}{ru_brand(m["brand"])} из Китая под ключ — {price_text(m)} | МТК Восток-Авто',
         f'{m["name"]}{ru_brand(m["brand"])} из Китая под льготный утильсбор: {m["engine"]}, {m["power"].rstrip(".")}. Цена под ключ {price_text(m)}, подбор, проверка, доставка и растаможка.',
         body, active="katalog/", jsonld=ld, og="img/m/" + m["stem"] + ".webp", prio="0.8")


def avto_page(kp, rates):
    brands = sorted({c.get("brand") or "" for c in kp} - {""})
    years = sorted({c.get("year") for c in kp if c.get("year")})
    pmax = math.ceil(max(c["total"] for c in kp) / 1e5) * 1e5
    fuels = [(k, t) for k, t in (("petrol", "Бензин"), ("hybrid", "Гибрид"), ("ev", "Электро"), ("erev", "Гибрид EREV")) if any(c["fuel_key"] == k for c in kp)]
    body = f"""
<section class="phead phs"><div class="wrap">{ph_show(kp)}{crumbs((None, "Авто в Китае"))}
<h1 class="rv in">Авто в&nbsp;Китае<br><em>с&nbsp;ценой на&nbsp;сегодня</em></h1>
<p class="lead">Реальные машины из&nbsp;наших расчётов для&nbsp;клиентов и&nbsp;свежие объявления в&nbsp;Китае&nbsp;— каждый день новые. Цена под&nbsp;ключ пересчитана {ddmm(TODAY)} по&nbsp;курсу юаня {f"{rates['vtb']:.2f}".replace(".", ",")}&nbsp;₽. В&nbsp;неё входят доставка из&nbsp;Китая, таможенные платежи и&nbsp;оформление, получение СБКТС и&nbsp;электронного ПТС, подбор и&nbsp;сопровождение сделки. Если машину уже продали&nbsp;— найдём аналогичную или&nbsp;похожую.</p>
</div></section>
<section class="sec tight"><div class="wrap lay">
<aside class="flt" aria-label="Фильтры">{FCLOSE}
<h4>Поиск</h4><input type="search" data-f="q" placeholder="Модель или марка">
<h4>Топливо</h4><div class="chips" data-f="fuel">{"".join(f'<button class="chip" type="button" data-v="{k}">{t}</button>' for k, t in fuels)}</div>
<h4>Привод</h4><div class="chips" data-f="feat"><button class="chip" type="button" data-v="awd">Только полный</button></div>
<h4>Марка</h4><select data-f="brand"><option value="">Любая</option>{"".join(f"<option>{E(b)}</option>" for b in brands)}</select>
<h4>Цена под ключ</h4><input type="range" data-f="price" min="1000000" max="{int(pmax)}" step="100000" value="{int(pmax)}"><div class="rng"><span>до</span><b data-out="price">любая</b></div>
<h4>Год и пробег</h4><div class="two"><select data-f="ymin"><option value="">Год от</option>{"".join(f'<option value="{y}">{y}</option>' for y in years)}</select>
<select data-f="kmmax"><option value="">Пробег до</option>{"".join(f'<option value="{k}">{k // 1000} тыс. км</option>' for k in (10000, 30000, 50000, 80000, 120000))}</select></div>
<button class="btn ob sm reset" type="button" data-reset>Сбросить фильтры</button>
<button class="btn b sm reset fbtn" type="button" data-fopen>Показать</button>
</aside>
<div>
<div class="lhead"><span class="cnt">Найдено: <b id="cnt">{len(kp)}</b></span><span style="display:flex;gap:10px"><button class="btn ob sm fbtn" type="button" data-fopen>Фильтры</button>
<select data-sort aria-label="Сортировка"><option value="pop-asc">Популярные</option><option value="price-asc">Сначала дешевле</option><option value="price-desc">Сначала дороже</option><option value="year-desc">Сначала новее</option><option value="km-asc">Меньше пробег</option></select></span></div>
<div class="list" data-list>{"".join(kp_card(c) for c in pop_rank(kp))}</div>
<p class="empty" id="empty">По&nbsp;таким условиям машин нет. <a class="more" href="#" data-reset>Сбросить фильтры</a></p>
<p class="note">Цена под&nbsp;ключ: автомобиль, доставка, комиссия банка, пошлина и&nbsp;сборы, утильсбор, СБКТС и&nbsp;ЭПТС, склад и&nbsp;наши услуги. Курс юаня меняется каждый день&nbsp;— вместе с&nbsp;ним меняется и&nbsp;цена. Объявления в&nbsp;Китае живут недолго: если машину продали, подберём такую&nbsp;же по&nbsp;году, пробегу и&nbsp;цене.</p>
</div></div></section>
{fin_block()}"""
    ld = [bc_ld(("avto/", "Авто в Китае")),
          {"@context": "https://schema.org", "@type": "ItemList", "name": "Автомобили из Китая с ценой под ключ",
           "itemListElement": [{"@type": "ListItem", "position": i, "url": SITE + u("avto/" + c["slug"] + "/"), "name": c["title"]} for i, c in enumerate(kp, 1)]}]
    page("avto/", "Авто из Китая с ценой под ключ на сегодня — реальные машины | МТК Восток-Авто",
         f"{len(kp)} реальных машин из Китая с фото и ценой под ключ, пересчитанной по курсу юаня на {ddmm(TODAY)}. Фильтры по марке, топливу, приводу, году и пробегу.",
         body, active="avto/", jsonld=ld, prio="0.9")


def car_page(c, kp, models, rates):
    imgs, sl = c["imgs"], c["slug"]
    main = "".join(f'<img {"src" if i == 1 else "data-src"}="{u(f"img/kp/{sl}/{i}.webp")}" alt="{E(c["title"])}, фото {i}"{"" if i == 1 else " loading=\"lazy\""}>' for i in imgs)
    th = "".join(f'<img src="{u(f"img/kp/{sl}/t{i}.webp")}" alt="" loading="lazy">' for i in imgs)
    p = c["price"]
    brk = "".join(f"<tr><td>{E(k)}</td><td>{rub(v)}</td></tr>" for k, v in p["lines"])
    kv = [("Год", c.get("year")), ("Пробег", f'{c["mileage_km"]:,} км'.replace(",", " ") if c.get("mileage_km") is not None else None),
          ("Двигатель", (f'{c["volume_cc"] / 1000:.1f} л'.replace(".", ",") if c.get("volume_cc") else c.get("fuel_label"))),
          ("Мощность", f'{c["power_hp"]} л.с.' if c.get("power_hp") else None)]
    rows = [("Первая регистрация" if c.get("source") == "che168" else "Год выпуска",
             f'{c["year"]}' + (f', {c["month"]:02d} месяц' if c.get("month") else "") if c.get("year") else None),
            ("Пробег", kv[1][1]), ("Топливо", c.get("fuel_label")), ("Объём двигателя", f'{c["volume_cc"]} см³' if c.get("volume_cc") else None),
            ("Мощность", f'{c["power_hp"]} л.с.' + (f' ({c["power_kw"]} кВт)' if c.get("power_kw") else "") if c.get("power_hp") else None),
            ("Батарея", f'{c["battery_kwh"]:g} кВт·ч'.replace(".", ",") if c.get("battery_kwh") else None), ("Запас хода", f'{c["range_km"]} км' if c.get("range_km") else None),
            ("Коробка", c.get("transmission")), ("Привод", c.get("drive")), ("Кузов", (c.get("body") or "").capitalize() or None), ("Цвет", c.get("color")),
            ("Комплектация", c.get("trim")), ("Цена в Китае", f'{c["car_cny"]:,} ¥'.replace(",", " ") if c.get("car_cny") else None)]
    spec = "".join(f"<tr><th>{k}</th><td>{E(str(v))}</td></tr>" for k, v in rows if v)
    model = next((m for m in models if m["name"] == c.get("catalog_name")), None)
    sim = [x for x in kp if x["slug"] != c["slug"] and (x.get("catalog_name") == c.get("catalog_name") and c.get("catalog_name"))]
    sim += [x for x in kp if x["slug"] != c["slug"] and x not in sim and x.get("brand") == c.get("brand")]
    sim += sorted([x for x in kp if x["slug"] != c["slug"] and x not in sim], key=lambda x: abs(x["total"] - c["total"]))
    body = f"""
<section class="phead"><div class="wrap">{crumbs(("avto/", "Авто в Китае"), (None, E(c["title"])))}
<h1 class="rv in">{E(c["title"])} <em>{c.get("year") or ""}</em></h1>
<div class="kv">{"".join(f"<div><small>{k}</small><b>{E(str(v))}</b></div>" for k, v in kv if v)}</div>
</div></section>
<section class="sec tight"><div class="wrap cols">
<div><div class="gal"><div class="gmain">{main}<span class="gn"></span><button class="pv" type="button" aria-label="Предыдущее фото">{SVG_L}</button><button class="nx" type="button" aria-label="Следующее фото">{SVG_R}</button></div>
<div class="gth">{th}</div></div>
<h2 class="h2" style="font-size:clamp(28px,2.6vw,38px);margin-top:50px">Характеристики</h2><table class="spec" style="margin-top:20px">{spec}</table>
{f'<p class="note"><a class="more" href="{u("katalog/" + model["slug"] + "/")}">О модели {E(model["name"])} в каталоге <span class="ar">→</span></a></p>' if model else ""}</div>
<div><div class="box pbox"><p class="kick">Итого под ключ</p><div class="tot">{rub(p["total"])}</div>
<p class="rt">По&nbsp;курсу юаня {f"{rates['vtb']:.2f}".replace(".", ",")}&nbsp;₽ на&nbsp;{ddmm(TODAY)}. Цена пересчитывается каждый день.</p>
<p class="rt">Доставим в&nbsp;любой город России, доставку посчитаем отдельно.</p>
{f'<p class="rt">Объявление в&nbsp;Китае от&nbsp;{che_date(c)}.</p>' if c.get("source") == "che168" else ""}
<details><summary>Из чего складывается цена</summary><table class="brk">{brk}</table></details>
<div class="btns">{kp_btns("a_" + bot_key(c["slug"])) if KP_ON else f'<a class="btn b" href="{u("kontakty/")}">Заказать этот автомобиль</a>'}<a class="btn ob" href="{u("kontakty/")}">Подобрать похожий</a></div>{kp_note() if KP_ON else ""}
<p class="sold">Объявления в&nbsp;Китае живут недолго. Если эту машину уже продали, найдём такую&nbsp;же: год, пробег и&nbsp;цена будут близки.</p></div></div>
</div></section>
<section class="sec bg"><div class="wrap"><div class="shead"><div><p class="kick rv">Похожие авто</p><h2 class="h2 rv d1">Ещё варианты <em>с&nbsp;ценой</em></h2></div>{ARROWS.format(id="reel2")}</div></div>
<div class="reel" id="reel2">{"".join(kp_card(x, vt=True) for x in sim[:10])}</div></section>
<div class="lbox"><img alt=""><button class="x" type="button" aria-label="Закрыть"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
<button class="pv" type="button" aria-label="Назад">{SVG_L}</button><button class="nx" type="button" aria-label="Вперёд">{SVG_R}</button></div>"""
    ld = [bc_ld(("avto/", "Авто в Китае"), ("avto/" + c["slug"] + "/", c["title"])),
          {"@context": "https://schema.org", "@type": ["Product", "Car"], "name": f'{c["title"]} {c.get("year") or ""}'.strip(),
           "brand": {"@type": "Brand", "name": c.get("brand") or ""}, "model": c.get("model"), "vehicleModelDate": str(c.get("year") or ""),
           "mileageFromOdometer": {"@type": "QuantitativeValue", "value": c.get("mileage_km"), "unitCode": "KMT"},
           "fuelType": c.get("fuel_label"), "image": [SITE + u(f'img/kp/{c["slug"]}/{i}.webp') for i in imgs[:5]],
           "offers": {"@type": "Offer", "priceCurrency": "RUB", "price": p["total"], "priceValidUntil": (TODAY + timedelta(days=1)).isoformat(),
                      "availability": "https://schema.org/PreOrder", "seller": {"@type": "Organization", "name": "МТК Восток-Авто"}}}]
    km = f', {kv[1][1]}' if c.get("mileage_km") else ""   # пробег в заголовке: у машин одной модели и года заголовки разные
    page(f'avto/{c["slug"]}/', f'{c["title"]} {c.get("year") or ""}{ru_brand(c.get("brand"))}{km} из Китая — {html.unescape(rub(p["total"]))} под ключ | МТК Восток-Авто',
         f'{c["title"]}{ru_brand(c.get("brand"))} {c.get("year") or ""}, {html.unescape(kp_line(c))}. Цена под ключ на {ddmm(TODAY)}: {html.unescape(rub(p["total"]))}. Фото, характеристики и расчёт.',
         body, active="avto/", jsonld=ld, og=f'img/kp/{c["slug"]}/1.webp', prio="0.7")


def bu_row(b):
    """Строка б/у над новыми, как в премиум-каталоге (макет L8, Юрий 24.10.2026): метка, цена под ключ, подпись; ниже плашка «Новый 2026»."""
    if not b:
        return ""
    pr = f'<b>{rub(b["price"])}</b>' if b["price"] else '<b class="pq">цена по&nbsp;запросу</b>'
    sp = f'<p>{E(b["spec"])}</p>' if b["spec"] else ""
    return f'<div class="bu"><div class="bh"><span class="bl">{E(b["label"])}</span>{pr}</div>{sp}</div><span class="nw">Новый 2026 · цена производителя</span>'


PREM_BRAND = {"mercedes": "Mercedes-Benz", "bmw": "BMW", "landrover": "Land Rover", "liauto": "Li Auto", "nio": "NIO", "aito": "AITO", "im": "IM"}
PREM_FUEL = {"ICE": "petrol", "MHEV": "petrol", "HEV": "hybrid", "PHEV": "hybrid", "BEV": "ev", "EREV": "erev"}
PREM_BODY = [("SUV", "Кроссовер"), ("三厢车", "Седан"), ("掀背车", "Лифтбек"), ("两厢车", "Хэтчбек"), ("旅行车", "Универсал"), ("MPV", "Минивэн"),
             ("跑车", "Купе и кабриолет"), ("敞篷车", "Купе и кабриолет")]


def prem_facets(P):
    """Топливо, привод и кузов модели премиум-каталога по её версиям (~/auto-china/catalog/cars_prem26) — для фильтров (Юрий 27.10.2026)."""
    out = {}
    for m in P.models():
        vs = [v for x in m["mdls"] for v in x["versions"]]
        bodies = {t for v in vs for k, t in PREM_BODY if k in (v.get("body") or "")}
        out[m["key"]] = {"fuel": sorted({PREM_FUEL[v["type"]] for v in vs if v.get("type") in PREM_FUEL}),
                         "awd": any(v.get("drive") == "AWD" for v in vs), "body": sorted(bodies)}
    return out


def premium_page(prem, rates):
    """Премиальные автомобили из Китая: б/у и новые (Юрий 11.10.2026, заголовок — как в каталогах, «Авто» 25.10.2026): карточки с ценой «от» по курсу дня (как строки PDF премиум-каталога),
    над ней строка б/у и плашка «Новый 2026», как в каталоге (Юрий 24.10.2026), авторы фото.
    Данные и фото готовит new/premium.py."""
    import premium as P
    day, noprice = P.day_prices(rates["vtb"], rates["cny"], rates["eur"])
    if noprice:
        print("Премиум без цены (нет в PDF каталога или расходится с ним):", ", ".join(noprice))
    cards = [dict(c, price=day[c["key"]]["from"], bu=day[c["key"]]["bu"]) if c["key"] in day else dict(c, price=None, bu=None)
             for c in prem["cards"]]
    origins = [(k, t) for k, t in prem["origins"]]
    chips = "".join(f'<button class="chip" type="button" data-v="{k}">{t} <i>{sum(c["origin"] == k for c in cards)}</i></button>' for k, t in origins)
    fac = prem_facets(P)
    for c in cards:
        f = fac.get(c["key"], {})
        c["brand_t"] = PREM_BRAND.get(c["brand"], c["brand"].capitalize())
        c["fuel"], c["awd"], c["body"] = f.get("fuel", []), f.get("awd", False), f.get("body", [])
        c["cond"] = " ".join((["new"] if c.get("price") else []) + (["bu"] if c.get("bu") else []))
        c["pmin"] = min([x for x in (c.get("price"), (c.get("bu") or {}).get("price")) if x] or [0])
    fuels = [(k, t) for k, t in (("petrol", "Бензин"), ("hybrid", "Гибрид"), ("ev", "Электро"), ("erev", "Гибрид EREV")) if any(k in c["fuel"] for c in cards)]
    bodies = sorted({b for c in cards for b in c["body"]}, key=lambda b: -sum(b in c["body"] for c in cards))
    brands = sorted({c["brand_t"] for c in cards})
    pmax = math.ceil(max(c["pmin"] for c in cards) / 1e6) * 1e6
    grid = "".join(f'<div class="card pc" data-origin="{c["origin"]}" data-fuel="{" ".join(c["fuel"])}" data-feat="{"awd" if c["awd"] else ""}" data-body="{E(" ".join(c["body"]))}"'
                   f' data-brand="{E(c["brand_t"])}" data-cond="{c["cond"]}" data-price="{c["pmin"] or 10**10}" data-name="{E(c["name"])}" data-q="{E((c["name"] + " " + (c.get("cn") or "")).lower())}">'
                   f'<div class="im{" ct" if c.get("bg") else ""}"'
                   + (f' style="background:linear-gradient({c["bg"][0]},{c["bg"][1]} 50%,{c["bg"][2]} 50%)"' if c.get("bg") else "")
                   + f'><img src="{u(c["img"])}" alt="{E(c["name"])}" loading="lazy" width="{c["size"][0]}" height="{c["size"][1]}"></div>'
                   f'<div class="t"><h3>{E(c["name"])}</h3>'
                   + (f'<div class="pz">{bu_row(c["bu"])}<div class="pr">от&nbsp;{rub(c["price"])}<small>под ключ</small></div></div>'
                      if c.get("price") else "")
                   + '</div></div>' for c in cards)
    credits = "".join(f'<li>{E(c["name"])}&nbsp;— {E(c["author"])}, <a href="{E(c["license_url"])}" rel="license noopener" target="_blank">{E(c["license"])}</a>, '
                      f'<a href="{E(c["page"])}" rel="noopener" target="_blank">Wikimedia Commons</a></li>' for c in cards)
    body = f"""
<section class="phead">{phv("premium")}<div class="wrap">{crumbs((None, "Премиум-авто"))}
<h1 class="rv in">Премиальные автомобили <em>из&nbsp;Китая</em>: б/у и&nbsp;новые</h1>
<p class="lead">Ориентировочные цены под&nbsp;ключ на&nbsp;{ddmm(TODAY)}. В&nbsp;них входят доставка из&nbsp;Китая, таможенные платежи и&nbsp;оформление, получение СБКТС и&nbsp;электронного ПТС, подбор и&nbsp;сопровождение сделки. Доставим в&nbsp;любой город России.</p>
</div></section>
<section class="sec tight prem"><div class="wrap lay">
<aside class="flt" aria-label="Фильтры">{FCLOSE}
<h4>Поиск</h4><input type="search" data-f="q" placeholder="Модель или марка">
<h4>Топливо</h4><div class="chips" data-f="fuel">{"".join(f'<button class="chip" type="button" data-v="{k}">{t}</button>' for k, t in fuels)}</div>
<h4>Привод</h4><div class="chips" data-f="feat"><button class="chip" type="button" data-v="awd">Только полный</button></div>
<h4>Кузов</h4><div class="chips" data-f="body">{"".join(f'<button class="chip" type="button" data-v="{E(b)}">{E(b)}</button>' for b in bodies)}</div>
<h4>Марка</h4><select data-f="brand"><option value="">Любая</option>{"".join(f"<option>{E(b)}</option>" for b in brands)}</select>
<h4>Цена под ключ</h4><input type="range" data-f="price" min="2000000" max="{int(pmax)}" step="500000" value="{int(pmax)}"><div class="rng"><span>до</span><b data-out="price">любая</b></div>
<button class="btn ob sm reset" type="button" data-reset>Сбросить фильтры</button>
<button class="btn b sm reset fbtn" type="button" data-fopen>Показать</button>
</aside>
<div>
<div class="pfl"><div class="chips" data-f="origin" data-one><button class="chip all" type="button" data-reset>Все <i>{len(cards)}</i></button>{chips}</div>
<span style="display:flex;gap:10px;align-items:center"><span class="cnt">Найдено: <b id="cnt">{len(cards)}</b></span><button class="btn ob sm fbtn" type="button" data-fopen>Фильтры</button></span></div>
<div class="list" data-list>{grid}</div>
<p class="empty" id="empty">По&nbsp;таким условиям моделей нет. <a class="more" href="#" data-reset>Сбросить фильтры</a></p>
</div></div>
<div class="wrap">
<div class="box pcta"><div><h3>Узнать цену под&nbsp;ключ</h3><p>Фото&nbsp;— пример модели, не&nbsp;конкретный автомобиль. Цвет, комплектацию и&nbsp;город выдачи подберём под&nbsp;Ваш запрос и&nbsp;посчитаем итог до&nbsp;рубля.</p></div>
{f'<div>{kp_btns("p")}{kp_note()}</div>' if KP_ON else f'<a class="btn b" href="{u("kontakty/")}">Написать специалисту <span class="ar">→</span></a>'}</div>
<div class="credits"><h2>Авторы фото</h2><p>Фото моделей&nbsp;— с&nbsp;Wikimedia Commons по&nbsp;свободным лицензиям. Снимки обрезаны и&nbsp;уменьшены под&nbsp;карточки.</p><ul>{credits}</ul></div>
</div></section>"""
    ld = [bc_ld(("premium/", "Премиум-авто")),
          {"@context": "https://schema.org", "@type": "ItemList", "name": "Премиальные автомобили из Китая: б/у и новые",
           "itemListElement": [{"@type": "ListItem", "position": i, "name": c["name"]} for i, c in enumerate(cards, 1)]}]
    page("premium/", "Премиальные автомобили из Китая: б/у и новые под ключ | МТК Восток-Авто",
         f"{len(cards)} моделей премиальных автомобилей из Китая, б/у и новые: европейские, японские, корейские, американские и китайские марки. Подбор, доставка и растаможка под ключ.",
         body, active="premium/", jsonld=ld, og=cards[0]["img"], prio="0.8")


def load_moto(rates=None):
    """Электромопеды «Восток-Мото» (Юрий 24.10 и 26.10.2026, задача «Авто» 26.10.2026): данные и фото — выгрузка «Мото»
    (MOTO/out/site), их не правим; копия json — new/data/mopedy.json (сборка без выгрузки идёт по ней и уже сделанным фото).
    Цены — по курсам ЦБ дня функцией «Мото» price_rub (moto_price.py: формула, наценки и курс ЦБ — её; Юрий 26.10.2026:
    сайт пересчитывает каждое утро); нет курса доллара или юаней в записи — рубли выгрузки."""
    src, f = MOTO / "out" / "site" / "mopedy.json", DATA / "mopedy.json"
    if src.exists():
        shutil.copyfile(src, f)
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    out = IMG / "moto"
    out.mkdir(parents=True, exist_ok=True)
    for m in d["mopeds"]:
        ph, dst = MOTO / "out" / "site" / m["photo"], out / f'{m["id"]}.webp'
        if ph.exists():
            m["size"] = webp(ph, dst, 750, 80)
        elif dst.exists():
            with Image.open(dst) as im:
                m["size"] = im.size
    for x in out.glob("*.webp"):                       # фото мопедов, которых больше нет в выгрузке
        if x.stem not in {m["id"] for m in d["mopeds"]} | {"logo"}:
            x.unlink()
    lg = MOTO / "logo" / "family" / "Vostok-Moto-logo-izumrud-4.png"
    if lg.exists() and (not (out / "logo.webp").exists() or (out / "logo.webp").stat().st_mtime < lg.stat().st_mtime):
        im = Image.open(lg).convert("RGBA")
        im = im.crop(im.getchannel("A").getbbox()).resize((240, 240), Image.LANCZOS)
        im.save(out / "logo.webp", quality=90, method=6)
    first = next((m for m in d["mopeds"] if m.get("size")), None)
    if first and (MOTO / "out" / "site" / first["photo"]).exists():   # превью ссылки
        im = Image.open(MOTO / "out" / "site" / first["photo"]).convert("RGB")
        im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS).save(out / "og.jpg", quality=82)
    lost = [m["name"] for m in d["mopeds"] if not m.get("size")]
    if lost:
        print("Мопеды без фото (на сайт не идут):", ", ".join(lost))
    d["mopeds"] = [m for m in d["mopeds"] if m.get("size")]
    if rates and rates.get("usd") and (MOTO / "moto_price.py").exists():
        spec = importlib.util.spec_from_file_location("vostok_moto_price", MOTO / "moto_price.py")
        mp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mp)
        n = 0
        for m in d["mopeds"]:
            if m.get("price_from_cny"):
                m["price_from_rub"], m["price_to_rub"] = mp.price_rub(m, rates["cny"], rates["usd"])
                n += 1
        if n:
            d["date"] = ddmm(TODAY)
        print(f"Мопеды: цены по курсу ЦБ {rates['cbr_date']} (юань {rates['cny']:.4f}, доллар {rates['usd']:.4f}) — {n} из {len(d['mopeds'])}")
    return d


MOTO_FACTS = ["Ставить на&nbsp;учёт в&nbsp;ГИБДД не&nbsp;нужно", "Номера не&nbsp;нужны", "ПТС не&nbsp;нужен", "ОСАГО не&nbsp;нужно",
              "Права категории M или любой другой: A,&nbsp;B,&nbsp;C", "Ездить можно с&nbsp;16&nbsp;лет"]   # как на обложке каталога «Восток-Мото»


def moto_price(m):
    a, b = m["price_from_rub"], m.get("price_to_rub")
    return f'<i>цена от</i> {rub(a)}' + (f' <i>до</i> {rub(b)}' if b and b != a else "")


def moto_page(d):
    """Электромопеды из Китая «Восток-Мото» (Юрий 26.10.2026: раздел с мопедами, фото и ценами): карточки как в клиентском каталоге
    «Восток-Мото» — фото, класс, характеристики, заметка, «цена от … до …» (себестоимость до Ижевска + 20 000 ₽, решение Юрия 26.10;
    формула «Мото», курс ЦБ дня — load_moto). Шлемы не берём."""
    ms, date_ = d["mopeds"], d["date"]
    brands = list(dict.fromkeys(m["brand"] for m in ms))
    chips = "".join(f'<button class="chip" type="button" data-v="{slugify(b)}">{E(b)} <i>{sum(m["brand"] == b for m in ms)}</i></button>' for b in brands)
    for i, m in enumerate(ms):                          # для фильтров (Юрий 27.10.2026): запас хода — верхняя граница, батарея — из строки «… А·ч»
        km = [int(x) for x in re.findall(r"\d+", next((x for x in m["specs"] if x.startswith("запас хода")), ""))]
        bat = next((x for x in m["specs"] if "А·ч" in x), "")
        m["_km"], m["_ord"] = max(km or [0]), i
        m["_bat"] = "graphene" if "графен" in bat else "lithium" if "литие" in bat else "lead" if "свинцов" in bat else ""
    pmax = math.ceil(max(m["price_from_rub"] for m in ms) / 5000) * 5000
    pmin = math.floor(min(m["price_from_rub"] for m in ms) / 5000) * 5000
    bats = [(k, t) for k, t in (("lead", "Свинцовая"), ("graphene", "Графеновая"), ("lithium", "Литиевая")) if any(m["_bat"] == k for m in ms)]
    grid = "".join(f'<div class="card pc mc" data-brand="{slugify(m["brand"])}" data-price="{m["price_from_rub"]}" data-range="{m["_km"]}" data-bat="{m["_bat"]}"'
                   f' data-ord="{m["_ord"]}" data-name="{E(m["name"])}" data-q="{E((m["name"] + " " + m["brand"]).lower())}"><div class="im ct"><img src="{u("img/moto/" + m["id"] + ".webp")}" alt="{E(m["name"])}, электромопед" loading="lazy" width="{m["size"][0]}" height="{m["size"][1]}"></div>'
                   f'<div class="t"><h3>{E(m["name"])}</h3><span class="cl">{E(m["class"])}</span>'
                   f'<ul class="ms">{"".join(f"<li>{E(x)}</li>" for x in m["specs"])}</ul>'
                   + (f'<p class="mn">{E(m["note"])}</p>' if m.get("note") else "")
                   + f'<div class="pr">{moto_price(m)}</div></div></div>' for m in ms)
    lo = min(m["price_from_rub"] for m in ms)
    facts = "".join(f"<li>{t}</li>" for t in MOTO_FACTS) + '<li class="w">Шлем обязателен</li>'
    body = f"""
<section class="phead">{phv("mopedy")}<div class="wrap">{crumbs((None, "Электромопеды"))}
<div class="mhd"><img class="mlogo" src="{u("img/moto/logo.webp")}" alt="Восток-Мото" width="120" height="120">
<h1 class="rv in sm">Электромопеды <em>из&nbsp;Китая</em></h1></div>
<p class="lead">Помимо автомобилей, привозим из&nbsp;Китая электромопеды. <span class="nohy">«Восток-Мото»</span>: {len(ms)} {plural(len(ms), "модель", "модели", "моделей")} до&nbsp;50&nbsp;км/ч и&nbsp;до&nbsp;4&nbsp;кВт под&nbsp;права категории M. Цены с&nbsp;доставкой до&nbsp;вашего города в&nbsp;России, по&nbsp;курсу на&nbsp;{date_}: цена зависит от&nbsp;курса&nbsp;— актуальную цену уточняйте.</p>
</div></section>
<section class="sec tight prem moto"><div class="wrap">
<ul class="mfacts">{facts}</ul></div>
<div class="wrap lay">
<aside class="flt" aria-label="Фильтры">{FCLOSE}
<h4>Поиск</h4><input type="search" data-f="q" placeholder="Модель или марка">
<h4>Марка</h4><div class="chips" data-f="brand">{chips}</div>
<h4>Цена</h4><input type="range" data-f="price" data-rub min="{pmin}" max="{pmax}" step="5000" value="{pmax}"><div class="rng"><span>до</span><b data-out="price">любая</b></div>
<h4>Запас хода</h4><select data-f="rmin"><option value="">Любой</option>{"".join(f'<option value="{k}">от&nbsp;{k}&nbsp;км</option>' for k in (40, 50, 60, 80))}</select>
<h4>Батарея</h4><div class="chips" data-f="bat">{"".join(f'<button class="chip" type="button" data-v="{k}">{t}</button>' for k, t in bats)}</div>
<button class="btn ob sm reset" type="button" data-reset>Сбросить фильтры</button>
<button class="btn b sm reset fbtn" type="button" data-fopen>Показать</button>
</aside>
<div>
<div class="lhead"><span class="cnt">Найдено: <b id="cnt">{len(ms)}</b></span><span style="display:flex;gap:10px"><button class="btn ob sm fbtn" type="button" data-fopen>Фильтры</button>
<select data-sort aria-label="Сортировка"><option value="ord-asc">По порядку</option><option value="price-asc">Сначала дешевле</option><option value="price-desc">Сначала дороже</option><option value="range-desc">Больше запас хода</option></select></span></div>
<div class="list" data-list>{grid}</div>
<p class="empty" id="empty">По&nbsp;таким условиям моделей нет. <a class="more" href="#" data-reset>Сбросить фильтры</a></p>
</div></div>
<div class="wrap">
<div class="box pcta"><div><h3>Узнать актуальную цену</h3><p>Цена зависит от&nbsp;курса юаня. Напишите&nbsp;— подберём модель и&nbsp;цвет и&nbsp;назовём цену на&nbsp;сегодня.</p></div>
<a class="btn b" href="{u("kontakty/")}">Написать специалисту <span class="ar">→</span></a></div>
</div></section>"""
    ld = [bc_ld(("mopedy/", "Электромопеды")),
          {"@context": "https://schema.org", "@type": "ItemList", "name": "Электромопеды из Китая «Восток-Мото»",
           "itemListElement": [{"@type": "ListItem", "position": i, "name": m["name"]} for i, m in enumerate(ms, 1)]}]
    page("mopedy/", "Электромопеды из Китая «Восток-Мото»: цены и характеристики | МТК Восток-Авто",
         f"{len(ms)} {plural(len(ms), 'модель', 'модели', 'моделей')} электромопедов из Китая: {', '.join(brands[:4])} и другие. До 50 км/ч, права категории M, "
         f"учёт в ГИБДД не нужен. Цена от {html.unescape(rub(lo))}.",
         body, active="mopedy/", jsonld=ld, og="img/moto/og.jpg", prio="0.8")


def how_page(faq):
    tl = []
    for n, h, p, pay, ph, free in STEPS:
        img = ph or {"01": "sec2", "03": "d_q05_2", "05": "d_xrv_2"}.get(n)
        tl.append(f'<div class="ts rv{" free" if free else ""}"><div class="c">{n}</div><div><h3>{h}</h3><p>{nbs(p)}</p>{f"<span class=pay>{nbs(pay)}</span>" if pay else ""}</div>'
                  f'<div class="ph"><img src="{u("img/" + (img + "_m" if img.startswith("sec") else img) + ".webp")}" alt="" loading="lazy"></div></div>')
    docs = ["Договор на&nbsp;подбор и&nbsp;сопровождение", "Контракт и&nbsp;инвойс от&nbsp;продавца", "Чек об&nbsp;оплате через ВТБ", "Таможенные документы",
            "СБКТС и&nbsp;электронный ПТС", "Ключи и&nbsp;всё, что положено к&nbsp;машине"]
    qs = [q for q in faq if q.get("group") in ("О компании и договоре", "Сроки и доставка") and not q.get("confirm")][:5]
    body = f"""
<section class="phead phx"><div class="wrap">{ph_route()}{crumbs((None, "Как купить"))}
<h1 class="rv in sm">Как купить автомобиль<br><em>из&nbsp;Китая под&nbsp;ключ</em></h1>
<p class="lead">Семь шагов от&nbsp;выбора до&nbsp;ключей. Срок от&nbsp;оплаты до&nbsp;выдачи&nbsp;— обычно <span class="nobr">45–65</span>&nbsp;дней. Каждый шаг прозрачен: присылаем фото, видео, документы и&nbsp;сроки.</p></div></section>
<section class="sec tight"><div class="wrap"><div class="tl">{"".join(tl)}</div></div></section>
<section class="sec bg" id="docs"><div class="wrap"><div class="cols"><div><p class="kick rv">Документы</p><h2 class="h2 rv d1">Что Вы <em>получаете</em></h2>
<p class="lead rv d2">Все платежи&nbsp;— по&nbsp;договору и&nbsp;через банк. После выдачи машину ставят на&nbsp;учёт в&nbsp;ГИБДД как обычную.</p></div>
<ul class="pts rv d1">{"".join(f"<li>{d}</li>" for d in docs)}</ul></div>
<h3 class="docs-h rv">Образцы документов из&nbsp;реальных сделок</h3>
<div class="docs4">{"".join(f'<a class="doc rv" href="{u("img/docs/" + k + ".webp")}" target="_blank" rel="noopener"><span class="di"><img src="{u("img/docs/" + k + "_t.webp")}" alt="{E(t)}" loading="lazy"></span><span class="dn">{t}</span></a>' for k, t, _ in DOCS)}</div>
<p class="note">Личные данные покупателя и&nbsp;продавца скрыты. Нажмите на&nbsp;документ, чтобы открыть его крупно.</p></div></section>
{f'<section class="sec"><div class="wrap"><p class="kick rv">Вопросы</p><h2 class="h2 rv d1">Коротко <em>о&nbsp;главном</em></h2><div class="faq">{faq_items(qs)}</div><p class="note"><a class="more" href="{u("voprosy/")}">Все вопросы <span class="ar">→</span></a></p></div></section>' if qs else ""}
{fin_block()}"""
    page("kak-kupit/", "Как купить автомобиль из Китая под ключ — 7 шагов | МТК Восток-Авто",
         "Как проходит покупка машины из Китая: выбор, проверка, договор и оплата через ВТБ, доставка, СБКТС и ЭПТС, растаможка, выдача. Срок 45–65 дней.",
         body, active="kak-kupit/", jsonld=[bc_ld(("kak-kupit/", "Как купить"))] + ([faq_ld(qs)] if qs else []), prio="0.8")


def price_page(kp, rates):
    # пример — Nissan Kicks Татьяны Парусовой, фото из её КП (Юрий 28.10.2026); имени клиентки на сайте нет
    ex = next((c for c in kp if c["slug"].startswith("nissan-kicks-1-5-xv-deluxe-2022")), None) or next((c for c in kp if "kicks" in c["slug"]), kp[0] if kp else None)
    exb = ""
    if ex:
        exb = f"""<section class="sec bg"><div class="wrap cols"><div><p class="kick rv">Пример</p><h2 class="h2 rv d1">{E(ex["title"])} <em>{ex.get("year") or ""}</em></h2>
<p class="lead rv d2">Так выглядит расчёт конкретной машины на&nbsp;{ddmm(TODAY)}: каждая строка&nbsp;— отдельный платёж, ничего сверху.</p>
<a class="exph rv d2" href="{u("avto/" + ex["slug"] + "/")}"><img src="{u("img/kp/" + ex["slug"] + "/1.webp")}" alt="{E(ex["title"])} {ex.get("year") or ""}" loading="lazy"></a>
<p class="rv d2" style="margin-top:26px"><a class="btn b" href="{u("avto/" + ex["slug"] + "/")}">Смотреть машину <span class="ar">→</span></a></p></div>
<div class="box rv d1"><table class="brk">{"".join(f"<tr><td>{E(k)}</td><td>{rub(v)}</td></tr>" for k, v in ex["price"]["lines"])}
<tr><td><b>Итого под ключ</b></td><td><b>{rub(ex["total"])}</b></td></tr></table></div></div></section>"""
    v = rates["vtb"]
    # плёнка — как в КП: одна строка 3 500 – 6 000 ¥, без фронт-зоны (Юрий 09.10.2026, kp_v3 PPF_*; на сайте с 27.10.2026)
    svc = [("Проверка машины", (1300,), "Осмотр на&nbsp;месте с&nbsp;отчётом, фото и&nbsp;видео"),
           ("Плёнка PPF&nbsp;— полная оклейка", (3500, 6000), "Цена зависит от&nbsp;качества плёнки и&nbsp;марки автомобиля")]
    span = lambda ys: "&nbsp;– ".join(f"{y:,}".replace(",", "&nbsp;") for y in ys)
    rspan = lambda ys: "&nbsp;– ".join([f"{round(y * v):,}".replace(",", "&nbsp;") for y in ys[:-1]] + [rub(ys[-1] * v)])
    body = f"""
<section class="phead phx pinc"><div class="wrap">{crumbs((None, "Стоимость"))}
<h1 class="rv in">Стоимость&nbsp;— <em>под&nbsp;ключ</em></h1>
<p class="lead">Автомобиль, доставка, растаможка, документы и&nbsp;наши услуги. Оплата в&nbsp;четыре этапа по&nbsp;договору, без&nbsp;скрытых платежей.</p>
{ph_inc()}
</div></section>
<section class="sec"><div class="wrap"><p class="kick rv">Платежи</p><h2 class="h2 rv d1">Четыре этапа <em>оплаты</em></h2>{PAYS}
<p class="note rv">Оплачивается отдельно: постановка на&nbsp;учёт в&nbsp;ГИБДД и&nbsp;страховка&nbsp;— по&nbsp;тарифам ГИБДД и&nbsp;страховой.</p></div></section>
{exb}
<section class="sec"><div class="wrap"><p class="kick rv">Дополнительно</p><h2 class="h2 rv d1">Услуги <em>по&nbsp;желанию</em></h2>
<div class="svc">{"".join(f'<div class="rv"><b>{t}</b><span>{span(ys)}&nbsp;¥</span><p>≈&nbsp;{rspan(ys)} по&nbsp;курсу дня · {d}</p></div>' for t, ys, d in svc)}</div></div></section>
{fin_block()}"""
    page("stoimost/", "Стоимость автомобиля из Китая под ключ: из чего складывается цена | МТК Восток-Авто",
         f"Из чего складывается цена машины из Китая под ключ: автомобиль, доставка, комиссия банка, пошлина, утильсбор, СБКТС и ЭПТС, услуги. Курс юаня на {ddmm(TODAY)}.",
         body, active="stoimost/", jsonld=[bc_ld(("stoimost/", "Стоимость"))], prio="0.8")


def ph_inc():
    """«Стоимость под ключ»: справа в шапке — что входит в цену и кнопка в «Калькулятор» (Юрий 27.10.2026: калькулятор отдельным разделом)."""
    import price as PR
    items = ["Автомобиль по&nbsp;цене в&nbsp;Китае", f"Доставка автовозом {nf(PR.DELIVERY_CNY)}&nbsp;¥ и&nbsp;погрузка по&nbsp;Китаю",
             "Пошлина, сборы и&nbsp;утильсбор", "Оформление: растаможка, СБКТС, ЭПТС", "Подбор автомобиля и&nbsp;сопровождение сделки"]
    return (f'<div class="phinc"><h3>Что входит в&nbsp;цену</h3><ul>{"".join(f"<li>{t}</li>" for t in items)}</ul>'
            f'<a class="btn w" href="{u("kalkulyator/")}">Посчитать в&nbsp;калькуляторе <span class="ar">→</span></a></div>')


def calc_page(rates):
    """«Калькулятор под ключ» (Юрий 27.10.2026, макет 3): курсы строкой под заголовком, поля в ряд, крупный итог под ними.
    Вводится цена машины в Китае — калькулятор сам добавляет доставку, растаможку, оформление, подбор и сопровождение."""
    import price as PR
    v = rates["vtb"]
    rl = (f'<p class="rline"><span>Курс юаня для&nbsp;расчёта на&nbsp;{ddmm(TODAY)} <b>{f"{v:.2f}".replace(".", ",")}&nbsp;₽</b></span>'
          f'<span>Юань по&nbsp;ЦБ&nbsp;— для&nbsp;пошлины <b>{f"{rates['cny']:.4f}".replace(".", ",")}&nbsp;₽</b></span>'
          f'<span>Евро по&nbsp;ЦБ&nbsp;— для&nbsp;пошлины <b>{f"{rates['eur']:.2f}".replace(".", ",")}&nbsp;₽</b></span></p>')
    body = f"""
<section class="phead phx pcalc pkalk"><div class="wrap">{crumbs((None, "Калькулятор"))}
<h1 class="rv in">Калькулятор <em>под&nbsp;ключ</em></h1>
<p class="lead">Вы вводите цену автомобиля в&nbsp;Китае&nbsp;— калькулятор считает цену под&nbsp;ключ с&nbsp;доставкой автовозом {nf(PR.DELIVERY_CNY)}&nbsp;¥, растаможкой и&nbsp;оформлением, подбором и&nbsp;сопровождением сделки.</p>
{rl}{ph_calc(rates)}
<p class="kcta">Заинтересовало? Свяжитесь с&nbsp;нами&nbsp;— подберём машину под&nbsp;этот бюджет. {kp_btns("calc", light=True, calc=True).replace('class="btn w"', 'class="btn w sm"') if KP_ON else f'<a class="btn w sm" href="{u("kontakty/")}">Написать нам <span class="ar">→</span></a>'}</p>{kp_note(True) if KP_ON else ""}
</div></section>
<section class="sec kmore"><div class="wrap"><a class="more" href="{u("stoimost/")}">Из&nbsp;чего складывается цена и&nbsp;как проходит оплата <span class="ar">→</span></a></div></section>
{fin_block()}"""
    page("kalkulyator/", "Калькулятор стоимости автомобиля из Китая под ключ | МТК Восток-Авто",
         f"Калькулятор цены машины из Китая под ключ: доставка, пошлина, утильсбор, оформление и наши услуги. Курс юаня на {ddmm(TODAY)}.",
         body, active="kalkulyator/", jsonld=[bc_ld(("kalkulyator/", "Калькулятор"))], prio="0.8")


def deliv_page():
    body = f"""
<section class="phead">{phv("vydannye")}<div class="wrap">{crumbs((None, "Выданные авто"))}
<h1 class="rv in">Примеры выданных <em>автомобилей</em></h1>
<p class="lead">Некоторые из&nbsp;автомобилей, которые мы уже привезли и&nbsp;передали владельцам. Цены&nbsp;— итог под&nbsp;ключ по&nbsp;договору.</p></div></section>
<section class="sec tight"><div class="wrap"><div class="dgrid" style="margin-top:0">{deliv_cards()}</div>
<p class="note">Новые выдачи&nbsp;— в&nbsp;нашем <a class="more" href="{CHANNEL}">Telegram-канале <span class="ar">→</span></a></p></div></section>
{fin_block()}"""
    page("vydannye/", "Примеры выданных автомобилей из Китая — наши клиенты | МТК Восток-Авто",
         "Примеры автомобилей из Китая, которые мы привезли и передали владельцам: модель, год, пробег, город выдачи и итог под ключ по договору.",
         body, active="vydannye/", jsonld=[bc_ld(("vydannye/", "Выданные авто"))], prio="0.6")


def faq_page(faq):
    groups = []
    for g in dict.fromkeys(q["group"] for q in faq):
        items = [q for q in faq if q["group"] == g]
        groups.append(f'<div class="fgroup"><h2 class="rv">{E(g)}</h2><div class="faq" style="margin-top:20px">{faq_items(items)}</div></div>')
    body = f"""
<section class="phead">{phv("voprosy")}<div class="wrap">{crumbs((None, "Вопросы"))}
<h1 class="rv in">Частые <em>вопросы</em></h1>
<p class="lead">Оплата, сроки, таможня, утильсбор, проверка машины и&nbsp;документы. Не&nbsp;нашли ответ&nbsp;— <a class="lk" href="{u("kontakty/")}">напишите специалисту</a>.</p>
<a class="btn o phbtn" href="{u("kontakty/")}">Написать специалисту <span class="ar">→</span></a></div></section>
<section class="sec tight"><div class="wrap" style="max-width:1100px">{"".join(groups)}
<p class="note" style="margin-top:50px"><a class="btn b" href="{u("kontakty/")}">Задать свой вопрос <span class="ar">→</span></a></p></div></section>
{fin_block()}"""
    page("voprosy/", "Частые вопросы об автомобилях из Китая под ключ | МТК Восток-Авто",
         "Ответы на частые вопросы: оплата через ВТБ, сроки доставки, таможня и утильсбор, проверка машины, СБКТС и ЭПТС, электромобили и гибриды.",
         body, active="voprosy/", jsonld=[bc_ld(("voprosy/", "Вопросы")), faq_ld(faq)], prio="0.8")


def ph_chat():
    """«Контакты»: вместо машины — живой чат со специалистами (Юрий 27.10.2026, вариант 2): фото с отметкой «на связи»,
    сообщения всплывают по очереди после «печатает…» (s.js), строка ввода ведёт к карточкам специалистов."""
    lines = ["Здравствуйте! Подберу машину под&nbsp;ваш бюджет и&nbsp;пришлю несколько вариантов.",
             "Северо-Запад: посчитаю цену под&nbsp;ключ с&nbsp;доставкой в&nbsp;ваш город.",
             "Урал и&nbsp;Поволжье: отвечу в&nbsp;Telegram, WhatsApp или&nbsp;MAX."]
    av = lambda p: f'<img src="{u("img/" + p["img"] + ".webp")}" alt="" width="40" height="40">'
    msgs = "".join(f'<div class="m">{av(p)}<div class="bb"><b>{p["name"].split()[0]}</b><p>{t}</p></div></div>' for p, t in zip(TEAM, lines))
    return (f'<div class="phchat"><div class="hd"><div class="av">{"".join(f"<span>{av(p)}</span>" for p in TEAM[:3])}</div>'
            f'<div><b>Специалисты<br>МТК ВОСТОК&#8209;АВТО</b><small><i></i>на&nbsp;связи</small></div></div>'
            f'<div class="msgs">{msgs}<div class="typ" aria-hidden="true"><span></span><span></span><span></span></div></div>'
            f'<a class="in" href="#team">Напишите модель или бюджет<i>→</i></a></div>')


def contacts_page():
    body = f"""
<section class="phead pcont"><div class="wrap">{crumbs((None, "Контакты"))}
<h1 class="rv in sm">Напишите <em>специалисту</em></h1>
<p class="lead">Напишите модель или бюджет&nbsp;— бесплатно подберём несколько машин в&nbsp;Китае и&nbsp;посчитаем цену под&nbsp;ключ с&nbsp;доставкой в&nbsp;ваш город.</p>
{f'<div class="btns">{kp_btns("kont", light=True)}</div>{kp_note(True)}' if KP_ON else ""}</div>{ph_chat()}</section>
<section class="sec tight" id="team"><div class="wrap"><div class="tgrid" style="margin-top:0">{team_cards()}</div>
<div class="box rv" style="margin-top:22px;display:flex;flex-wrap:wrap;gap:20px;align-items:center;justify-content:space-between"><div><h3>Telegram-канал МТК Восток-Авто</h3>
<p style="color:var(--muted);margin-top:6px">Новые машины, подборки и&nbsp;выданные автомобили.</p></div><a class="btn b" href="{CHANNEL}">Открыть канал <span class="ar">→</span></a></div></div></section>
{fin_block()}"""
    page("kontakty/", "Контакты — МТК Восток-Авто, автомобили из Китая под ключ",
         "Специалисты МТК Восток-Авто: Юрий Золотарев, Глеб Цепелев (Северо-Запад), Иван Сергеев (Урал и Поволжье). Telegram, WhatsApp, MAX, телефон.",
         body, active="kontakty/", jsonld=[bc_ld(("kontakty/", "Контакты")), ORG], prio="0.7")


def extras(models, kp, rates, moto=None):
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"<url><loc>{SITE}{u(p)}</loc><lastmod>{TODAY.isoformat()}</lastmod><priority>{pr}</priority></url>\n" for p, pr in PAGES) + "</urlset>\n")
    lines = [f"# МТК Восток-Авто", "", "> Международная транспортная компания «Восток-Авто»: новые и б/у автомобили из Китая под ключ для частных покупателей в России — "
             "подбор, проверка, договор, оплата через ВТБ, доставка, растаможка, СБКТС и ЭПТС. Работаем с Китаем с 2016 года. Срок от оплаты до выдачи 45–65 дней.", "",
             f"Курс юаня для расчёта на {ddmm(TODAY)}: {rates['vtb']:.2f} ₽.", "", "## Разделы", ""]
    lines += [f"- [{t}]({SITE}{u(p)})" for p, t in MENU]
    lines += ["", f"## Каталог ({len(models)} моделей, цена под ключ — ориентир)", ""]
    lines += [f"- [{m['name']}{ru_brand(m['brand'])}]({SITE}{u('katalog/' + m['slug'] + '/')}): {m['engine']}, {m['power']}; {price_text(m)}" for m in models]
    if kp:
        lines += ["", f"## Авто в Китае ({len(kp)} машин, цена под ключ на {ddmm(TODAY)})", ""]
        lines += [f"- [{c['title']} {c.get('year') or ''}]({SITE}{u('avto/' + c['slug'] + '/')}): {kp_line(c)}; {c['total']:,} ₽ под ключ".replace(",", " ") for c in kp]
    if moto and moto["mopeds"]:
        lines += ["", f"## Электромопеды «Восток-Мото» ({len(moto['mopeds'])} {plural(len(moto['mopeds']), 'модель', 'модели', 'моделей')}, права категории M, цены по курсу на {moto['date']})", ""]
        lines += [f"- [{m['name']}]({SITE}{u('mopedy/')}): {' · '.join(m['specs'])}; {html.unescape(re.sub('<[^>]+>', '', moto_price(m)))}" for m in moto["mopeds"]]
    lines += ["", "## Контакты", ""] + [f"- {p['name']} — {p['note']}: {p['tel']}, Telegram @{p['tg']}" for p in TEAM] + [f"- Telegram-канал: {CHANNEL}", ""]
    (OUT / "llms.txt").write_text("\n".join(lines))
    (OUT / "404.html").write_text(f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Страница не найдена — МТК Восток-Авто</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<script>var p=location.pathname;if(p.indexOf("/new/")===0)location.replace(p.slice(4)+location.search+location.hash)</script></head>
<body style="font-family:sans-serif;text-align:center;padding:80px 20px"><h1>Страница не найдена</h1><p><a href="{u()}">На главную МТК Восток-Авто</a></p></body></html>
""")
    if SEARCH.get("indexnow"):                           # ключ IndexNow: Яндекс и Bing узнают о новых и изменённых страницах сразу
        (OUT / f"{SEARCH['indexnow']}.txt").write_text(SEARCH["indexnow"])
    if SEARCH.get("yandex"):                             # файл подтверждения Яндекс Вебмастера — на случай способа «HTML-файл»; мета-тег на главной ставит VERIFY
        (OUT / f"yandex_{SEARCH['yandex']}.html").write_text(f'<html>\n    <head>\n        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n    </head>\n    <body>Verification: {SEARCH["yandex"]}</body>\n</html>\n')
    if SEARCH.get("google_file"):                       # файл подтверждения Google Search Console, способ «HTML-файл» (аккаунт URUZ MARKET, Юрий 28.10.2026); не удалять
        (OUT / f"{SEARCH['google_file']}.html").write_text(f"google-site-verification: {SEARCH['google_file']}.html")
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n" if PREVIEW else f"User-agent: *\nAllow: /\nSitemap: {SITE}{u('sitemap.xml')}\n")


def politika_page():
    """Политика обработки персональных данных («Анализ» 28.10.2026, ч. 2 ст. 18.1 152-ФЗ): сайт (Яндекс Метрика) и боты заявок.
    Пока оператор — заглушка, страница не индексируется и в sitemap не попадает."""
    op = OPERATOR or "[название оператора, ИНН — уточняется]"
    sec = [("Общие положения", [f"Политика определяет, как {E(op)} (далее — Оператор) обрабатывает персональные данные посетителей сайта mtk-vostok-avto.ru и пользователей чат-ботов «МТК Восток-Авто» в&nbsp;Telegram и&nbsp;MAX. Политика составлена по&nbsp;Федеральному закону № 152-ФЗ «О&nbsp;персональных данных»."]),
           ("Какие данные обрабатываются", ["На&nbsp;сайте: файлы cookie, IP-адрес, сведения о&nbsp;браузере и&nbsp;устройстве, действия на&nbsp;страницах&nbsp;— через сервис Яндекс Метрика.",
                                            "В&nbsp;чат-ботах: имя, ник и&nbsp;ID в&nbsp;мессенджере, выбранный автомобиль и&nbsp;параметры расчёта в&nbsp;калькуляторе, ваш город, переписка в&nbsp;чате, номер телефона&nbsp;— если вы его отправили.",
                                            "Каталог в&nbsp;Telegram-боте выдаётся подписчикам канала: бот один раз спрашивает у&nbsp;Telegram, подписан ли ваш ID на&nbsp;канал, и&nbsp;ответ не&nbsp;сохраняет."]),
           ("Цели обработки", ["Ответить на&nbsp;запрос и&nbsp;прислать расчёт стоимости и&nbsp;коммерческое предложение; связаться с&nbsp;вами по&nbsp;заявке; присылать рекламные предложения&nbsp;— только с&nbsp;отдельного согласия; вести статистику посещений сайта, чтобы улучшать его."]),
           ("Основания", ["Расчёт по&nbsp;вашему запросу в&nbsp;боте&nbsp;— действия по&nbsp;запросу субъекта до&nbsp;заключения договора (п.&nbsp;5 ч.&nbsp;1 ст.&nbsp;6 152-ФЗ). Номер телефона и&nbsp;переписка&nbsp;— с&nbsp;вашего согласия (ст.&nbsp;9 152-ФЗ). Реклама&nbsp;— с&nbsp;отдельного согласия (ст.&nbsp;18 38-ФЗ «О&nbsp;рекламе», ст.&nbsp;15 152-ФЗ)."]),
           ("Что Оператор делает с данными", ["Сбор, запись, систематизация, накопление, хранение, уточнение, использование, удаление и&nbsp;уничтожение. Обработка автоматизированная. Персональные данные граждан России записываются и&nbsp;хранятся в&nbsp;базах данных на&nbsp;территории Российской Федерации."]),
           ("Срок обработки", ["До&nbsp;достижения цели или отзыва согласия, но&nbsp;не&nbsp;дольше 3&nbsp;лет с&nbsp;последнего обращения. После этого данные удаляются в&nbsp;течение 30&nbsp;дней."]),
           ("Кому передаются данные", ["Специалистам Оператора, которые ведут вашу заявку. Сообщения в&nbsp;ботах передаются через Telegram и&nbsp;MAX по&nbsp;их правилам, статистика сайта&nbsp;— через Яндекс Метрику. Другим лицам Оператор данные не&nbsp;передаёт, кроме случаев, предусмотренных законом."]),
           ("Ваши права", ["Узнать, какие ваши данные обрабатываются; потребовать уточнить или удалить их; отозвать согласие; обжаловать действия Оператора в&nbsp;Роскомнадзоре или в&nbsp;суде."]),
           ("Как отозвать согласие", ["Напишите в&nbsp;чат-бот «Отозвать согласие»&nbsp;— номер телефона и&nbsp;данные заявки будут удалены. От&nbsp;рекламы&nbsp;— кнопка «Отписаться» под&nbsp;любым предложением. Можно также написать специалисту: " + f'<a href="{u("kontakty/")}">Контакты</a>.']),
           ("Оператор", [f"{E(op)}{OPERATOR_RKN}. Связаться&nbsp;— " + f'<a href="{u("kontakty/")}">Контакты</a>.']),]
    doc = "".join(f"<h2>{h}</h2>" + "".join(f"<p>{t}</p>" for t in ps) for h, ps in sec)
    body = f"""
<section class="phead"><div class="wrap">{crumbs((None, "Политика обработки данных"))}
<h1 class="rv in sm">Политика обработки <em>персональных данных</em></h1>
<p class="lead">Редакция от&nbsp;29.10.2026.</p></div></section>
<section class="sec tight"><div class="wrap"><div class="doc">{doc}</div></div></section>"""
    page("politika/", "Политика обработки персональных данных — МТК Восток-Авто",
         "Как МТК Восток-Авто обрабатывает персональные данные посетителей сайта и пользователей чат-ботов.", body, noindex=not OPERATOR, prio="0.2")


def bot_data(models, kp, rates):
    """Данные для бота заявок (tools/mtk-zayavki/bot.py): по коду из ссылки «Получить КП» — те же цифры, что на странице сайта."""
    cars = {bot_key(c["slug"]): {"slug": c["slug"], "t": f'{c["title"]} {c.get("year") or ""}'.strip(), "line": html.unescape(kp_line(c)),
                                 "total": c["price"]["total"], "lines": [[k, v] for k, v in c["price"]["lines"]],
                                 "img": f'img/kp/{c["slug"]}/1.webp'} for c in kp}
    mods = {bot_key(m["slug"]): {"slug": m["slug"], "t": m["name"], "price": price_text(m), "img": f'img/m/{m["stem"]}.webp'} for m in models}
    (DATA / "bot_calc.json").write_text(json.dumps(calc_data(rates), ensure_ascii=False))   # калькулятор в боте — те же данные, что на странице
    (DATA / "bot_cars.json").write_text(json.dumps({"date": ddmm(TODAY), "rate": f'{rates["vtb"]:.2f}'.replace(".", ","), "cars": cars, "models": mods},
                                                   ensure_ascii=False, indent=0))


def main():
    global NW, NH, ASSET_V
    offline = "--offline" in sys.argv
    IMG.mkdir(parents=True, exist_ok=True)
    fonts()
    NW, NH = brand()
    css, js = (NEW / "src" / "s.css").read_text(), (NEW / "src" / "s.js").read_text()
    ASSET_V = hashlib.md5((css + js).encode()).hexdigest()[:8]
    (OUT / "s.css").write_text(css)
    (OUT / "s.js").write_text(js)
    road = MTK / "kp" / "fon_a4_polnyy.jpg"
    webp(road, IMG / "road.webp", 1600, 74, crop=(0, 700, 1400, 1700))
    webp(road, IMG / "road_m.webp", 900, 74)
    webp(road, IMG / "fin_m.webp", 900, 74, crop=(0, FIN_M_TOP, 1400, 1980))   # нижний блок на телефоне — без лишнего неба (Юрий 27.10.2026)
    shutil.copyfile(NEW / "src" / "og_yu7.jpg", IMG / "og_yu7.jpg")   # превью ссылки: кадр из видео первого экрана (Юрий 17.10)
    for n in ("d_xrv_1", "d_xrv_2", "d_q05_1", "d_q05_2", "d_yaris_1", "d_yaris_2", "d_coolray_1", "d_coolray_2", "yura", "gleb", "ivan"):
        shutil.copy2(MAIN_IMG / f"{n}.webp", IMG / f"{n}.webp")
    kicks = ROOT.parent / "foto-inbox-mtk" / "kicks-xv-2022"
    webp(kicks / "1.jpg", IMG / "k_1.webp", 1280, 74)
    for k, _, src in DOCS:
        webp(AC / "kp_v3" / "docs_light" / f"{src}.png", IMG / "docs" / f"{k}.webp", 1240, 82)
        webp(AC / "kp_v3" / "docs_light" / f"{src}.png", IMG / "docs" / f"{k}_t.webp", 520, 76)
    for n in ("vydannye", "mopedy", "kontakty"):           # шапки разделов: машина или мопед на синем фоне (Nano Banana, Юрий 27.10.2026)
        cut = NEW / "src" / f"ph_{n}.png"                  # вырезан из фона (rembg), за ним фон шапки — мопед: «тёмное пятно» (Юрий 27.10.2026)
        webp(cut if cut.exists() else NEW / "src" / f"ph_{n}.jpg", IMG / "ph" / f"{n}.webp", 1500, 82 if cut.exists() else 80, alpha=cut.exists())
    import ph_anim
    for n in ph_anim.SCENES:                               # мопед и прицеп въезжают в кадр (Юрий 27.10.2026)
        ph_anim.fresh(n)
    for k in range(4):
        deck_img(k, IMG / f"sec{k}.webp", 2200, 74)
        deck_img(k, IMG / f"sec{k}_m.webp", 1100, 74)
        deck_img(k, IMG / f"tile{k}.webp")

    cbr = cbr_rates(offline)
    vtb, src = day_rate(cbr, offline)
    print(f"курс юаня на {ddmm(TODAY)}: {vtb} — {src}")
    rates = {"vtb": vtb, "vtb_src": src, "cny": cbr["cny"], "eur": cbr["eur"], "usd": cbr.get("usd"), "cbr_date": cbr["date"]}
    models = load_models(rates)
    for m in models:
        model_imgs(m)
    live_m = {m["slug"] for m in models}                 # страницы и фото моделей, убранных из каталога («Авто» 20.10.2026);
    for x in (OUT / "katalog").glob("*/index.html"):     # их старые адреса nginx сервера сайта отправляет на каталог (301)
        if x.parent.name not in live_m:
            x.unlink()
            x.parent.rmdir()
    live_i = {f'{m["stem"]}{t}.webp' for m in models for t in ("", "_c")}
    for x in (IMG / "m").glob("*.webp"):
        if x.name not in live_i:
            x.unlink()
    kp = load_kp(rates)
    for c in kp:
        kp_imgs(c)
    kp = [c for c in kp if c.get("imgs")]
    live = {c["slug"] for c in kp}
    for d in (OUT / "avto", IMG / "kp"):                # страницы и фото машин, которых больше нет в списке
        for x in (d.iterdir() if d.exists() else []):
            if x.is_dir() and x.name not in live:
                shutil.rmtree(x)
    faq = json.loads((DATA / "faq.json").read_text()) if (DATA / "faq.json").exists() else []

    PAGES.clear()
    home(models, kp, rates, faq)
    catalog_page(models)
    if (DATA / "premium.json").exists():
        premium_page(json.loads((DATA / "premium.json").read_text()), rates)
    for m in models:
        model_page(m, models, kp)
    if kp:
        avto_page(kp, rates)
        for c in kp:
            car_page(c, kp, models, rates)
    moto = load_moto(rates)
    if moto and moto["mopeds"]:
        moto_page(moto)
    how_page(faq)
    price_page(kp, rates)
    calc_page(rates)
    deliv_page()
    if faq:
        faq_page(faq)
    contacts_page()
    politika_page()
    bot_data(models, kp, rates)
    extras(models, kp, rates, moto)
    (DATA / "last_build.json").write_text(json.dumps({"date": TODAY.isoformat(), "rates": rates, "models": len(models), "kp": len(kp), "pages": len(PAGES)}, ensure_ascii=False, indent=1))
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"страниц {len(PAGES)}, моделей {len(models)}, машин {len(kp)}, курс {vtb} ({src}), ЦБ {cbr['cny']:.4f}/{cbr['eur']:.2f}, всего {size / 1e6:.1f} МБ")


if __name__ == "__main__":
    main()
