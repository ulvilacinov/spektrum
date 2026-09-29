#!/usr/bin/env bash
# Nightly: database dump and uploaded PDFs to S3. The EC2 instance role grants the access;
# the bucket's lifecycle rule deletes old copies.
set -euo pipefail
cd /opt/spektrum
set -a; source .env; set +a
: "${BACKUP_BUCKET:?BACKUP_BUCKET is not set}"
stamp=$(date -u +%Y-%m-%dT%H%M%SZ)

docker compose exec -T postgres pg_dump -U vocab -Fc vocab \
  | aws s3 cp - "s3://${BACKUP_BUCKET}/db/vocab-${stamp}.dump"
docker compose exec -T app tar -C /data -cz uploads \
  | aws s3 cp - "s3://${BACKUP_BUCKET}/uploads/uploads-${stamp}.tar.gz"
echo "$(date -u) backup ${stamp} done"
