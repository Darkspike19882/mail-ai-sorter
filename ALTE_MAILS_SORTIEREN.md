#!/bin/bash
# Alte Mails Sortieren Script - für 984 unsortierte Emails

echo "📧 Alte Mails Sortieren - 984 unsortierte Emails"
echo "================================================================"
echo ""

# Optionen für alte Mails
echo "Optionen für alte Mails:"
echo "1. Alle Mails sortieren (empfohlen)"
echo "2. Nur INBOX sortieren"
echo "3. Bestimmten Zeitraum sortieren"
echo ""
read -p "Welche Option? (1-3): " option

case $option in
  1)
    echo "Sortiere ALLE Mails..."
    ./run.sh --all --max-per-account 250 --no-delay --parallel
    ;;
  2)
    echo "Sortiere nur INBOX..."
    ./run.sh --days-back 365 --max-per-account 200 --no-delay
    ;;
  3)
    read -p "Wie viele Tage zurück? (z.B. 30): " days
    echo "Sortiere Mails der letzten $days Tage..."
    ./run.sh --days-back $days --max-per-account 150 --no-delay
    ;;
  *)
    echo "Ungültige Option"
    exit 1
    ;;
esac

echo ""
echo "✅ Sortierung abgeschlossen!"
echo "Ergebnisse:"
echo "• Sortierte Mails siehe oben im Log"
echo "• Sender-Cache automatisch erweitert"
echo "• Mail-Index automatisch aktualisiert"
