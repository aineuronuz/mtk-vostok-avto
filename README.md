# mtk-vostok-avto.ru — сайт «МТК Восток-Авто»

GitHub Pages из папки `docs/` (ветка main), домен в `docs/CNAME`. Сайт собирает `new/site.py` (с 06.10.2026; цены — cron `new/daily.sh`). `build.py` — старый одностраничный сайт, не запускать.

Курс дня (ВТБ, запасной ЦБ × 1,0211) — `new/data/kurs_dnya.json`, его пишет `new/site.py` каждое утро (cron, `new/daily.sh`); по нему пересчитываются «Каталог», «Авто в Китае» и «Премиум».

Страница «Премиум» (`/premium/`, новые премиальные автомобили из Китая, с 11.10.2026): данные и фото готовит `new/premium.py` (модели — премиум-каталог `~/auto-china/catalog/cars_prem26`, фото — `~/auto-china/catalog/site_photos`) в `new/data/premium.json` и `docs/img/p/`; страницу рисует `new/site.py`. После смены моделей или фото: `python3 new/premium.py && python3 new/site.py --offline`.

Страница «Мопеды» (`/mopedy/`, электромопеды «Восток-Мото», с 26.10.2026): данные и фото — выгрузка проекта «Мото» `~/KATE/мото/catalog/out/site/` (mopedy.json и foto/), сайт их не правит и не пересчитывает цены; `new/site.py` копирует json в `new/data/mopedy.json`, фото — в `docs/img/moto/`. После новой выгрузки: `python3 new/site.py --offline`.
