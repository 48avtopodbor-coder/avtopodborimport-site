#!/usr/bin/env python3
"""Обложки для каталога: первое фото каждой машины в продаже.

Новый сервер не может подключиться ни к одному серверу в Китае (проверено 12.11:
ни к фото che168, ни к baidu.com), а старый хостинг может. Поэтому фото скачивает
хостинг: по ssh туда уходит небольшая программа на Python со списком ссылок,
а фото возвращаются по тому же соединению одним потоком (архив tar).
На хостинге ничего не сохраняется и не устанавливается.

Фото скачиваются по одному, с паузой, без подмены заголовков. Если che168
отказывает (403 или 429 несколько раз подряд), запуск останавливается,
и следующие два часа фото не скачиваются: ограничения не обходим.

Куда: /opt/avtopodborimport/photos/<номер объявления>.webp (nginx отдаёт их
по адресу /photos/), в базе сайта у машины заполняется local_photo.
Сначала самые свежие машины, как в каталоге.

Где работает: сервер Timeweb Cloud, файл /opt/avtopodborimport/fetch_photos.py.
Запуск от root (нужны ssh hosting и запись в папку фото):
    python3 /opt/avtopodborimport/fetch_photos.py             # до 2000 фото, не дольше 40 минут
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
# Здесь хранится время, до которого не скачиваем после отказа che168
COOLDOWN_PATH = os.environ.get("PHOTOS_COOLDOWN", "/srv/che168/photos_cooldown")
COOLDOWN_HOURS = 2
# Машины, у которых фото не скачалось (нет такого, не картинка): сутки их не трогаем,
# иначе они каждый час стояли бы первыми в очереди
FAILED_PATH = os.environ.get("PHOTOS_FAILED", "/srv/che168/photos_failed.json")
FAILED_HOURS = 24

# Программа для хостинга приходит на стандартный ввод Python.
# Если python3 нет в PATH, берём Python сборщика.
REMOTE_SHELL = 'exec "$(command -v python3 || echo "$HOME/che168/.venv/bin/python")" -u -'
SSH_CMD = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
           "-o", "ServerAliveInterval=30", "hosting", REMOTE_SHELL]
# Для проверки на другом компьютере: PHOTOS_FETCH_CMD="python3 -u -"
FETCH_CMD = shlex.split(os.environ["PHOTOS_FETCH_CMD"]) if os.environ.get("PHOTOS_FETCH_CMD") else SSH_CMD

MAX_BYTES = 3 * 1024 * 1024  # обложка обычно 20–40 КБ
MAX_REFUSED = 3  # столько отказов che168 подряд — и стоп
SAVE_EVERY = 200  # как часто записывать готовые фото в базу

ID_RE = re.compile(r"^[0-9A-Za-z_-]{1,40}$")
URL_RE = re.compile(r"^https://[0-9a-z.-]+\.autoimg\.cn/[^\s\"'\\]+$")

# Машины в продаже без обложки, первое фото из photos (или images), сначала свежие
COUNT_SQL = "SELECT count(*) FROM cars WHERE is_active = 1 AND price_cny > 0 AND local_photo IS NULL;"
CANDIDATES_SQL = """
SELECT listing_id, url FROM (
  SELECT listing_id::text AS listing_id, scraped_at,
         COALESCE(CASE WHEN pg_input_is_valid(photos, 'json') THEN photos::json->>0 END,
                  CASE WHEN pg_input_is_valid(images, 'json') THEN images::json->>0 END) AS url
  FROM cars
  WHERE is_active = 1 AND price_cny > 0 AND local_photo IS NULL
) t
WHERE url IS NOT NULL
ORDER BY scraped_at DESC
LIMIT %d;
"""
ON_SALE_SQL = """
SELECT count(*) FILTER (WHERE local_photo IS NOT NULL) || ' из ' || count(*)
FROM cars WHERE is_active = 1 AND price_cny > 0;
"""

STOP_TEXT = {
    "done": "список закончился",
    "timeout": "вышло время",
    "refused": "che168 отказывает",
    "no-connection": "нет связи с сервером фото",
}

# Эта часть выполняется на хостинге. Только стандартная библиотека,
# без f-строк: версия Python там может быть старой.
REMOTE_CODE = r'''
import http.client, io, json, sys, tarfile, time
from urllib.parse import urlsplit

UA = "Python-urllib/%d.%d" % sys.version_info[:2]
REFUSED = (403, 429, 514)


def fetch(conns, host, path, max_bytes):
    # Одно фото; соединение с сервером фото держим открытым между запросами
    for attempt in (1, 2):
        conn = conns.get(host)
        if conn is None:
            conn = http.client.HTTPSConnection(host, timeout=20)
            conns[host] = conn
        try:
            conn.request("GET", path, headers={"User-Agent": UA, "Accept": "image/webp,image/*;q=0.8"})
            resp = conn.getresponse()
            length = resp.getheader("Content-Length") or ""
            if length.isdigit() and int(length) > max_bytes:
                conn.close()
                conns.pop(host, None)
                return resp.status, None, "too-big"
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
    for listing_id, url in p["items"]:
        if time.time() > deadline:
            stats["stop"] = "timeout"
            break
        u = urlsplit(url)
        host = u.hostname or ""
        if u.scheme != "https" or not host.endswith(".autoimg.cn"):
            stats["errors"] += 1
            continue
        path = u.path + ("?" + u.query if u.query else "")
        status, body, ctype = fetch(conns, host, path, p["max_bytes"])
        if status == 200 and body and len(body) <= p["max_bytes"] and ctype.startswith("image/"):
            info = tarfile.TarInfo(listing_id)
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
                stats["examples"].append("%s: %s" % (listing_id, status))
                break
        else:
            stats["errors"] += 1
            if len(stats["examples"]) < 3:
                stats["examples"].append("%s: %s %s" % (listing_id, status, ctype))
            if status is None:
                # Нет ответа сервера фото: подряд 20 раз — значит, нет связи
                errors_row += 1
                if errors_row >= 20:
                    stats["stop"] = "no-connection"
                    break
            else:
                # Ответ есть, но фото не годится (нет такого, не картинка, слишком большое)
                stats["failed"].append(listing_id)
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
    """Записывает local_photo готовым машинам."""
    if not rows:
        return
    values = ",".join(f"('{lid}','{path}')" for lid, path in rows)
    psql(
        f"UPDATE cars SET local_photo = v.p FROM (VALUES {values}) AS v(id, p) "
        f"WHERE cars.listing_id::text = v.id AND cars.local_photo IS NULL;"
    )


def existing(listing_id):
    """Фото уже лежит в папке (например, после прерванного запуска)."""
    for ext in (".webp", ".jpg", ".png"):
        path = os.path.join(PHOTOS_DIR, listing_id + ext)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return "/photos/" + listing_id + ext
    return None


def image_ext(data):
    """Тип файла по первым байтам: в папку фото попадают только картинки."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    return None


