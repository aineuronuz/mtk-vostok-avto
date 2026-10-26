"""«Авто в Китае»: каждое утро N = 5 машин из свежих объявлений che168 (二手车之家 — площадка Autohome), Юрий 26.10.2026.

Отбор: модели бензинового каталога сайта (cars_data: МОНОПРИВОД и ПОЛНЫЙ ПРИВОД), серия che168 — по китайскому имени (CN,
кэш data/che_series.json); первая регистрация — в окне, где машина на день ввоза (сегодня + 50…65 дней) точно 3–5 лет
(льготный утильсбор, запас 6 месяцев от пятилетнего края); бензин; мощность до 160 л.с. и объём — по Autohome spec;
не меньше 4 фото. Машины — разных моделей и марок, по очереди европейские, китайские, корейские, японские и любая
(ORDER), модель не повторяется 14 дней. Электро и гибриды не берём: 30-минутную мощность мотора по объявлению не проверить.
Цена под ключ — price.calc, как у машин из КП. Номера на фото — табличка «ВОСТОК-АВТО» (plate_detect.py).
Машина остаётся на сайте и после снятия объявления (Юрий 26.10.2026). Данные — data/che_cars.json (только добавляются),
фото — PHOTOS/<infoid>/ (вне репозитория, нужны каждой сборке). VIN и продавец на сайт не идут.
  python3 new/che_feed.py [N]      — в daily.sh перед сборкой, раз в день
"""
import hashlib
import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
import uuid
from datetime import date, timedelta
from pathlib import Path

NEW = Path(__file__).resolve().parent
DATA = NEW / "data"
CARS = DATA / "che_cars.json"
SERIES = DATA / "che_series.json"
SPECS = DATA / "che_specs.json"
SKIP = DATA / "che_skip.json"                                  # объявления, отклонённые при проверке, — не брать снова
PHOTOS = Path.home() / "yurazol-sites" / "che-photos"
AC = Path.home() / "auto-china"
MAX_PH = 8

K = "com.rnw.www"   # подпись мобильного API che168, как в ~/auto-china/catalog/audit_prem26/bu_2510/che168api.py («Авто» 25.10)
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
DEV = str(uuid.uuid4())
SEARCH = "https://api2scsou.che168.com/api/v11/search"
INFO = "https://apiuscdt.che168.com/apic/v3/car/getcarinfo"

