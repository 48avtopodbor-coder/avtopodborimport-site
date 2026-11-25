"""
details.py — всё по каждой машине через API che168 (без www): цвет, фото, описание и полные характеристики.

Карточка машины (1 запрос на машину): цвет, все фото, описание продавца, число владельцев,
дата регистрации и объявления, страховка, техосмотр и другие поля.
Параметры комплектации (1 запрос на комплектацию, ~200 строк): двигатель, мощность, коробка, привод,
размеры, шины и диски, оснащение. У всех машин одной комплектации они одинаковые,
поэтому хранятся один раз в таблице specs.
Фото не скачиваются: храним ссылки на сервер фото che168 (в каталоге показываем оттуда).
Темп запросов к API карточек подбирается сам (che168_api.py). Если API попросил паузу, сборщик ждёт её
конца, пока это укладывается во время запуска (--minutes), иначе останавливается до следующего запуска.

Запуск:
    python3 details.py --limit 5        # проба на 5 машинах
    python3 details.py                  # все машины без данных, свежие первыми
    python3 details.py --minutes 50     # работать не дольше 50 минут
"""

import json
import re
import sys
import time

from loguru import logger
import che168_api as api
from database import init_db, get_conn

COLORS = [("香槟", "шампань"), ("咖啡", "коричневый"), ("黑", "чёрный"), ("白", "белый"),
          ("灰", "серый"), ("银", "серебристый"), ("蓝", "синий"), ("红", "красный"),
          ("棕", "коричневый"), ("绿", "зелёный"), ("黄", "жёлтый"), ("橙", "оранжевый"),
          ("紫", "фиолетовый"), ("金", "золотой"), ("粉", "розовый")]
SKIP_INFO = ("piclist", "remark")  # фото и описание храним в отдельных столбцах (photos, description)
MAX_TEXT = 3000                 # длинные тексты (описание продавца) обрезаем до этой длины
MAX_PHOTOS = 60
MAX_WAITS = 6                   # запуск без --minutes: столько раз ждём конца паузы API, потом стоп
SPEC_RETRY_DAYS = 7             # неполные характеристики перепроверяем без постоянных повторов


def has_core_specs(spec):
    return bool(spec.get("fuel") and spec.get("drive") and spec.get("power_hp"))


PENDING_DETAILS_WHERE = (
    "is_active = 1 AND (params_at IS NULL OR photos IS NULL OR "
    "((NULLIF(trim(fuel), '') IS NULL OR NULLIF(trim(drive), '') IS NULL "
    "OR power_hp IS NULL OR power_hp <= 0) "
    f"AND params_at < datetime('now', '-{SPEC_RETRY_DAYS} days')))"
)


def _num(x):
    m = re.search(r"\d+(?:\.\d+)?", str(x or ""))
    return float(m.group()) if m else None


def color_ru(c):
    c = str(c or "").strip()
    if not c:
        return None
    # Che168 groups some colours (e.g. 银/灰色). Keep every part in source order.
    parts = re.split(r"\s*[/／]\s*", c)
    if not all(parts):
        return c
    translated = []
    for part in parts:
        if part in ("其他", "其它", "其他颜色", "其它颜色"):
            translated.append("другой")
        else:
            translated.append(next((ru for cn, ru in COLORS if cn in part), part))
    return " / ".join(translated)


def fuel_ru(v):
    v = str(v or "")
    if not v:
        return None
    if "氢" in v:
        return "водород"
    if "增程" in v:
        return "гибрид EREV"
    if "插电" in v:
        return "гибрид PHEV"
    if "纯电" in v:
        return "электро"
    if "油电" in v or "混合动力" in v:
        return "гибрид HEV"
    mild = " (мягкий гибрид)" if "轻混" in v else ""
    if "柴油" in v:
        return "дизель" + mild
    if "汽油" in v:
        return "бензин" + mild
    if "天然气" in v or "CNG" in v.upper():
        return "газ"
    return v


def drive_ru(v):
    v = str(v or "")
    if "四驱" in v:
        return "полный"
    if "后驱" in v:
        return "задний"
    if "前驱" in v:
        return "передний"
    return v or None


def gearbox_ru(*values):
    v = " ".join(str(x) for x in values if x)
    if not v:
        return None
    return "механика" if "手动" in v else "автомат"


def power_hp(p: dict):
    ps = _num(p.get("最大马力(Ps)")) or _num(p.get("电动机(Ps)"))
    if not ps:
        kw = _num(p.get("最大功率(kW)")) or _num(p.get("电动机总功率(kW)"))
        ps = kw * 1.35962 if kw else None
    return int(round(ps)) if ps else None


def engine_ml(p: dict):
    ml = _num(p.get("排量(mL)"))
    if ml and 50 <= ml <= 20000:
        return int(round(ml))
    liters = _num(p.get("排量(L)"))
    return int(round(liters * 1000)) if liters and 0.05 <= liters <= 20 else None


