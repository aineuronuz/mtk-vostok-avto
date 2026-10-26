#!/bin/bash
# Каждый день: курс ЦБ и ВТБ (запасной — ЦБ × 1,0211) на сегодня, курс дня — new/data/kurs_dnya.json → цены под ключ на сайте → GitHub Pages
# cron в 07:30 и 08:30 по серверу (Берлин, зимой и летом разное смещение от МСК); с --cron работает только запуск в 09:30 МСК (25.10.2026)
set -e
if [ "$1" = "--cron" ] && [ "$(TZ=Europe/Moscow date +%H)" != "09" ]; then exit 0; fi
cd /home/sergei/yurazol-sites/mtk-vostok-avto.ru
echo "== $(date '+%F %T')"
git pull -q --rebase
SUM=$(new/kp_sum.sh)                       # отпечаток КП «Авто» до сборки — kp_watch.sh не пересобирает то же самое
timeout 2400 python3 new/che_feed.py 5 || echo "che168: ошибка, сборка без новых объявлений"   # 5 машин из объявлений в день (Юрий 26.10.2026)
python3 new/site.py
echo "$SUM" > new/data/kp_deals.md5
git add -A docs new/data/rates.json new/data/last_build.json new/data/kurs_dnya.json new/data/mopedy.json new/data/kp_deals.md5 new/data/che_cars.json new/data/che_series.json new/data/che_specs.json new/data/che_skip.json
if ! git diff --cached --quiet; then
  git -c user.name=aineuronuz -c user.email=aineuronuz@users.noreply.github.com commit -q -m "Цены под ключ на $(date +%d.%m.%Y)"
  git push -q
  echo "отправлено"
  python3 new/indexnow.py || true   # Яндекс и Bing узнают о новых ценах сразу
fi