# модель каталога → серия на che168 (китайское имя)
CN = {"Toyota Corolla (Levin)": "卡罗拉", "Toyota Yaris L": "YARiS L 致炫", "Audi A3 / A3L": "奥迪A3", "Audi A4L": "奥迪A4L",
      "Audi Q2L": "奥迪Q2L", "Audi Q3": "奥迪Q3", "BMW 1-Series седан": "宝马1系", "BMW X1": "宝马X1", "BMW X2 sDrive20i": "宝马X2",
      "BMW 320Li": "宝马3系", "Chevrolet Monza": "科鲁泽", "Chevrolet Onix": "科沃兹", "Ford Focus": "福克斯", "Ford Territory": "领界",
      "Honda Civic": "思域", "Honda Fit": "飞度", "Honda Vezel": "缤智", "Honda XR-V": "本田XR-V", "Hyundai Elantra": "伊兰特",
      "Hyundai ix25": "现代ix25", "Hyundai ix35": "现代ix35", "Hyundai Verna": "悦纳", "Kia K3 (Cerato)": "起亚K3", "Kia KX1": "起亚KX1",
      "Kia Pegas": "焕驰", "Mazda 3 Axella": "马自达3 昂克赛拉", "Mazda 6 Atenza": "阿特兹", "Mazda CX-4": "马自达CX-4",
      "Mazda CX-5": "马自达CX-5", "Mazda CX-30": "马自达CX-30", "Mercedes-Benz A-class L": "奔驰A级", "Mercedes-Benz GLA": "奔驰GLA",
      "Mercedes-Benz GLB": "奔驰GLB", "Nissan Qashqai": "逍客", "Nissan Sylphy": "轩逸", "Nissan Tiida": "骐达", "Nissan Kicks": "劲客",
      "Nissan X-Trail": "奇骏", "Nissan Altima": "天籁", "Skoda Kamiq": "柯米克", "Skoda Karoq": "柯珞克", "Skoda Octavia": "明锐",
      "Volkswagen Bora": "宝来", "Volkswagen Golf": "高尔夫", "Volkswagen Lamando L": "凌渡L", "Volkswagen Lavida": "朗逸",
      "Volkswagen Magotan": "迈腾", "Volkswagen Sagitar (Jetta)": "速腾", "Volkswagen Santana": "桑塔纳", "Volkswagen Tharu": "途岳",
      "Volkswagen Tharu XR": "途岳新锐", "Volkswagen Touran L": "途安L", "Volkswagen T-ROC": "探歌", "Volkswagen Tayron": "探岳",
      "Geely Colorful (Coolray)": "缤越", "Geely Binrui": "缤瑞", "Geely Emgrand L": "帝豪L", "Geely Emgrand": "帝豪", "Geely Emgrand S": "帝豪S",
      "Chery Arrizo 5 / 5 Plus / 5 GT": "艾瑞泽5", "Chery Tiggo 3x": "瑞虎3x", "Chery Tiggo 5x": "瑞虎5x", "Chery Tiggo 7": "瑞虎7",
      "Chery Tiggo 7 Plus": "瑞虎7 PLUS", "Chery Tiggo 8": "瑞虎8", "Chery Omoda 5": "欧萌达", "Jetour X70 / X70 Plus": "捷途X70",
      "Jetour Dashing": "捷途大圣", "Exeed LX": "星途LX", "Haval M6 PLUS": "哈弗M6", "Haval Chitu": "哈弗赤兔", "Changan CS35 Plus": "长安CS35PLUS",
      "Dongfeng Aeolus Yixuan": "奕炫", "Dongfeng Forthing T5": "风行T5", "Dongfeng Fengon S560": "风光S560", "Venucia D60": "启辰D60",
      "MG5": "名爵5", "MG ZS": "名爵ZS", "Roewe i5": "荣威i5", "Wuling Xingchi": "五菱星驰", "Wuling Victory": "五菱凯捷",
      "Wuling Jiachen": "五菱佳辰", "Jetta VS5": "捷达VS5", "Jetta VS7": "捷达VS7", "Livan X3 Pro": "睿蓝X3 PRO",
      "Subaru Forester": "森林人", "Subaru XV": "斯巴鲁XV", "Mitsubishi Eclipse Cross": "奕歌"}
ORIGIN = {"Audi": "eu", "BMW": "eu", "Mercedes-Benz": "eu", "Skoda": "eu", "Volkswagen": "eu", "Jetta": "eu",
          "Hyundai": "kr", "Kia": "kr", "Toyota": "jp", "Honda": "jp", "Nissan": "jp", "Mazda": "jp", "Subaru": "jp", "Mitsubishi": "jp",
          "Chevrolet": "us", "Ford": "us"}                      # остальные марки — китайские
ORDER = ["eu", "cn", "kr", "jp", None]                         # пятая — любая марка
COLOR = {"白色": "белый", "黑色": "чёрный", "灰色": "серый", "银色": "серебристый", "银灰色": "серебристый", "红色": "красный", "蓝色": "синий",
         "棕色": "коричневый", "咖啡色": "коричневый", "绿色": "зелёный", "黄色": "жёлтый", "橙色": "оранжевый", "香槟色": "шампань",
         "紫色": "фиолетовый", "金色": "золотистый"}


def signed(params, url):
    p = {k: str(v) for k, v in params.items()}
    p.update({"deviceid": DEV, "userid": "0", "s_pid": "0", "s_cid": "0", "_appid": "2sc.m", "v": "11.41.5", "_subappid": ""})
    p["_sign"] = hashlib.md5((K + "".join(k + p[k] for k in sorted(p)) + K).encode()).hexdigest()
    return url + "?" + urllib.parse.urlencode(p)


_B = {}