def tires_text(p: dict):
    front, rear = p.get("前轮胎规格"), p.get("后轮胎规格")
    if front and rear and rear != front:
        return "{} / {}".format(front, rear)
    return front or rear


def photo_urls(piclist) -> list:
    """Ссылки на фото из ответа (элементы бывают строками или словарями)."""
    out = []
    for p in piclist or []:
        u = p if isinstance(p, str) else None
        if isinstance(p, dict):
            u = next((v for v in p.values() if isinstance(v, str) and ("autoimg" in v or v.startswith(("//", "http")))), None)
        if not u:
            continue
        u = u.strip()
        if u.startswith("//"):
            u = "https:" + u
        if u.startswith("http") and u not in out:
            out.append(u)
    return out[:MAX_PHOTOS]


def reusable_spec_cache(row, expected_model=None):
    """An EV cache must have usable range data and the same known model year."""
    if not has_core_specs(row):
        return False
    if row.get("fuel") != "электро":
        return True
    try:
        groups = json.loads(row.get("params_json") or "[]")
        entries = [(key, value) for _, items in groups for key, value in items]
    except (ValueError, TypeError):
        return False
    ranges = {}
    for key, value in entries:
        match = re.fullmatch(r"(NEDC|CLTC|WLTC|WLTP)?纯电续航里程[（(]km[）)]", str(key))
        if match and re.fullmatch(r"\d+(?:\.\d+)?", str(value)) and float(value) > 0:
            ranges.setdefault(match.group(1), set()).add(float(value))
    if not ranges or any(len(values) != 1 for values in ranges.values()):
        return False
    expected_year = re.search(r"(?:19|20)\d{2}款", expected_model or "")
    if expected_year:
        for key, value in entries:
            if key == "车型名称":
                cached_year = re.search(r"(?:19|20)\d{2}款", str(value))
                if cached_year and cached_year.group() != expected_year.group():
                    return False
    return True


def spec_info(spec_id, infoid, expected_model=None):
    """Параметры комплектации: из таблицы specs, а если их там нет — 1 запрос к API и запись в specs."""
    if spec_id:
        with get_conn() as conn:
            row = conn.execute("SELECT fuel, drive, gearbox, power_hp, engine_ml, tires, params_text, params_json "
                               "FROM specs WHERE spec_id = ? AND full = 1", (spec_id,)).fetchone()
        if row and reusable_spec_cache(dict(row), expected_model):
            return {k: v for k, v in dict(row).items() if k != "params_json"}
    groups = api.car_params(infoid)
    if groups is None:
        return None
    p = {}
    for _, items in groups:
        for name, value in items:
            p.setdefault(name, value)
    fuel_src = p.get("能源类型") or p.get("燃料形式")
    summary = [("能源类型", fuel_src), ("发动机", p.get("发动机")), ("最大马力(Ps)", p.get("最大马力(Ps)")),
               ("变速箱", p.get("变速箱")), ("驱动方式", p.get("驱动方式")), ("轮胎", tires_text(p))]
    s = {
        "fuel": fuel_ru(fuel_src),
        "drive": drive_ru(p.get("驱动方式")),
        "gearbox": gearbox_ru(p.get("变速箱类型"), p.get("变速箱")),
        "power_hp": power_hp(p),
        "engine_ml": engine_ml(p),
        "tires": tires_text(p),
        "params_text": "; ".join("{}: {}".format(k, v) for k, v in summary if v) or None,
    }
    # Регистрационные сведения не являются параметрами модели. Не отравляем
    # общий кэш комплектации ответом, в котором вообще нет технических данных.
    has_technical_data = any(s.get(k) for k in
                             ("fuel", "drive", "gearbox", "power_hp", "engine_ml", "tires"))
    if spec_id and has_technical_data:
        with get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO specs (spec_id, fuel, drive, gearbox, power_hp, engine_ml, tires, "
                         "params_text, params_json, full, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                         (spec_id, s["fuel"], s["drive"], s["gearbox"], s["power_hp"], s["engine_ml"], s["tires"],
                          s["params_text"], json.dumps(groups, ensure_ascii=False), int(has_core_specs(s))))
            conn.commit()
    return s


def save(listing_id, fields: dict, done=True):
    """done=False — характеристики не получены: машина останется в очереди на догрузку."""
    sets = "".join("{}=?, ".format(k) for k in fields)
    mark = "params_at=CURRENT_TIMESTAMP, " if done else ""
    with get_conn() as conn:
        conn.execute("UPDATE cars SET " + sets + mark +
                     "enriched_at=COALESCE(enriched_at, CURRENT_TIMESTAMP), updated_at=CURRENT_TIMESTAMP "
                     "WHERE listing_id=?", list(fields.values()) + [listing_id])
        conn.commit()


_odd = [0]


