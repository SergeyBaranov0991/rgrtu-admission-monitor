#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${DB_PATH:-/data/rgrtu.db}"
BACKUP_DIR="${BACKUP_DIR:-/data/backups}"

mkdir -p "$BACKUP_DIR"
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/rgrtu-$(date +%F).db'"