def _browser():
    """Chromium: сервер che168 временами отдаёт JS-проверку на бота (cookie EO_Bot_Ssid) — браузер её проходит, дальше
    запросы идут с его cookie (как che168pw.py «Авто», 25.10)."""
    if "ctx" not in _B:
        from playwright.sync_api import sync_playwright
        _B["p"] = sync_playwright().start()
        _B["b"] = _B["p"].chromium.launch(executable_path="/usr/bin/chromium")
        _B["ctx"] = _B["b"].new_context(user_agent=UA, locale="zh-CN", is_mobile=True, viewport={"width": 400, "height": 900})
        _B["pg"] = _B["ctx"].new_page()
        _B["pg"].goto("https://m.che168.com/", wait_until="domcontentloaded", timeout=60000)
        _B["pg"].wait_for_timeout(3000)
    return _B


def close():
    if "b" in _B:
        _B["b"].close()
        _B["p"].stop()
        _B.clear()


def api(params, url=SEARCH):
    b = _browser()
    for attempt in range(4):
        u = signed(params, url)
        try:
            t = b["ctx"].request.get(u, headers={"Referer": "https://m.che168.com/"}, timeout=30000).text()
            if t.lstrip().startswith("{"):
                j = json.loads(t)
                if j.get("returncode") == 0:
                    return j["result"]
            else:                                              # проверка на бота — пройти её страницей и повторить
                b["pg"].goto(u, wait_until="load", timeout=60000)
                b["pg"].wait_for_timeout(2500)
        except Exception as e:  # noqa: BLE001
            print("  che168:", str(e)[:120], flush=True)
        time.sleep(2 + attempt * 4)
    return None


def search(**kw):
    p = {"pageindex": 1, "pagesize": 50, "ishideback": 1, "srecom": 2, "cid": 0, "car_area": 1, "ssnew": 1}
    p.update(kw)
    return api(p) or {}


def norm(s):
    return re.sub(r"[\s·]", "", s or "").lower()


def series_id(name, cache):
    if name in cache:
        return cache[name]
    kw = CN.get(name)
    sid = None
    if kw:
        r = search(keywords=kw)
        if not r:
            return None                                        # поиск не ответил — не запоминаем
        cl = r.get("carlist") or []
        cnt = {}
        for x in cl:
            sn = re.split(r" 20\d\d款|/\d\d款| 20\d\d", x.get("carname") or "")[0]
            if norm(sn) == norm(kw) or norm(kw) in norm(sn):
                cnt[x["seriesid"]] = cnt.get(x["seriesid"], 0) + 1
        sid = max(cnt, key=cnt.get) if cnt else None
        time.sleep(0.5)
    cache[name] = sid
    SERIES.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    return sid


def spec(specid, cache):
    """Объём (см³), мощность ДВС (л.с.) и топливо по странице параметров Autohome (curl с сервера проходит, «Авто» 25.10)."""
    k = str(specid)
    if k in cache:
        return cache[k]
    r = subprocess.run(["curl", "-s", "-m", "30", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                        f"https://car.autohome.com.cn/config/spec/{specid}.html"], capture_output=True)
    html = r.stdout.decode("utf-8", "ignore")
    i = html.find("var config = ")
    got = {}
    if i >= 0:
        span = re.compile(r"<span class='hs_kw\d+_\w+'></span>")
        num = lambda s: float(m.group()) if (m := re.match(r"[\d.]+", s or "")) else None
        cfg, _ = json.JSONDecoder().raw_decode(html[i + len("var config = "):])
        secs = cfg["result"]["paramtypeitems"]
        ids = [v["specid"] for v in secs[0]["paramitems"][0]["valueitems"]]
        col = ids.index(specid) if specid in ids else None
        if col is not None:
            for sec in secs:
                sn = span.sub("", sec["name"])
                for p in sec["paramitems"]:
                    vi = p.get("valueitems") or []
                    v = span.sub("", (vi[col].get("value") if col < len(vi) else "") or "")
                    if p["id"] == 1182 and sn == "发动机":
                        got["cc"] = num(v)
                    elif p["id"] == 1294 and sn == "发动机":
                        got["ps"] = num(v)
                    elif p["id"] == 1149:
                        got["fuel"] = v
    cache[k] = got
    SPECS.write_text(json.dumps(cache, ensure_ascii=False))
    time.sleep(0.4)
    return got


