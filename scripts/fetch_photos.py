#!/usr/bin/env python3
"""Локальные первые два фото машин в продаже.

Новый сервер не может подключиться к серверам фото в Китае, а старый хостинг
может. Поэтому хостинг последовательно получает изображения и передаёт их
обратно по SSH одним потоком tar. На хостинге ничего не сохраняется.

Запросы идут по одному, с паузой. После нескольких подряд отказов Che168 запуск
останавливается, и следующие два часа фото не запрашиваются.

Первое фото сохраняется как <номер объявления>.<расширение>, следующие — как
<номер объявления>_2, <номер объявления>_3 и <номер объявления>_4. Nginx отдаёт их из /photos/;
PostgreSQL хранит пути в local_photo, local_photo_2, local_photo_3 и local_photo_4.
Размер файла не ограничен: полученные изображения сохраняются без сжатия
и изменения разрешения в том качестве, которое отдаёт URL источника.

Запуск на сервере Timeweb Cloud от root:
    python3 /opt/avtopodborimport/fetch_photos.py             # до 2000 фото, до 40 минут
    python3 /opt/avtopodborimport/fetch_photos.py --limit 30  # пробный запуск
    python3 /opt/avtopodborimport/fetch_photos.py --dry-run   # только посчитать
"""
import argparse
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from datetime import datetime

PHOTOS_DIR = os.environ.get("PHOTOS_DIR", "/opt/avtopodborimport/photos")
DB_NAME = os.environ.get("PHOTOS_DB", "avtopodborimport")
LOCK_PATH = os.environ.get("PHOTOS_LOCK", "/tmp/fetch_photos.lock")
COOLDOWN_PATH = os.environ.get("PHOTOS_COOLDOWN", "/srv/che168/photos_cooldown")
COOLDOWN_HOURS = 2
FAILED_PATH = os.environ.get("PHOTOS_FAILED", "/srv/che168/photos_failed.json")
FAILED_HOURS = 24

# Скрипт на хостинге работает только со стандартной библиотекой.
REMOTE_SHELL = 'exec "$(command -v python3 || echo "$HOME/che168/.venv/bin/python")" -u -'
SSH_CMD = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
           "-o", "ServerAliveInterval=30", "hosting", REMOTE_SHELL]
FETCH_CMD = shlex.split(os.environ["PHOTOS_FETCH_CMD"]) if os.environ.get("PHOTOS_FETCH_CMD") else SSH_CMD

MAX_REFUSED = 3
SAVE_EVERY = 200

ID_RE = re.compile(r"^[0-9A-Za-z_-]{1,40}$")
URL_RE = re.compile(r"^https://[0-9a-z.-]+\.autoimg\.cn/[^\s\"'\\]+$")

# На каждую машину берём максимум четыре исходных URL.
PHOTO_SOURCES_SQL = """
WITH source AS (
  SELECT listing_id::text AS listing_id, scraped_at, local_photo, local_photo_2, local_photo_3, local_photo_4,
         COALESCE(CASE WHEN pg_input_is_valid(photos, 'json') THEN photos::json->>0 END,
                  CASE WHEN pg_input_is_valid(images, 'json') THEN images::json->>0 END) AS first_url,
         COALESCE(CASE WHEN pg_input_is_valid(photos, 'json') THEN photos::json->>1 END,
                  CASE WHEN pg_input_is_valid(images, 'json') THEN images::json->>1 END) AS second_url,
         COALESCE(CASE WHEN pg_input_is_valid(photos, 'json') THEN photos::json->>2 END,
                  CASE WHEN pg_input_is_valid(images, 'json') THEN images::json->>2 END) AS third_url,
         COALESCE(CASE WHEN pg_input_is_valid(photos, 'json') THEN photos::json->>3 END,
                  CASE WHEN pg_input_is_valid(images, 'json') THEN images::json->>3 END) AS fourth_url
  FROM cars
  WHERE is_active = 1 AND price_cny > 0
)
"""
COUNT_SQL = PHOTO_SOURCES_SQL + """
SELECT count(*)
FROM source
CROSS JOIN LATERAL (VALUES (1, first_url, local_photo), (2, second_url, local_photo_2),
                           (3, third_url, local_photo_3), (4, fourth_url, local_photo_4))
  AS photo(photo_index, url, local_path)
WHERE url IS NOT NULL AND local_path IS NULL;
"""
CANDIDATES_SQL = PHOTO_SOURCES_SQL + """
SELECT listing_id, photo_index, url
FROM source
CROSS JOIN LATERAL (VALUES (1, first_url, local_photo), (2, second_url, local_photo_2),
                           (3, third_url, local_photo_3), (4, fourth_url, local_photo_4))
  AS photo(photo_index, url, local_path)
WHERE url IS NOT NULL AND local_path IS NULL
ORDER BY photo_index ASC, scraped_at DESC
LIMIT %d;
"""
ON_SALE_SQL = """
SELECT count(*) FILTER (WHERE local_photo IS NOT NULL) || '|' ||
       count(*) FILTER (WHERE local_photo_2 IS NOT NULL) || '|' ||
       count(*) FILTER (WHERE local_photo_3 IS NOT NULL) || '|' ||
       count(*) FILTER (WHERE local_photo_4 IS NOT NULL) || '|' || count(*)
FROM cars WHERE is_active = 1 AND price_cny > 0;
"""

