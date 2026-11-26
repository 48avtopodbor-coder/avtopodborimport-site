#!/usr/bin/env python3
import sqlite3, requests, os, json, time
DB = os.path.expanduser("~/che168/data/cars.db")
PHOTOS_DIR = os.path.expanduser("~/che168/photos")
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM cars WHERE (photos IS NOT NULL AND photos != '[]' OR images IS NOT NULL AND images != '[]')")
total = cur.fetchone()[0]
print(f"Total: {total}", flush=True)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://www.che168.com/"})
ok = fail = offset = 0
while True:
    cur.execute("SELECT listing_id,photos,images FROM cars WHERE (photos IS NOT NULL AND photos != '[]' OR images IS NOT NULL AND images != '[]') ORDER BY listing_id LIMIT 100 OFFSET ?", (offset,))
    rows = cur.fetchall()
    if not rows:
        break
    for lid, pj, ij in rows:
        url = None
        for fld in [pj, ij]:
            if not fld:
                continue
            try:
                arr = json.loads(fld)
                if isinstance(arr, list) and arr:
                    url = arr[0]
                    break
            except:
                pass
        if not url:
            fail += 1
            continue
        ext = ".webp" if ".webp" in url else ".png" if ".png" in url else ".jpg"
        lp = f"{PHOTOS_DIR}/{lid}{ext}"
        if os.path.exists(lp) and os.path.getsize(lp) > 1000:
            ok += 1
            continue
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 1000:
                open(lp, "wb").write(r.content)
                ok += 1
            else:
                fail += 1
        except:
            fail += 1
        time.sleep(0.3)
    offset += 100
    print(f"  {offset}/{total} ok:{ok} err:{fail}", flush=True)
conn.close()
print(f"Done! ok:{ok} err:{fail}")
