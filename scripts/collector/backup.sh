#!/bin/sh
# backup.sh — копия базы в data/cars_backup.db (можно запускать во время сбора).
cd /home/c/cc14862/che168 || exit 1
/home/c/cc14862/che168/.venv/bin/python -c "
import sqlite3
src = sqlite3.connect('data/cars.db', timeout=120)
dst = sqlite3.connect('data/cars_backup.db.tmp')
src.backup(dst)
dst.close()
import os
os.replace('data/cars_backup.db.tmp', 'data/cars_backup.db')
print('копия базы готова')
" >> data/cron.log 2>&1
