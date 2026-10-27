#!/bin/bash
# Три раза в день: курс ЦБ и ВТБ (запасной — ЦБ × 1,0211), курс дня — new/data/kurs_dnya.json → цены под ключ на сайте → GitHub Pages
# cron каждый час в :05 по серверу (Берлин, зимой и летом разное смещение от МСК); с --cron работает только в 10:05, 14:05 и 18:05 МСК —
# новый курс ВТБ и пересчёт цен. С --che (cron каждый час в :30) только в 09:30 МСК: 5 объявлений che168 в данные, на сайт они выходят
# сборкой в 10:05 (Юрий 27.10.2026; до того всё раз в день в 09:30). Без ключей — всё сразу: объявления, курс, сборка.
set -e
H=$(TZ=Europe/Moscow date +%H)
if [ "$1" = "--cron" ]; then case "$H" in 10|14|18) ;; *) exit 0 ;; esac; fi
if [ "$1" = "--che" ] && [ "$H" != "09" ]; then exit 0; fi
cd /home/sergei/yurazol-sites/mtk-vostok-avto.ru
echo "== $(date '+%F %T')"
git pull -q --rebase --autostash
SUM=$(new/kp_sum.sh)                       # отпечаток КП «Авто» до сборки — kp_watch.sh не пересобирает то же самое
if [ "$1" != "--cron" ]; then
  timeout 2400 python3 new/che_feed.py 5 || echo "che168: ошибка, сборка без новых объявлений"   # 5 машин из объявлений в день (Юрий 26.10.2026)
  if [ "$1" = "--che" ]; then exit 0; fi
fi
python3 new/site.py
echo "$SUM" > new/data/kp_deals.md5
git add -A docs new/data/rates.json new/data/last_build.json new/data/kurs_dnya.json new/data/mopedy.json new/data/kp_deals.md5 new/data/che_cars.json new/data/che_series.json new/data/che_specs.json new/data/che_skip.json
if ! git diff --cached --quiet; then
  git -c user.name=aineuronuz -c user.email=aineuronuz@users.noreply.github.com commit -q -m "Цены под ключ на $(TZ=Europe/Moscow date '+%d.%m.%Y %H:%M')"
  git push -q
  echo "отправлено"
  python3 new/indexnow.py || true   # Яндекс и Bing узнают о новых ценах сразу
fi