def handle(listing_id, spec_id) -> str:
    info, rc, msg = api.car_info(listing_id)
    if info is None:
        if rc is None:
            return "fail"
        if rc == 99999 or any(w in msg for w in ("下架", "不存在", "删除", "已售")):
            save(listing_id, {"is_active": 0})
            return "sold"
        _odd[0] += 1
        if _odd[0] <= 3:
            logger.warning("   {}: ответ {} {}", listing_id, rc, msg[:60])
        return "fail"

    spec_id = str(info.get("specid") or spec_id or "") or None
    got = spec_info(spec_id, listing_id, info.get("carname"))       # None — API характеристик не ответил
    s = got or {}
    photos = photo_urls(info.get("piclist"))
    # Все простые поля карточки (описание продавца, владельцы, страховка, техосмотр...)
    keep = {k: (v[:MAX_TEXT] if isinstance(v, str) else v) for k, v in info.items()
            if k not in SKIP_INFO and isinstance(v, (str, int, float, bool)) and v not in ("", None)}
    fields = {
        "model": str(info.get("carname") or "").strip() or None,
        "series_name": str(info.get("seriesname") or "").strip() or None,
        "color": color_ru(info.get("colorname")),
        "gearbox": s.get("gearbox") or gearbox_ru(info.get("gearbox")),
        "fuel": s.get("fuel"),
        "drive": s.get("drive"),
        "power_hp": s.get("power_hp"),
        "engine_ml": s.get("engine_ml"),
        "tires": s.get("tires"),
        "params_text": s.get("params_text"),
        "first_reg_date": info.get("firstregdate"),
        "publish_date": info.get("publicdate"),
        "dealer_name": info.get("dealername"),
        "spec_id": spec_id,
        "description": (str(info.get("remark") or "").strip()[:MAX_TEXT]) or None,
        "photos": json.dumps(photos, ensure_ascii=False),
        "photo_count": len(photos),
        "details_json": json.dumps(keep, ensure_ascii=False),
    }
    save(listing_id, {k: v for k, v in fields.items() if v not in (None, "")}, done=got is not None)
    if got is None:
        return "fail"           # цвет и фото записаны, характеристики догрузятся в следующий раз
    return "ok" if fields["color"] or fields["gearbox"] else "noparams"


def _hhmm(t):
    return time.strftime("%H:%M", time.localtime(t))


def fetch_details(limit=None, since=None, minutes=None) -> dict:
    """Данные для продающихся машин, у которых их ещё нет, свежие первыми.
    since — только машины, добавленные после этого момента (UTC); minutes — ограничение по времени."""
    init_db()
    sql = "SELECT listing_id, spec_id FROM cars WHERE " + PENDING_DETAILS_WHERE
    params = []
    if since:
        sql += " AND scraped_at >= ?"
        params.append(since)
    sql += " ORDER BY id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    with get_conn() as conn:
        rows = [(r[0], r[1]) for r in conn.execute(sql, params)]

    logger.info("Цвет, фото и параметры: {} машин", len(rows))
    deadline = time.time() + minutes * 60 if minutes else None
    cnt = {"ok": 0, "noparams": 0, "sold": 0, "fail": 0}
    fails_in_row = waits = 0
    for i, (listing_id, spec_id) in enumerate(rows, 1):
        if deadline and time.time() > deadline:
            logger.info("   время вышло, остальное в следующий запуск")
            break
        until = api.cooldown_until(api.DETAIL_HOST)
        if until:
            if deadline and until + 5 > deadline:
                logger.warning("   API на паузе до {} — это позже конца запуска, остальное в следующий раз",
                               _hhmm(until))
                break
            if not deadline and waits >= MAX_WAITS:
                logger.warning("   API всё время просит паузу — остальное в следующий запуск")
                break
            waits += 1
            logger.warning("   жду конца паузы API до {}", _hhmm(until))
            time.sleep(max(0, until - time.time()) + 5)
        status = handle(listing_id, spec_id)
        cnt[status] += 1
        fails_in_row = fails_in_row + 1 if status == "fail" else 0
        if fails_in_row >= 20:
            logger.error("   20 ошибок подряд — останавливаюсь")
            break
        if i % 100 == 0:
            logger.info("   {}/{}: ok {ok}, без параметров {noparams}, продано {sold}, ошибок {fail} "
                        "| запрос раз в {p:.1f} с", i, len(rows), p=api.interval(api.DETAIL_HOST), **cnt)
    logger.info("Данные готовы: ok {ok}, без параметров {noparams}, продано {sold}, ошибок {fail} "
                "| запросов к API {r}, запрос раз в {p:.1f} с", r=api.stats["requests"],
                p=api.interval(api.DETAIL_HOST), **cnt)
    return cnt


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | {level} | {message}")
    logger.add("data/details.log", rotation="10 MB", retention="7 days")
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    minutes = float(args[args.index("--minutes") + 1]) if "--minutes" in args else None
    fetch_details(limit=limit, minutes=minutes)
