"""
enrich.py — проверка через открытый API che168 (apipcmusc), продаётся ли машина.

Запуск:
    python3 enrich.py --recheck    # перепроверить машины, которых давно не было в списке (цена, снята ли с продажи)
    python3 enrich.py --limit 5    # старый режим: подробности для машин без них (теперь это делает details.py)
"""

import sys
import json
import time
import urllib.request

from loguru import logger
from database import init_db, cars_to_enrich, update_details, get_conn
from sold_status import FailedResponses, is_sold_response

API = "https://apipcmusc.che168.com/v1/car/getcarinfo?_appid=2sc.pc&infoid="
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Referer": "https://www.che168.com/",
}
PAUSE = 1.0             # пауза между запросами, сек
MAX_ERRORS_IN_ROW = 20  # столько ошибок подряд — останавливаемся
RECHECK_HOURS = 20      # перепроверять машины, не обновлявшиеся дольше этого


def get_info(infoid: str) -> dict:
    req = urllib.request.Request(API + str(infoid), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def details_from(res: dict) -> dict:
    fields = {
        "series_name":    res.get("seriesname"),
        "spec_id":        str(res.get("specid") or ""),
        "city":           res.get("cname"),
        "province_id":    str(res.get("pid") or ""),
        "displacement":   str(res.get("displacement") or ""),
        "environmental":  res.get("environmental"),
        "first_reg_date": res.get("firstregdate"),
        "dealer_id":      str(res.get("dealerid") or ""),
        "dealer_name":    res.get("dealername"),
        "publish_date":   res.get("publicdate"),
        "details_json":   json.dumps(res, ensure_ascii=False),
        "is_active":      1,
    }
    img = res.get("imageurl") or ""
    if img:
        fields["images"] = "https:" + img if img.startswith("//") else img
    try:
        price = float(res.get("price") or 0)
    except (TypeError, ValueError):
        price = 0
    if price:
        fields["price_wan"] = price
        fields["price_cny"] = int(price * 10000)
    return fields


def recheck_from(res: dict) -> dict:
    """Перепроверка: машина ещё продаётся — обновляем только цену. Цвет, фото, описание и
    характеристики уже записал details.py, их не трогаем."""
    fields = {"is_active": 1}
    try:
        price = float(res.get("price") or 0)
    except (TypeError, ValueError):
        price = 0
    if price:
        fields["price_wan"] = price
        fields["price_cny"] = int(price * 10000)
    return fields


def process(ids: list, title: str, fields_from=details_from) -> dict:
    logger.info("{}: {} машин", title, len(ids))
    cnt = {"ok": 0, "sold": 0, "fail": 0, "err": 0}
    failed_responses = FailedResponses(logger)
    err_in_row = 0
    for i, infoid in enumerate(ids, 1):
        try:
            data = get_info(infoid)
            res = data.get("result")
            rc, msg = data.get("returncode"), data.get("message")
            if rc == 0 and res:
                update_details(infoid, fields_from(res))
                cnt["ok"] += 1
                err_in_row = 0
            elif is_sold_response(rc, msg):
                update_details(infoid, {"is_active": 0})
                cnt["sold"] += 1
                err_in_row = 0
            else:
                cnt["fail"] += 1
                err_in_row += 1
                failed_responses.log(infoid, rc, msg)
        except Exception as e:
            cnt["err"] += 1
            err_in_row += 1
            failed_responses.log(infoid, getattr(e, "code", None), str(e))
            time.sleep(5)
        if err_in_row >= MAX_ERRORS_IN_ROW:
            logger.error("{} ошибок подряд — останавливаюсь", err_in_row)
            break
        if i % 200 == 0:
            logger.info("   {}/{}: ok {ok}, снято с продажи {sold}, ошибок API {fail}, исключений {err}",
                        i, len(ids), **cnt)
        time.sleep(PAUSE)
    logger.info("{} завершена: ok {ok}, снято с продажи {sold}, ошибок API {fail}, исключений {err}",
                title, **cnt)
    return cnt


def enrich_pending(limit=None) -> dict:
    return process(cars_to_enrich(limit), "Догрузка подробностей")


def recheck_active(hours: int = RECHECK_HOURS, limit=None) -> dict:
    sql = ("SELECT listing_id FROM cars WHERE is_active = 1 AND enriched_at IS NOT NULL "
           "AND updated_at < datetime('now', ?) ORDER BY updated_at")
    params = [f"-{hours} hours"]
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    with get_conn() as conn:
        ids = [r[0] for r in conn.execute(sql, params)]
    return process(ids, "Перепроверка продающихся машин", recheck_from)


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | {level} | {message}")
    logger.add("data/enrich.log", rotation="10 MB", retention="7 days")
    init_db()
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    if "--recheck" in sys.argv:
        recheck_active(limit=limit)      # цвет и параметры новых машин теперь догружает details.py
    else:
        enrich_pending(limit)
