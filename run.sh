#!/usr/bin/env bash
set -euo pipefail

# Mail AI Sorter - Run Script
# Dieses Script startet die Email-Sortierung

# Pfad zum Script-Verzeichnis
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Secrets laden (optional - wenn secrets.env existiert)
if [ -f "$SCRIPT_DIR/secrets.env" ]; then
    source "$SCRIPT_DIR/secrets.env"
fi

# Python Script starten
exec python3 "$SCRIPT_DIR/sorter.py" --config "$SCRIPT_DIR/config.json" "$@"
