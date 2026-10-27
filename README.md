# mtk-vostok-avto.ru — сайт «МТК Восток-Авто»

GitHub Pages из папки `docs/` (ветка main), домен в `docs/CNAME`. Сайт собирает `new/site.py` (с 06.10.2026; цены — cron `new/daily.sh`). `build.py` — старый одностраничный сайт, не запускать.

Курс дня (ВТБ, запасной ЦБ × 1,0211) — `new/data/kurs_dnya.json`, его пишет `new/site.py` три раза в день, в 10:05, 14:05 и 18:05 МСК (cron, `new/daily.sh`; Юрий 27.10.2026, до того раз в день в 09:30); по нему пересчитываются «Каталог», «Авто в Китае» и «Премиум».

Страница «Премиум» (`/premium/`, новые премиальные автомобили из Китая, с 11.10.2026): данные и фото готовит `new/premium.py` (модели — премиум-каталог `~/auto-china/catalog/cars_prem26`, фото — `~/auto-china/catalog/site_photos`) в `new/data/premium.json` и `docs/img/p/`; страницу рисует `new/site.py`. После смены моделей или фото: `python3 new/premium.py && python3 new/site.py --offline`.

Страница «Мопеды» (`/mopedy/`, электромопеды «Восток-Мото», с 26.10.2026): данные и фото — выгрузка проекта «Мото» `~/KATE/мото/catalog/out/site/` (mopedy.json и foto/), сайт их не правит и не пересчитывает цены; `new/site.py` копирует json в `new/data/mopedy.json`, фото — в `docs/img/moto/`. После новой выгрузки: `python3 new/site.py --offline`.

Машины из КП («Авто в Китае», лента на главной): июнь–сентябрь — `new/data/kp_cars.json`, с 06.10.2026 — сделки «Авто» `~/auto-china/kp_v3/deals/*.py`, их читает `new/kp_deals.py` при каждой сборке (цена — `price.calc_deal`, формула КП; фото с табличкой «ВОСТОК-АВТО» — кэш `~/yurazol-sites/cache/kp_deals`). Новые КП попадают на сайт в тот же день: `new/kp_watch.sh` (cron каждые 30 минут, 10–22 МСК) пересобирает сайт, если сделки изменились (`new/kp_sum.sh`, `new/data/kp_deals.md5`).

Объявления che168 (площадка Autohome) в «Авто в Китае»: `new/che_feed.py` каждое утро (10:05 МСК) из `daily.sh` добавляет 5 машин — бензин, 3–5 лет на день ввоза, до 160 л.с., модели каталога, разные марки; продавцы-экспортёры в Россию (русский текст, «出口») отсекаются. Данные `new/data/che_cars.json` (только добавляются, снятые объявления остаются), фото с табличкой «ВОСТОК-АВТО» — `~/yurazol-sites/che-photos/` (детектор номеров `new/plate_detect.py`, модели `~/yurazol-sites/tools/plate_models`).
