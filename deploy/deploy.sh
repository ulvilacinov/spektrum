#!/usr/bin/env bash
# Runs on the server after GitHub Actions copied this folder and .env to /opt/spektrum
# and logged Docker in to GHCR.
set -euo pipefail
cd /opt/spektrum

docker compose pull app
docker compose up -d --remove-orphans
docker logout ghcr.io >/dev/null 2>&1 || true
docker image prune -f >/dev/null

# Nightly backup to S3 (see backup.sh) when a bucket is configured.
if grep -q '^BACKUP_BUCKET=.\+' .env; then
  echo "0 3 * * * ubuntu /opt/spektrum/backup.sh >> /var/log/spektrum-backup.log 2>&1" \
    | sudo tee /etc/cron.d/spektrum-backup >/dev/null
  sudo touch /var/log/spektrum-backup.log && sudo chown ubuntu /var/log/spektrum-backup.log
fi

echo "Waiting for the app to become healthy..."
for _ in $(seq 1 60); do
  status=$(docker inspect --format '{{.State.Health.Status}}' "$(docker compose ps -q app)")
  if [ "$status" = "healthy" ]; then
    echo "Deployed: $(grep '^APP_IMAGE=' .env | cut -d= -f2)"
    exit 0
  fi
  sleep 3
done
echo "The app did not become healthy:" >&2
docker compose logs --tail 80 app >&2
exit 1
