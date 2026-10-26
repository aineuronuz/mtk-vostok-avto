#!/bin/bash
# Новые КП «Авто» — на сайт в тот же день (Юрий 26.10.2026): cron каждые 30 минут, работает с 10 до 22 МСК. Если сделки
# kp_v3/deals, углы табличек plates_kp.json или фото сделок изменились с прошлой сборки — сборка по сегодняшнему курсу
# (--offline, курс записал утренний daily.sh) и выкладка. Утром в 09:30 всё делает daily.sh.
set -e
H=$(TZ=Europe/Moscow date +%-H)
if [ "$H" -lt 10 ] || [ "$H" -gt 22 ]; then exit 0; fi
cd /home/sergei/yurazol-sites/mtk-vostok-avto.ru
SUM=$(new/kp_sum.sh)
if [ "$SUM" = "$(cat new/data/kp_deals.md5 2>/dev/null)" ]; then exit 0; fi
echo "== $(date '+%F %T') КП изменились"
git pull -q --rebase
python3 new/site.py --offline
echo "$SUM" > new/data/kp_deals.md5
git add -A docs new/data/kp_deals.md5 new/data/mopedy.json
if ! git diff --cached --quiet; then
  git -c user.name=aineuronuz -c user.email=aineuronuz@users.noreply.github.com commit -q -m "Машины из новых КП на $(date +%d.%m.%Y)"
  git push -q
  echo "отправлено"
fi