STOP_TEXT = {
    "done": "список закончился",
    "timeout": "вышло время",
    "refused": "Che168 отказывает",
    "no-connection": "нет связи с сервером фото",
}

# Этот код исполняется на старом хостинге; используем только стандартную библиотеку.
REMOTE_CODE = r'''
import http.client, io, json, sys, tarfile, time
from urllib.parse import urlsplit

UA = "Python-urllib/%d.%d" % sys.version_info[:2]
REFUSED = (403, 429, 514)


def fetch(conns, host, path):
    for attempt in (1, 2):
        conn = conns.get(host)
        if conn is None:
            conn = http.client.HTTPSConnection(host, timeout=20)
            conns[host] = conn
        try:
            conn.request("GET", path, headers={"User-Agent": UA, "Accept": "image/webp,image/*;q=0.8"})
            resp = conn.getresponse()
            body = resp.read()
            if resp.will_close:
                conn.close()
                conns.pop(host, None)
            return resp.status, body, (resp.getheader("Content-Type") or "").lower()
        except (OSError, http.client.HTTPException):
            conn.close()
            conns.pop(host, None)
    return None, None, ""


def main(params):
    p = json.loads(params)
    deadline = time.time() + p["minutes"] * 60
    out = tarfile.open(fileobj=sys.stdout.buffer, mode="w|")
    start = tarfile.TarInfo(".start")
    out.addfile(start, io.BytesIO(b""))
    conns = {}
    stats = {"ok": 0, "errors": 0, "refused": 0, "stop": "done", "examples": [], "failed": []}
    refused_row = errors_row = 0
    for listing_id, photo_index, url in p["items"]:
        label = "%s:%s" % (listing_id, photo_index)
        if time.time() > deadline:
            stats["stop"] = "timeout"
            break
        u = urlsplit(url)
        host = u.hostname or ""
        if u.scheme != "https" or not host.endswith(".autoimg.cn"):
            stats["errors"] += 1
            stats["failed"].append(label)
            continue
        path = u.path + ("?" + u.query if u.query else "")
        status, body, ctype = fetch(conns, host, path)
        if status == 200 and body and ctype.startswith("image/"):
            info = tarfile.TarInfo("%s__p%s" % (listing_id, photo_index))
            info.size = len(body)
            info.mtime = int(time.time())
            out.addfile(info, io.BytesIO(body))
            stats["ok"] += 1
            refused_row = errors_row = 0
        elif status in REFUSED:
            stats["refused"] += 1
            refused_row += 1
            if refused_row >= p["max_refused"]:
                stats["stop"] = "refused"
                stats["examples"].append("%s: %s" % (label, status))
                break
        else:
            stats["errors"] += 1
            if len(stats["examples"]) < 3:
                stats["examples"].append("%s: %s %s" % (label, status, ctype))
            if status is None:
                errors_row += 1
                if errors_row >= 20:
                    stats["stop"] = "no-connection"
                    break
            else:
                stats["failed"].append(label)
                errors_row = 0
        time.sleep(p["pause"])
    out.close()
    sys.stdout.buffer.flush()
    sys.stderr.write("RESULT " + json.dumps(stats) + "\n")
'''


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def psql(sql):
    """Запрос к базе сайта от имени postgres; возвращает строки ответа."""
    r = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", DB_NAME, "-AtqX", "-v", "ON_ERROR_STOP=1", "-f", "-"],
        input=sql, capture_output=True, text=True, timeout=300, cwd="/",
    )
    if r.returncode != 0:
        sys.exit(f"{now()} ошибка базы: {r.stderr.strip()}")
    return r.stdout


