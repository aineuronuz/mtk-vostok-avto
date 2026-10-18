"""IndexNow: сообщает Яндексу и Bing (через него — DuckDuckGo, ChatGPT-поиску, Copilot) все адреса из docs/sitemap.xml.
Запуск: python3 new/indexnow.py — после выкладки, его вызывает new/daily.sh. Ключ — new/data/search.json, файл ключа в корне сайта пишет site.py."""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "mtk-vostok-avto.ru"
key = json.loads((ROOT / "new" / "data" / "search.json").read_text())["indexnow"]
urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "docs" / "sitemap.xml").read_text())
body = json.dumps({"host": HOST, "key": key, "keyLocation": f"https://{HOST}/{key}.txt", "urlList": urls}).encode()
for api in ("https://yandex.com/indexnow", "https://api.indexnow.org/indexnow"):
    req = urllib.request.Request(api, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(api, r.status, len(urls), "адресов")
    except urllib.error.HTTPError as e:
        print(api, e.code, e.read()[:200].decode("utf-8", "replace"))
    except Exception as e:
        print(api, "ошибка", e)
