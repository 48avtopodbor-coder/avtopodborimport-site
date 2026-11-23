#!/bin/sh
# The site server starts the collector directly over its existing SSH alias.
set -eu
collector_dir=/home/c/cc14862/che168
remote() { ssh -o BatchMode=yes -o ConnectTimeout=20 hosting "$@"; }
before=$(remote "stat -c %s $collector_dir/data/cron.log")
remote "cd $collector_dir || exit 1; : > data/empty; setsid nohup sh run_hourly.sh > data/start.log 2>&1 < data/empty &"
sleep 20
after=$(remote "stat -c %s $collector_dir/data/cron.log")
if [ "$after" = "$before" ]; then
    echo "$(date '+%Y-%m-%d %H:%M') сборщик не начал работу"
    remote "cat $collector_dir/data/start.log"
    exit 1
fi
echo "$(date '+%Y-%m-%d %H:%M') прямой запуск сборщика подтверждён"
