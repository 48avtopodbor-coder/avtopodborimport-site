"""
scraper.py — сборщик б/у авто che168 через API мобильного сайта (без www, капчи и браузера).

Поиск API отдаёт не больше ~500 машин на один запрос, а в обычном порядке ещё и перемешивает их.
Поэтому каждый бренд делится на части («срезы») по году, цене и при необходимости пробегу так,
чтобы в каждой было не больше CAP машин, и каждый срез листается в порядке цены.
Годы — MIN_YEAR..MAX_YEAR из config.py для расчётной даты растаможки.

Запуск:
    python3 scraper.py                    # полный проход: все машины нужных лет по всем брендам
    python3 scraper.py --brand Exeed      # один бренд
    python3 scraper.py --pages 2          # для проверки: не больше 2 страниц на срез
    --no-details                          # не догружать цвет, фото и характеристики
    --every 660                           # по расписанию: проход, только если прошлый был 660+ минут назад

Код выхода: 0 — проход по списку сделан, 10 — ещё рано (--every), 1 — API просит паузу, проход не закончен.
"""

import calendar
import json
import os
import sys
import time

from loguru import logger
from config import TARGET_BRANDS, SUBBRAND_RULES, MIN_YEAR, MAX_YEAR
import che168_api as api
from database import init_db, save_cars, get_stats, get_conn
from details import fetch_details

PAGE_SIZE = 20                  # больше API за раз не отдаёт
MAX_PAGES = 25                  # глубже 25 страниц (500 машин) API повторяет уже выданное
CAP = 400                       # машин в срезе — с запасом меньше лимита выдачи
SORT_MAIN, SORT_SPARE = 1, 2    # 1 — по цене (сверху дорогие); 2 — запасной порядок, добирает пропуски
MIN_COVERAGE = 0.97             # если срез собран хуже — второй проход в запасном порядке
PRICE_START = ((0, 10), (10, 20), (20, 30), (30, 50), (50, 1000))     # 万 юаней, границы включаются
MILEAGE_SPLIT = ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 100))     # 万 км
NOT_DUE = 10                    # код выхода: проход по списку ещё не нужен (--every)
LIST_DONE = os.path.join(api.DATA, "last_list_done")    # отметка конца последнего полного прохода
RAW_KEYS = ("infoid", "carname", "price", "mileage", "firstregyear", "cname", "cityid", "dealerid",
            "seriesid", "specid", "sname", "syname", "displacement", "environmental", "isnewly", "url")

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | {level} | {message}")
logger.add("data/scraper.log", rotation="10 MB", retention="7 days")


