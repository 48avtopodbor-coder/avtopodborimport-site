#!/bin/bash
set -Eeuo pipefail
cd /opt/avtopodborimport
exec 9>/run/lock/avtopodbor-release.lock
flock -n 9 || exit 0
export DOCKER_CONFIG=/etc/avtopodbor-registry
image=ghcr.io/48avtopodbor-coder/avtopodborimport-site:latest
old=$(docker inspect --format '{{.Image}}' avtopodbor-web)
timeout 180 docker pull "$image"
new=$(docker image inspect --format '{{.Id}}' "$image")
[ "$new" != "$old" ] || exit 0
# A failed candidate requires manual investigation, not repeated outages.
if [ -f /var/lib/avtopodbor-release/rejected ] && [ "$(cat /var/lib/avtopodbor-release/rejected)" = "$new" ]; then
  echo 'Candidate previously failed; retaining running version'
  exit 1
fi
mkdir -p /var/lib/avtopodbor-release
docker tag "$old" avtopodborimport-site:rollback
compose=$(mktemp /opt/avtopodborimport/.release-XXXXXX.yml)
trap 'rm -f "$compose"' EXIT
write_override() { printf 'services:\n  web:\n    image: %s\n' "$1" > "$compose"; }
healthy() {
  for attempt in {1..20}; do
    if curl -fsS --max-time 5 http://127.0.0.1:3000/api/health > /dev/null &&
       curl -fsS --max-time 10 http://127.0.0.1:3000/catalog/used > /dev/null; then
      return 0
    fi
    sleep 3
  done
  return 1
}
write_override "$new"
if timeout 90 docker compose -f docker-compose.yml -f "$compose" up -d --no-build --pull never web && healthy; then
  printf '%s\n' "$new" > /var/lib/avtopodbor-release/current
  echo "Release healthy: $new"
else
  printf '%s\n' "$new" > /var/lib/avtopodbor-release/rejected
  write_override "$old"
  timeout 90 docker compose -f docker-compose.yml -f "$compose" up -d --no-build --pull never web
  healthy || { echo 'CRITICAL: rollback health check failed'; exit 2; }
  echo 'Candidate failed; previous image restored'
  exit 1
fi
