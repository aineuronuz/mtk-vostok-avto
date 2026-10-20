#!/usr/bin/env python3
"""Страница фото для КП: папка с фото и подпись → mtk-vostok-avto.ru/foto/<адрес>/ на сайте (задача «Авто» 20.10.2026).

  python3 new/foto_page.py <адрес> <папка> "<подпись>" [--note "Юрий 20.10"]
      фото в порядке номеров (car1, car2, … или любые имена с числом), оригиналы → <n>.jpg, превью 640 px → t/<n>.jpg,
      страница по new/foto_page.tpl.html, затем commit, push, обновление сервера сайта и проверка, что всё открывается.
  --check   собрать во временную папку и сравнить с уже выложенной docs/foto/<адрес>/, ничего не меняя.
  --force   перезаписать уже выложенную страницу.
  --no-push только собрать в docs/foto/.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
FOTO = ROOT / "docs" / "foto"
TPL = ROOT / "new" / "foto_page.tpl.html"
BOX = Path.home() / "yurazol-sites" / "tools" / "rina-box"      # вход на сервер сайта (ACCESS.md, «Сервер Рины»)
EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIDE = 2000                                                  # больше — уменьшаем, меньше — кладём как есть


def photos(src):
    fs = [f for f in src.iterdir() if f.suffix.lower() in EXT]
    num = lambda f: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", f.stem)]
    return sorted(fs, key=num)


def plural(n):
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} фотография"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f"{n} фотографии"
    return f"{n} фотографий"


def build(src, dst, name):
    fs = photos(src)
    if not fs:
        sys.exit(f"в {src} нет фото")
    (dst / "t").mkdir(parents=True, exist_ok=True)
    links = []
    for n, f in enumerate(fs, 1):
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        if f.suffix.lower() in (".jpg", ".jpeg") and max(im.size) <= MAX_SIDE and not Image.open(f).getexif().get(0x0112, 1) > 1:
            shutil.copyfile(f, dst / f"{n}.jpg")
        else:
            big = im.copy()
            big.thumbnail((MAX_SIDE, MAX_SIDE))
            big.save(dst / f"{n}.jpg", quality=86, optimize=True, progressive=True)
            im = big
        w, h = im.size
        t = im.copy()
        t.thumbnail((640, 640))
        t.save(dst / "t" / f"{n}.jpg", quality=82, optimize=True, progressive=True)
        links.append(f'<a href="{n}.jpg" data-pswp-width="{w}" data-pswp-height="{h}" aria-label="Фото {n}"><img src="t/{n}.jpg" '
                     f'alt="{name}, фото {n}" width="{w}" height="{h}" loading="{"eager" if n <= 6 else "lazy"}"><span>{n}</span></a>')
    s = (TPL.read_text().replace("@@NAME@@", name).replace("@@COUNT_TEXT@@", plural(len(fs)))
         .replace("@@COUNT@@", str(len(fs))).replace("@@LINKS@@", "\n".join(links)))
    (dst / "index.html").write_text(s)
    return len(fs)


def same(a, b):
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    if fa != fb:
        return f"разные файлы: {sorted(set(map(str, fa)) ^ set(map(str, fb)))}"
    diff = [str(p) for p in fa if (a / p).read_bytes() != (b / p).read_bytes()]
    return f"отличаются: {diff}" if diff else ""


def git(*a):
    subprocess.run(["git", "-C", str(ROOT), "-c", "user.name=aineuronuz", "-c", "user.email=aineuronuz@users.noreply.github.com", *a], check=True)


def live(slug, n):
    """Обновить сервер сайта с GitHub и проверить страницу и все фото на нём самом."""
    files = " ".join([""] + [f"{i}.jpg t/{i}.jpg" for i in range(1, n + 1)])
    cmd = (f'/usr/local/bin/mtk-vostok-avto-pull >/dev/null 2>&1; B=https://mtk-vostok-avto.ru/foto/{slug}/; '
           f'R="--resolve mtk-vostok-avto.ru:443:127.0.0.1"; ok=0; bad=""; for p in "" {files}; do '
           f'c=$(curl -s -o /dev/null -w %{{http_code}} $R $B$p); [ "$c" = 200 ] && ok=$((ok+1)) || bad="$bad $p:$c"; done; '
           f'echo "$ok/{2 * n + 1}$bad"')
    out = subprocess.run([sys.executable, "-I", str(BOX), cmd, "120"], capture_output=True, text=True).stdout.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug"), ap.add_argument("src", type=Path), ap.add_argument("name")
    ap.add_argument("--note", default=""), ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true"), ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9-]+", a.slug):
        sys.exit("адрес — латиница, цифры и дефис")
    dst = FOTO / a.slug
    url = f"https://mtk-vostok-avto.ru/foto/{a.slug}/"
    if a.check:
        with tempfile.TemporaryDirectory() as tmp:
            n = build(a.src, Path(tmp), a.name)
            d = same(Path(tmp), dst)
        print(f"{url}: {n} фото, " + (f"НЕ совпадает с выложенной — {d}" if d else "собрано так же, как выложено"))
        sys.exit(1 if d else 0)
    if dst.exists() and not a.force:
        sys.exit(f"{dst} уже есть — --force, чтобы перезаписать")
    if dst.exists():
        shutil.rmtree(dst)
    if not a.no_push:
        git("pull", "-q", "--rebase")
    n = build(a.src, dst, a.name)
    if a.no_push:
        print(f"{dst}: {n} фото, не выложено")
        return
    git("add", str(dst))
    git("commit", "-q", "-m", f"Фото {a.name} для КП" + (f" ({a.note})" if a.note else "")
        + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    git("push", "-q")
    res = live(a.slug, n)
    print(f"{url}: {n} фото, на сервере сайта открывается {res or 'нет ответа от сервера'}")
    if not res.startswith(f"{2 * n + 1}/"):
        sys.exit(1)


if __name__ == "__main__":
    main()
