#!/bin/sh
# Hosting volumes (Fly.io) are mounted owned by root: hand the uploads folder to the app user,
# then run the command without root rights.
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p "${UPLOAD_DIR:-/data/uploads}"
  chown -R app:app "${UPLOAD_DIR:-/data/uploads}"
  # root's HOME stays set otherwise, and libpq fails on the unreadable /root/.postgresql
  # when it looks for SSL client certificates (e.g. connecting to Neon).
  export HOME=/tmp
  exec setpriv --reuid=app --regid=app --init-groups "$@"
fi
exec "$@"
