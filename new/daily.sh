#!/bin/bash
# Каждый день: курс ЦБ и ВТБ (запасной — ЦБ × 1,0211) на сегодня, курс дня — new/data/kurs_dnya.json → цены под ключ на сайте → GitHub Pages
# cron в 07:30 и 08:30 по серверу (Берлин, зимой и летом разное смещение от МСК); с --cron работает только запуск в 09:30 МСК (25.10.2026)
set -e
if [ "$1" = "--cron" ] && [ "$(TZ=Europe/Moscow date +%H)" != "09" ]; then exit 0; fi
cd /home/sergei/yurazol-sites/mtk-vostok-avto.ru
echo "== $(date '+%F %T')"
git pull -q --rebase
python3 new/site.py
git add -A docs new/data/rates.json new/data/last_build.json new/data/kurs_dnya.json
if ! git diff --cached --quiet; then
  git -c user.name=aineuronuz -c user.email=aineuronuz@users.noreply.github.com commit -q -m "Цены под ключ на $(date +%d.%m.%Y)"
  git push -q
  echo "отправлено"
  python3 new/indexnow.py || true   # Яндекс и Bing узнают о новых ценах сразу
fi
