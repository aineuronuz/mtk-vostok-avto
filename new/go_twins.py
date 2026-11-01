#!/usr/bin/env python3
"""Двойники страниц МТК на go.mtk-vostok-avto.ru — картинка в превью Telegram (Юрий 01.11.2026).

Telegram не достаёт до сервера сайта в Москве, и ссылки на mtk-vostok-avto.ru идут без картинки.
Двойник лежит на GitHub Pages (репо aineuronuz/mtk-go, локально ~/yurazol-sites/mtk-go): те же заголовок,
описание и картинка, что у страницы сайта, а посетителя он сразу переводит на тот же адрес mtk-vostok-avto.ru.
Переход — скриптом, не meta refresh: так Telegram читает картинку двойника, а не идёт за ним на сервер сайта.

  python3 new/go_twins.py [путь …]   по умолчанию — разделы из PAGES; затем commit и push в mtk-go
  --no-push                          только собрать
"""
import argparse
import html
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = Path.home() / "yurazol-sites" / "mtk-go"
SITE, GO = "https://mtk-vostok-avto.ru", "https://go.mtk-vostok-avto.ru"
PAGES = ["", "katalog/", "avto/", "premium/", "mopedy/", "kalkulyator/", "stoimost/", "kak-kupit/",
         "voprosy/", "kontakty/", "vydannye/"]
META = re.compile(r'<meta (?:property|name)="((?:og|twitter):[a-z:_]+|description)" content="([^"]*)">')
JUMP = f'<script>location.replace("{SITE}"+location.pathname+location.search+location.hash)</script>'


def image(url):
    """Картинку страницы — в mtk-go/img/, jpg или png; вернуть её адрес на go."""
    src = DOCS / url.removeprefix(SITE + "/").split("?")[0]
    im = Image.open(src)
    name = src.relative_to(DOCS / "img").with_suffix(".png" if src.suffix == ".png" else ".jpg")
    dst = OUT / "img" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in (".jpg", ".jpeg", ".png"):
        shutil.copyfile(src, dst)
    else:
        im.convert("RGB").save(dst, quality=86, optimize=True, progressive=True)
    return f"{GO}/img/{name.as_posix()}", im.size


def twin(path):
    s = (DOCS / path / "index.html").read_text()
    title = re.search(r"<title>([^<]*)</title>", s).group(1)
    tags, size = [], None
    for k, v in META.findall(s):
        if k in ("og:image", "twitter:image"):
            v, size = image(html.unescape(v))
        elif k == "og:url":
            v = f"{GO}/{path}"
        elif k.startswith("og:image:"):
            continue
        attr = "property" if k.startswith("og:") else "name"
        tags.append(f'<meta {attr}="{k}" content="{v}">')
    if size:
        tags.append(f'<meta property="og:image:width" content="{size[0]}"><meta property="og:image:height" content="{size[1]}">')
    page = (f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>'
            f'<meta name="robots" content="noindex">{"".join(tags)}{JUMP}</head>'
            f'<body><p><a href="{SITE}/{path}">{title}</a></p></body></html>\n')
    (OUT / path).mkdir(parents=True, exist_ok=True)
    (OUT / path / "index.html").write_text(page)


def git(*a):
    subprocess.run(["git", "-C", str(OUT), "-c", "user.name=aineuronuz", "-c", "user.email=aineuronuz@users.noreply.github.com", *a], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*"), ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    (OUT / "CNAME").write_text("go.mtk-vostok-avto.ru\n")
    (OUT / ".nojekyll").write_text("")
    # адреса без двойника — тоже на сайт, только без картинки в превью
    (OUT / "404.html").write_text(f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>МТК Восток-Авто</title>'
                                  f'<meta name="robots" content="noindex">{JUMP}</head>'
                                  f'<body><p><a href="{SITE}/">МТК Восток-Авто</a></p></body></html>\n')
    paths = [p.strip("/") + "/" if p.strip("/") else "" for p in a.paths] or PAGES
    for p in paths:
        twin(p)
    print(f"{len(paths)} двойников в {OUT}")
    if a.no_push:
        return
    git("add", "-A")
    if subprocess.run(["git", "-C", str(OUT), "diff", "--cached", "--quiet"]).returncode:
        git("commit", "-q", "-m", f"Двойники для превью в Telegram: {', '.join('/' + p for p in paths)}"
            "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
        git("push", "-q", "-u", "origin", "main")


if __name__ == "__main__":
    main()
