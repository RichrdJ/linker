#!/bin/sh
set -ef   # -f: geen bestandsnaam-uitbreiding van * in de opdracht

mkdir -p "$DATA_DIR"
CMD="uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5656} --proxy-headers --forwarded-allow-ips=*"

if [ -n "$PUID" ] && [ -n "$PGID" ]; then
  chown -R "$PUID:$PGID" "$DATA_DIR"
  exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups env HOME="$DATA_DIR" $CMD
fi

exec $CMD