def write_photo(listing_id, ext, data):
    final = os.path.join(PHOTOS_DIR, listing_id + ext)
    tmp = final + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.chmod(tmp, 0o644)
    os.replace(tmp, final)
    return "/photos/" + listing_id + ext


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
    return {k: v for k, v in data.items() if isinstance(v, (int, float)) and v > fresh}


def save_failed(failed):
    tmp = FAILED_PATH + ".part"
    with open(tmp, "w") as f:
        json.dump(failed, f)
    os.replace(tmp, FAILED_PATH)


def main():
    ap = argparse.ArgumentParser(description="Обложки машин через старый хостинг")
    ap.add_argument("--limit", type=int, default=2000, help="сколько машин за запуск (2000)")
    ap.add_argument("--minutes", type=float, default=40, help="не дольше стольких минут (40)")
    ap.add_argument("--pause", type=float, default=0.3, help="пауза между фото, с (0.3)")
    ap.add_argument("--dry-run", action="store_true", help="только посчитать, ничего не скачивать")
    args = ap.parse_args()

    if os.geteuid() != 0 and "PHOTOS_FETCH_CMD" not in os.environ:
        sys.exit("запускать от root: нужны ssh hosting и запись в папку фото")

    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"{now()} предыдущий запуск ещё идёт, пропуск")
        return

    pause_till = cooldown_until()
    if time.time() < pause_till and not args.dry_run:
        till = datetime.fromtimestamp(pause_till).strftime("%H:%M")
        print(f"{now()} пауза после отказа che168 до {till}, пропуск")
        return

    missing = int(psql(COUNT_SQL).strip() or 0)
    failed = load_failed()
    have, todo, skipped = [], [], 0
    for line in psql(CANDIDATES_SQL % (args.limit + len(failed))).splitlines():
        listing_id, _, url = line.partition("|")
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("http://"):
            url = "https://" + url[7:]
        if not ID_RE.match(listing_id) or not URL_RE.match(url):
            continue
        if listing_id in failed:
            skipped += 1
            continue
        if len(have) + len(todo) >= args.limit:
            break
        path = existing(listing_id)
        if path:
            have.append((listing_id, path))
        else:
            todo.append((listing_id, url))
    print(f"{now()} обложки: без фото {missing}, в этом запуске {len(have) + len(todo)}, "
          f"файл уже есть у {len(have)}, скачать {len(todo)}"
          + (f", отложено после неудачи {skipped}" if skipped else ""), flush=True)

    if args.dry_run:
        if todo:
            print(f"первое в очереди: {todo[0][0]} {todo[0][1]}")
        if time.time() < pause_till:
            print(f"сейчас пауза после отказа che168 до {datetime.fromtimestamp(pause_till):%H:%M}")
        print("проверка: ok, ничего не скачано и не записано")
        return

    save(have)
    if not todo:
        print(f"{now()} скачивать нечего")
        return

    started = time.time()
    program = REMOTE_CODE + "\nmain(%r)\n" % json.dumps({
        "items": todo, "minutes": args.minutes, "pause": args.pause,
        "max_bytes": MAX_BYTES, "max_refused": MAX_REFUSED,
    })
    errlog = tempfile.TemporaryFile()
    proc = subprocess.Popen(FETCH_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errlog)
    # Страховка от зависшего соединения
    watchdog = threading.Timer(args.minutes * 60 + 180, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    try:
        proc.stdin.write(program.encode())
        proc.stdin.close()
    except BrokenPipeError:
        pass

    wanted = dict(todo)
    done, pending, rejected, stream_error = [], [], [], None
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tf:
            for member in tf:
                if member.name == ".start":
                    continue
                listing_id = member.name
                if listing_id not in wanted or not member.isfile() or member.size > MAX_BYTES:
                    continue
                data = tf.extractfile(member).read()
                ext = image_ext(data)
                if not ext:
                    rejected.append(listing_id)
                    continue
                pending.append((listing_id, write_photo(listing_id, ext, data)))
                done.append(listing_id)
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

    errlog.seek(0)
    err_lines = errlog.read().decode("utf-8", "replace").splitlines()
    stats = None
    for line in err_lines:
        if line.startswith("RESULT "):
            stats = json.loads(line[7:])
    if stats is None:
        tail = " | ".join(err_lines[-3:]) or stream_error or "нет ответа"
        print(f"{now()} хостинг не прислал итог: {tail}")
    else:
        print(f"на хостинге: скачано {stats['ok']}, ошибок {stats['errors']}, отказов che168 {stats['refused']}; "
              f"остановка — {STOP_TEXT.get(stats['stop'], stats['stop'])}")
        if stats["examples"]:
            print("примеры: " + "; ".join(stats["examples"]))
        if stats["stop"] == "refused":
            with open(COOLDOWN_PATH, "w") as f:
                f.write(str(time.time() + COOLDOWN_HOURS * 3600))
            print(f"следующие {COOLDOWN_HOURS} ч фото не скачиваем")
    bad = [i for i in (stats or {}).get("failed", []) + rejected if i in wanted]
    if bad:
        failed.update({i: time.time() for i in bad})
        save_failed(failed)
    if stream_error and stats is not None:
        print(f"поток прервался: {stream_error}")
    on_sale = psql(ON_SALE_SQL).strip()
    print(f"{now()} готово за {time.time() - started:.0f} с: сохранено {len(done)}"
          + (f", не годится {len(bad)} (отложены на {FAILED_HOURS} ч)" if bad else "")
          + f"; в продаже с обложкой {on_sale}")


if __name__ == "__main__":
    main()