VIN_YEAR = {"L": 2020, "M": 2021, "N": 2022, "P": 2023, "R": 2024, "S": 2025, "T": 2026}


def fresh_enough(info, ylo):
    """Год модели (20xx款) и год по VIN (10-й знак) — не раньше нижнего края окна: машина, выпущенная заметно раньше
    регистрации, на день ввоза может оказаться старше 5 лет."""
    my = re.search(r"(20\d\d)款", (info.get("carname") or "") + (info.get("specname") or ""))
    vin = (info.get("vincode") or "").strip()
    vy = VIN_YEAR.get(vin[9].upper()) if len(vin) == 17 else None
    return bool(my) and int(my.group(1)) >= ylo and (vy is None or vy >= ylo)


def export_seller(info):
    """Продавец-экспортёр в Россию: на его фото чужие водяные знаки и контакты (Юрий 26.10.2026 — только чистые объявления).
    Признаки — русский текст или «出口 / 俄罗斯 / export / Russia» в описании и в названии продавца."""
    txt = info.get("remark") or ""
    if info.get("dealerid"):
        d = api({"dealerid": info["dealerid"], "infoid": info["infoid"]}, "https://apiuscdt.che168.com/apic/v1/dealer/getdealerinfo") or {}
        txt += " " + ((d.get("dealer") or {}).get("dealername") or "")
    return bool(re.search(r"[А-Яа-яЁё]|俄罗斯|出口|export|russia", txt, re.I))


def window(today):
    """(с, по) — месяцы первой регистрации, при которых на день ввоза машине точно 3–5 лет."""
    a0, a1 = today + timedelta(days=50), today + timedelta(days=65)
    lo = date(a1.year - 5, a1.month, 1) + timedelta(days=184)
    hi = date(a0.year - 3, a0.month, 1) - timedelta(days=31)
    return (lo.year, lo.month), (hi.year, hi.month)


def catalog_models():
    sys.path.insert(0, str(AC / "catalog"))
    import cars_data
    return [m["name"] for c in cars_data.CATEGORIES if c["cat"] in ("МОНОПРИВОД", "ПОЛНЫЙ ПРИВОД") for p in c["pages"] for m in p["cars"]]


def photos(info, infoid):
    import plate_detect
    d = PHOTOS / str(infoid)
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for i, url in enumerate((info.get("piclist") or [])[:MAX_PH], 1):
        raw, dst = d / f"raw{i}.webp", d / f"{i}.jpg"
        if not dst.exists():
            subprocess.run(["curl", "-s", "-m", "40", "-A", UA, "-o", str(raw), url])
            if not raw.exists() or raw.stat().st_size < 5000:
                continue
            try:
                plate_detect.cover(raw, dst)
            except Exception as e:  # noqa: BLE001
                print("  фото", url, e)
                continue
            raw.unlink()
        out.append(str(dst))
    return out