def save(rows):
    """Записывает готовые пути в соответствующее поле PostgreSQL."""
    if not rows:
        return
    values = ",".join(f"('{lid}',{photo_index},'{path}')" for lid, photo_index, path in rows)
    psql(
        "WITH v(id, photo_index, p) AS (VALUES " + values + "), "
        "photos AS (SELECT id, "
        "max(p) FILTER (WHERE photo_index = 1) AS first_path, "
        "max(p) FILTER (WHERE photo_index = 2) AS second_path, "
        "max(p) FILTER (WHERE photo_index = 3) AS third_path, "
        "max(p) FILTER (WHERE photo_index = 4) AS fourth_path "
        "FROM v GROUP BY id) "
        "UPDATE cars SET "
        "local_photo = COALESCE(cars.local_photo, photos.first_path), "
        "local_photo_2 = COALESCE(cars.local_photo_2, photos.second_path), "
        "local_photo_3 = COALESCE(cars.local_photo_3, photos.third_path), "
        "local_photo_4 = COALESCE(cars.local_photo_4, photos.fourth_path) "
        "FROM photos WHERE cars.listing_id::text = photos.id "
        "AND (cars.local_photo IS NULL OR cars.local_photo_2 IS NULL OR cars.local_photo_3 IS NULL OR cars.local_photo_4 IS NULL);"
    )


def photo_suffix(photo_index):
    return "" if photo_index == 1 else f"_{photo_index}"


def existing(listing_id, photo_index):
    """Путь, если файл уже скачан, например при прерванном запуске."""
    stem = listing_id + photo_suffix(photo_index)
    for ext in (".webp", ".jpg", ".png"):
        path = os.path.join(PHOTOS_DIR, stem + ext)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return "/photos/" + stem + ext
    return None


def image_ext(data):
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    return None


def write_photo(listing_id, photo_index, ext, data):
    stem = listing_id + photo_suffix(photo_index)
    final = os.path.join(PHOTOS_DIR, stem + ext)
    tmp = final + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.chmod(tmp, 0o644)
    os.replace(tmp, final)
    return "/photos/" + stem + ext


def failure_key(listing_id, photo_index):
    return f"{listing_id}:{photo_index}"