def _num(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def _dur(minutes):
    m = int(round(max(0, minutes)))
    return "{} ч {} мин".format(m // 60, m % 60) if m >= 60 else "{} мин".format(m)


def last_pass_time():
    """Когда закончился последний полный проход по списку (unix; 0 — не было)."""
    try:
        return os.path.getmtime(LIST_DONE)
    except OSError:
        pass
    with get_conn() as conn:        # до первого прохода этой версии — по последней машине, увиденной в списке
        t = conn.execute("SELECT MAX(seen_at) FROM cars").fetchone()[0]
    try:
        return calendar.timegm(time.strptime(str(t)[:19], "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return 0


def brand_ids() -> dict:
    """{бренд по-русски: id в API}. Берётся из data/brands.json, недостающие — из API."""
    path = os.path.join(api.DATA, "brands.json")
    try:
        with open(path, encoding="utf-8") as f:
            ids = json.load(f)
    except (OSError, ValueError):
        ids = {}
    if any(b["name_ru"] not in ids for b in TARGET_BRANDS):
        found = api.brands()
        for b in TARGET_BRANDS:
            if b["name_ru"] not in ids and b["name_cn"] in found:
                ids[b["name_ru"]] = found[b["name_cn"]]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ids, f, ensure_ascii=False)
    return ids


def to_car(item: dict, brand: dict) -> dict:
    infoid = str(item.get("infoid") or "")
    y = str(item.get("firstregyear") or "")[:4]
    price = _num(item.get("price"))
    mileage = _num(item.get("mileage"))

    name_ru, name_cn = brand["name_ru"], brand["name_cn"]
    title = "{} {}".format(item.get("carname") or "", item.get("sname") or "").upper()
    for rule in SUBBRAND_RULES:
        if rule["parent"] == name_ru and any(k.upper() in title for k in rule["keywords"]):
            name_ru, name_cn = rule["name_ru"], rule["name_cn"]

    dealer = str(item.get("dealerid") or "")
    img = str(item.get("imageurl") or "")
    url = str(item.get("url") or "")
    if dealer and dealer != "0":
        url = "https://www.che168.com/dealer/{}/{}.html".format(dealer, infoid)
    elif url.startswith("//"):
        url = "https:" + url
    elif not url:
        url = "https://m.che168.com/cardetail/index?infoid={}".format(infoid)

    return {
        "listing_id": infoid,
        "url": url,
        "brand_ru": name_ru,
        "brand_cn": name_cn,
        "model": item.get("carname"),
        "year": int(y) if y.isdigit() else None,
        "mileage_km": int(round(mileage * 10000)) if mileage else None,
        "price_wan": price,
        "price_cny": int(round(price * 10000)) if price else None,
        "city": item.get("cname"),
        "images": ("https:" + img) if img.startswith("//") else (img or None),
        "series_name": item.get("sname"),
        "spec_id": str(item.get("specid") or "") or None,
        "dealer_id": dealer or None,
        "displacement": str(item.get("displacement") or "") or None,
        "environmental": item.get("environmental"),
        "raw_data": json.dumps({k: item[k] for k in RAW_KEYS if k in item}, ensure_ascii=False),
    }


class Run:
    """Счётчики прохода."""
    def __init__(self):
        self.ids = set()
        self.seen = set()
        self.new = 0
        self.leaves = 0
        self.waits = 0
        self.stopped = False
        self.bad_mileage = set()


def query(bid, page, sort, f, run):
    """Одна страница среза f (словарь фильтров). Ждёт конца паузы API. None — не удалось."""
    for attempt in range(3):
        r = api.search(bid, page=page, size=PAGE_SIZE, sort=sort, **f)
        if r is not None:
            return r
        until = api.cooldown_until(api.SEARCH_HOST)
        if until:
            if run.waits >= 4:
                run.stopped = True
                return None
            run.waits += 1
            logger.warning("   жду конца паузы API до {}", time.strftime("%H:%M", time.localtime(until)))
            time.sleep(max(0, until - time.time()) + 5)
        else:
            time.sleep(10)
    return None


def keep(items, brand, run, got, seen):
    """Сохраняет машины нужных лет (их id — в got). В seen — все машины выдачи, включая другие годы:
    по ним считается полнота среза (в «6 лет» che168 попадают и машины конца 2020 г.)."""
    for i in items:
        if i.get("infoid"):
            seen.add(str(i["infoid"]))
            run.seen.add(str(i["infoid"]))
    cars = [to_car(i, brand) for i in items]
    cars = [c for c in cars if c["listing_id"] and c["year"] and MIN_YEAR <= c["year"] <= MAX_YEAR]
    run.new += save_cars(cars)
    for c in cars:
        got.add(c["listing_id"])
        run.ids.add(c["listing_id"])


def leaf(bid, brand, f, first, run, max_pages):
    """Листает срез, в котором машин не больше CAP. Первая страница уже получена."""
    _, total, pages = first
    pages = min(pages, max_pages)
    got, seen = set(), set()
    keep(first[0], brand, run, got, seen)
    for sort, start in ((SORT_MAIN, 2), (SORT_SPARE, 1)):
        if sort == SORT_SPARE and (len(seen) >= total * MIN_COVERAGE or pages < first[2]):
            break
        for p in range(start, pages + 1):
            r = query(bid, p, sort, f, run)
            if r is None or not r[0]:
                break
            keep(r[0], brand, run, got, seen)
    run.leaves += 1
    return got, seen


def collect_brand(brand, bid, age, max_pages, run):
    """Все машины бренда: делит запрос на срезы до CAP машин и листает каждый. Возвращает (по API, собрано)."""
    name = brand["name_ru"]
    this_year = time.localtime().tm_year
    got, seen = set(), set()
    whole = None

    def take(result):
        got.update(result[0])
        seen.update(result[1])

    stack = [({"agerange": age}, None)]
    while stack and not run.stopped:
        f, parent_total = stack.pop()
        key = (f["agerange"], f.get("price"))
        if "mileage" in f and key in run.bad_mileage:
            continue
        first = query(bid, 1, SORT_MAIN, f, run)
        if first is None:
            logger.error("   {}: срез {} не получен", name, f)
            continue
        items, total, _ = first
        if whole is None:
            whole = total
            logger.info("{} (id {}): {} машин", name, bid, total)
        if "mileage" in f and parent_total is not None and total >= parent_total:
            run.bad_mileage.add(key)              # фильтр пробега не сработал — дальше не дробится
            logger.warning("   {}: срез {} мельче не делится, беру первые {} машин", name, f, MAX_PAGES * PAGE_SIZE)
            take(leaf(bid, brand, {k: v for k, v in f.items() if k != "mileage"}, first, run, max_pages))
            continue
        if total <= CAP:
            take(leaf(bid, brand, f, first, run, max_pages))
            continue
        keep(items, brand, run, got, seen)        # первая страница большого среза тоже идёт в базу
        lo_age, hi_age = f["agerange"].split("-")
        if lo_age != hi_age:                      # 1) по году
            for year in range(MIN_YEAR, MAX_YEAR + 1):
                a = this_year - year + 1
                stack.append(({"agerange": "{}-{}".format(a, a)}, total))
        elif "price" not in f:                    # 2) по цене
            for lo, hi in PRICE_START:
                stack.append((dict(f, price="{}-{}".format(lo, hi)), total))
        else:
            lo, hi = (int(x) for x in f["price"].split("-"))
            if hi - lo > 1:                       # 3) цену пополам (граница входит в обе части)
                mid = (lo + hi) // 2
                stack.append((dict(f, price="{}-{}".format(mid, hi)), total))
                stack.append((dict(f, price="{}-{}".format(lo, mid)), total))
            elif "mileage" not in f:              # 4) по пробегу
                for a, b in MILEAGE_SPLIT:
                    stack.append((dict(f, mileage="{}-{}".format(a, b)), total))
            else:
                logger.warning("   {}: срез {} — {} машин, мельче не делится", name, f, total)
                take(leaf(bid, brand, f, first, run, max_pages))
        if run.leaves and run.leaves % 20 == 0:
            logger.info("   {}: найдено {} из {}", name, len(seen), whole)
    logger.info("   {}: найдено {} из {} ({}%), из них {}–{} г.: {}", name, len(seen), whole,
                round(100 * len(seen) / whole) if whole else 100, MIN_YEAR, MAX_YEAR, len(got))
    return whole or 0, len(got)


def main():
    args = sys.argv[1:]
    only = args[args.index("--brand") + 1] if "--brand" in args else None
    max_pages = int(args[args.index("--pages") + 1]) if "--pages" in args else MAX_PAGES
    every = float(args[args.index("--every") + 1]) if "--every" in args else None

    brands = [b for b in TARGET_BRANDS if not only or b["name_ru"].lower() == only.lower()]
    if not brands:
        logger.error("Бренд '{}' не найден в config.py", only)
        return
    init_db()
    if every:
        ago = (time.time() - last_pass_time()) / 60
        if ago < every:
            logger.info("Проход по списку был {} назад, следующий — через {}", _dur(ago), _dur(every - ago))
            sys.exit(NOT_DUE)
    until = api.cooldown_until(api.SEARCH_HOST)
    if until:
        logger.warning("API che168 на паузе до {}, запуск пропущен", time.strftime("%H:%M", time.localtime(until)))
        sys.exit(1)

    ids = brand_ids()
    age = api.age_range(MIN_YEAR, MAX_YEAR)
    run_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    logger.info("=== Старт: {} бренд(ов), годы {}–{} ===", len(brands), MIN_YEAR, MAX_YEAR)

    run = Run()
    api_total = 0
    for b in brands:
        bid = ids.get(b["name_ru"])
        if not bid:
            logger.error("{}: нет id бренда в API", b["name_ru"])
            continue
        total, _ = collect_brand(b, bid, age, max_pages, run)
        api_total += total
        if run.stopped:
            logger.error("API долго просит паузу — остальные бренды в следующий запуск")
            break

    if not run.stopped and not only and max_pages == MAX_PAGES:
        with open(LIST_DONE, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")

    if run.new and "--no-details" not in args:
        fetch_details(since=run_start)

    st = get_stats()
    logger.info("=== Готово. Найдено {} из {} по API, из них {}–{} г.: {}, новых {} | в базе {}, продаётся {}, "
                "с данными {} | запросов к API: {} ===", len(run.seen), api_total, MIN_YEAR, MAX_YEAR,
                len(run.ids), run.new, st["total"], st["active"], st["with_params"], api.stats["requests"])
    if run.stopped:
        sys.exit(1)


if __name__ == "__main__":
    main()