def pick(n=5, today=None):
    today = today or date.today()
    cars = json.loads(CARS.read_text()) if CARS.exists() else []
    have = {c["che"]["infoid"] for c in cars}
    recent = {c["catalog_name"] for c in cars if c["che"]["added"] >= (today - timedelta(days=14)).isoformat()}
    n -= sum(c["che"]["added"] == today.isoformat() for c in cars)
    if n <= 0:
        print("che168: сегодня уже добавлены")
        return []
    have |= set(json.loads(SKIP.read_text())) if SKIP.exists() else set()
    ser = json.loads(SERIES.read_text()) if SERIES.exists() else {}
    specs = json.loads(SPECS.read_text()) if SPECS.exists() else {}
    extra = json.loads((DATA / "models.json").read_text()) if (DATA / "models.json").exists() else {}
    (ylo, mlo), (yhi, mhi) = window(today)
    rnd = random.Random(today.isoformat())
    models = catalog_models()
    rnd.shuffle(models)
    todays = [c for c in cars if c["che"]["added"] == today.isoformat()]
    added, used_brand = [], {c["brand"] for c in todays}                     # повторный запуск за день — те же правила
    got = {ORIGIN.get(c["brand"], "cn") for c in todays}
    wants = [o for o in ORDER if o is None or o not in got]
    for want in (wants + [None] * n)[:n]:
        for name in models:
            brand = name.split()[0]
            org = ORIGIN.get(brand, "cn")
            if name in recent or brand in used_brand or (want and org != want) or name not in CN:
                continue
            sid = series_id(name, ser)
            if not sid:
                continue
            cl = []
            for page in (1, 2):
                cl += search(seriesid=sid, agerange="3-5", pageindex=page, pagesize=30).get("carlist") or []
                time.sleep(0.5)
            cand = [x for x in cl if x.get("infoid") not in have and str(ylo) <= (x.get("firstregyear") or "")[:4] <= str(yhi)]
            rnd.shuffle(cand)
            car = None
            for x in cand[:8]:
                info = api({"infoid": x["infoid"], "offertype": 0, "ucuserauth": "", "gpscid": 0, "iscardetailab": "B",
                            "encryptinfo": "", "fromtag": 0, "pvareaid": ""}, INFO)
                time.sleep(0.6)
                if not info or info.get("fuelname") != "汽油" or len(info.get("piclist") or []) < 4:
                    continue
                m = re.match(r"(20\d\d)-(\d\d)", info.get("firstregdate") or "")
                if not m or not ((ylo, mlo) <= (int(m.group(1)), int(m.group(2))) <= (yhi, mhi)):
                    continue
                if not fresh_enough(info, ylo) or export_seller(info):
                    continue
                sp = spec(info.get("specid"), specs)
                if not sp.get("ps") or not sp.get("cc") or sp["ps"] > 160 or (sp.get("fuel") and "汽油" not in sp["fuel"]):
                    continue
                cny = round(float(info.get("price") or 0) * 10000)
                if cny < 20000:
                    continue
                car = (info, sp, int(m.group(1)), int(m.group(2)), cny)
                break
            if not car:
                continue
            info, sp, y, mo, cny = car
            ph = photos(info, info["infoid"])
            if len(ph) < 4:
                continue
            km = round(float(info.get("mileage") or 0) * 10000)
            dm = info.get("drivingmode") or ""
            drive = "полный" if "四驱" in dm else "задний" if "后驱" in dm else "передний"
            engine = (info.get("engine") or "").strip()
            title = re.sub(r"\s*\(.*?\)|\s*/.*", "", name).strip() + (f" {engine}" if engine else "")
            rec = {"slug": re.sub(r"[^a-z0-9]+", "-", f"{title} {y} {km}km che{info['infoid']}".lower()).strip("-"),
                   "title": title, "brand": brand, "model": " ".join(name.split()[1:]), "trim": None,
                   "year": y, "month": mo, "mileage_km": km, "kind": "ice", "fuel_label": "Бензин", "power_hp": round(sp["ps"]),
                   "power_kw": None, "volume_cc": round(sp["cc"]), "battery_kwh": None, "range_km": None, "drive": drive,
                   "awd": drive == "полный", "transmission": {"自动": "автомат", "手动": "механика"}.get(info.get("gearbox"), info.get("gearbox")),
                   "body": (extra.get(name) or {}).get("body"), "color": COLOR.get(info.get("colorname")), "cond": None,
                   "car_cny": cny, "delivery_cny": 20000, "loading_cny": 1300, "tax": "ice", "photos": ph,
                   "kp_date_iso": today.isoformat(), "catalog_name": name, "source": "che168",
                   "che": {"infoid": info["infoid"], "added": today.isoformat(), "city_cn": info.get("cname"), "specid": info.get("specid")}}
            cars.append(rec)
            have.add(info["infoid"])
            added.append(rec)
            used_brand.add(brand)
            CARS.write_text(json.dumps(cars, ensure_ascii=False, indent=1))
            print(f"che168: {title} {y}-{mo:02d}, {km} км, {sp['ps']:.0f} л.с., {cny} ¥, фото {len(ph)}", flush=True)
            break
    print(f"che168: добавлено {len(added)} из {n}")
    return added


if __name__ == "__main__":
    try:
        pick(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
    finally:
        close()
