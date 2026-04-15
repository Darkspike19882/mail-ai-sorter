#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/mail-ai-sorter"
PLIST_PATH="$HOME/Library/LaunchAgents/com.michael.mail-ai-sorter.plist"
WRAPPER="$BASE_DIR/run.sh"
PYTHON_BIN="$(command -v python3)"
SECRETS="$BASE_DIR/secrets.env"

if [[ ! -f "$BASE_DIR/config.json" ]]; then
  echo "Fehlt: $BASE_DIR/config.json (kopiere config.example.json)" >&2
  exit 1
fi

if [[ ! -f "$SECRETS" ]]; then
  echo "Fehlt: $SECRETS — erstelle die Datei mit deinen Passwörtern:" >&2
  echo ""
  echo "  cat > $SECRETS << 'EOF'"
  echo "  export MAIL_IMPEDIRE_GOOGLEMAIL_COM_PASS='dein-app-passwort'"
  echo "  export MAIL_TREIBSAND1988_GMX_DE_PASS='dein-app-passwort'"
  echo "  export MAIL_MICHAEL_KATSCHKO_ICLOUD_COM_PASS='dein-app-passwort'"
  echo "  export MAIL_MICHAEL_KATSCHKO_DE_PASS='dein-app-passwort'"
  echo "  EOF"
  echo "  chmod 600 $SECRETS"
  exit 1
fi

# Sicherheit: secrets.env darf nur für den Owner lesbar sein
chmod 600 "$SECRETS"

# Wrapper-Script erstellen, das die Passwörter lädt und den Sorter aufruft
cat > "$WRAPPER" <<WRAPPER
#!/usr/bin/env bash
set -euo pipefail
source "$SECRETS"
exec "$PYTHON_BIN" "$BASE_DIR/sorter.py" --config "$BASE_DIR/config.json" --max-per-account 50 "\$@"
WRAPPER
chmod 700 "$WRAPPER"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.michael.mail-ai-sorter</string>

  <key>ProgramArguments</key>
  <array>
    <string>${WRAPPER}</string>
  </array>

  <key>StartInterval</key>
  <integer>300</integer>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${HOME}/Library/Logs/mail-ai-sorter.log</string>

  <key>StandardErrorPath</key>
  <string>${HOME}/Library/Logs/mail-ai-sorter.err.log</string>
</dict>
</plist>
PLIST

# Ggf. alten Agent entladen
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Agent laden und starten
launchctl load "$PLIST_PATH"

echo ""
echo "✓ LaunchAgent installiert und gestartet: $PLIST_PATH"
echo "✓ Wrapper: $WRAPPER"
echo ""
echo "Logs:"
echo "  tail -f $HOME/Library/Logs/mail-ai-sorter.log"
echo "  tail -f $HOME/Library/Logs/mail-ai-sorter.err.log"
echo ""
echo "Stoppen:    launchctl unload $PLIST_PATH"
echo "Neu laden:  launchctl load $PLIST_PATH"
echo "Manuell:    $WRAPPER --dry-run"