def cooldown_until():
    try:
        with open(COOLDOWN_PATH) as f:
            return float(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0.0


def load_failed():
    try:
        with open(FAILED_PATH) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    fresh = time.time() - FAILED_HOURS * 3600
    result = {k: v for k, v in data.items() if isinstance(v, (int, float)) and v > fresh}
    # Совместимость со старым кэшем, где ключом был только номер машины.
    for key, value in list(result.items()):
        if ":" not in key:
            result[f"{key}:1"] = value
            del result[key]
    return result


def save_failed(failed):
    tmp = FAILED_PATH + ".part"
    with open(tmp, "w") as f:
        json.dump(failed, f)
    os.replace(tmp, FAILED_PATH)


def main():
    ap = argparse.ArgumentParser(description="Первые два фото машин через старый хостинг")
    ap.add_argument("--limit", type=int, default=2000, help="сколько фото за запуск (2000)")
    ap.add_argument("--minutes", type=float, default=40, help="не дольше стольких минут (40)")
    ap.add_argument("--pause", type=float, default=0.3, help="пауза между фото, с (0.3)")
    ap.add_argument("--dry-run", action="store_true", help="только посчитать, ничего не скачивать")
    ap.add_argument("--photo-index", type=int, choices=(1, 2, 3, 4),
                    help="выбрать только одно фото для пробного запуска")
    args = ap.parse_args()

    if args.limit < 1 or args.minutes <= 0 or args.pause < 0:
        ap.error("limit должен быть больше 0, minutes — больше 0, pause — не меньше 0")
    if os.geteuid() != 0 and "PHOTOS_FETCH_CMD" not in os.environ:
        sys.exit("запускать от root: нужны ssh hosting и запись в папку фото")

    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        print(f"{now()} предыдущий запуск ещё идёт, пропуск")
        return

    pause_till = cooldown_until()
    if time.time() < pause_till and not args.dry_run:
        lock.close()
        till = datetime.fromtimestamp(pause_till).strftime("%H:%M")
        print(f"{now()} пауза после отказа Che168 до {till}, пропуск")
        return

    index_filter = " AND photo_index = %d" % args.photo_index if args.photo_index else " AND photo_index <= 2"
    missing = int(psql(COUNT_SQL.replace("WHERE url IS NOT NULL AND local_path IS NULL;",
                                         "WHERE url IS NOT NULL AND local_path IS NULL" + index_filter + ";")).strip() or 0)
    failed = load_failed()
    have, todo, skipped = [], [], 0
    candidates_sql = CANDIDATES_SQL.replace("WHERE url IS NOT NULL AND local_path IS NULL",
                                             "WHERE url IS NOT NULL AND local_path IS NULL" + index_filter)
    for line in psql(candidates_sql % (args.limit + len(failed))).splitlines():
        listing_id, photo_index, url = line.split("|", 2)
        photo_index = int(photo_index)
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("http://"):
            url = "https://" + url[7:]
        if not ID_RE.match(listing_id) or photo_index not in (1, 2, 3, 4) or not URL_RE.match(url):
            continue
        key = failure_key(listing_id, photo_index)
        if key in failed:
            skipped += 1
            continue
        if len(have) + len(todo) >= args.limit:
            break
        path = existing(listing_id, photo_index)
        if path:
            have.append((listing_id, photo_index, path))
        else:
            todo.append((listing_id, photo_index, url))
    selection = f"фото №{args.photo_index}" if args.photo_index else "первые два фото"
    print(f"{now()} {selection}: без локального файла {missing}, "
          f"в очереди {len(have) + len(todo)}, файл уже есть у {len(have)}, скачать {len(todo)}"
          + (f", отложено после неудачи {skipped}" if skipped else ""), flush=True)

    if args.dry_run:
        lock.close()
        if todo:
            print(f"первое в очереди: {todo[0][0]} фото {todo[0][1]} {todo[0][2]}")
        if time.time() < pause_till:
            print(f"сейчас пауза после отказа Che168 до {datetime.fromtimestamp(pause_till):%H:%M}")
        print("проверка: ok, ничего не скачано и не записано")
        return

    save(have)
    if not todo:
        lock.close()
        print(f"{now()} скачивать нечего")
        return

    started = time.time()
    program = REMOTE_CODE + "\nmain(%r)\n" % json.dumps({
        "items": todo, "minutes": args.minutes, "pause": args.pause,
        "max_refused": MAX_REFUSED,
    })
    errlog = tempfile.TemporaryFile()
    proc = subprocess.Popen(FETCH_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errlog)
    watchdog = threading.Timer(args.minutes * 60 + 180, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    try:
        proc.stdin.write(program.encode())
        proc.stdin.close()
    except BrokenPipeError:
        pass

    wanted = {f"{listing_id}__p{photo_index}": (listing_id, photo_index)
              for listing_id, photo_index, _ in todo}
    done, pending, rejected, stream_error = [], [], [], None
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tf:
            for member in tf:
                if member.name == ".start":
                    continue
                target = wanted.get(member.name)
                if target is None or not member.isfile():
                    continue
                data = tf.extractfile(member).read()
                ext = image_ext(data)
                if not ext:
                    rejected.append(failure_key(*target))
                    continue
                listing_id, photo_index = target
                pending.append((listing_id, photo_index,
                                write_photo(listing_id, photo_index, ext, data)))
                done.append(target)
                if len(pending) >= SAVE_EVERY:
                    save(pending)
                    pending = []
                    print(f"… {len(done)} фото", flush=True)
    except (tarfile.TarError, OSError) as e:
        stream_error = str(e)
    finally:
        save(pending)
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
        watchdog.cancel()
        proc.stdout.close()

    errlog.seek(0)
    err_lines = errlog.read().decode("utf-8", "replace").splitlines()
    errlog.close()
    stats = None
    for line in err_lines:
        if line.startswith("RESULT "):
            stats = json.loads(line[7:])
    if stats is None:
        tail = " | ".join(err_lines[-3:]) or stream_error or "нет ответа"
        print(f"{now()} хостинг не прислал итог: {tail}")
    else:
        print(f"на хостинге: скачано {stats['ok']}, ошибок {stats['errors']}, отказов Che168 {stats['refused']}; "
              f"остановка — {STOP_TEXT.get(stats['stop'], stats['stop'])}")
        if stats["examples"]:
            print("примеры: " + "; ".join(stats["examples"]))
        if stats["stop"] == "refused":
            with open(COOLDOWN_PATH, "w") as f:
                f.write(str(time.time() + COOLDOWN_HOURS * 3600))
            print(f"следующие {COOLDOWN_HOURS} ч фото не скачиваем")
    candidate_keys = {failure_key(listing_id, photo_index)
                      for listing_id, photo_index, _ in todo}
    bad = [key for key in (stats or {}).get("failed", []) + rejected if key in candidate_keys]
    if bad:
        failed.update({key: time.time() for key in bad})
        save_failed(failed)
    if stream_error and stats is not None:
        print(f"поток прервался: {stream_error}")
    on_sale = psql(ON_SALE_SQL).strip().split("|")
    if len(on_sale) == 5:
        print(f"{now()} готово за {time.time() - started:.0f} с: сохранено {len(done)} фото; "
              f"в продаже локально: главных {on_sale[0]}, вторых {on_sale[1]}, "
              f"третьих {on_sale[2]}, четвёртых {on_sale[3]} из {on_sale[4]}")
    else:
        print(f"{now()} готово за {time.time() - started:.0f} с: сохранено {len(done)} фото")
    if bad:
        print(f"не удалось получить {len(bad)} фото; повтор через {FAILED_HOURS} ч")
    lock.close()


if __name__ == "__main__":
    main()
