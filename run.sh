#!/usr/bin/env bash
set -euo pipefail
source "/Users/michaelkatschko/mail-ai-sorter/secrets.env"
exec "/opt/homebrew/bin/python3" "/Users/michaelkatschko/mail-ai-sorter/sorter.py" --config "/Users/michaelkatschko/mail-ai-sorter/config.json" --max-per-account 50 "$@"
