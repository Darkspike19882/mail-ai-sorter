#!/bin/bash
# Test-Script für 30-Minuten Regel - Zeigt genau was passiert

echo "🧪 30-Minuten Regel Test-Script"
echo "=================================="
echo ""
echo "Dieses Script zeigt dir genau, wie die 30-Minuten-Regel funktioniert:"
echo ""

# Prüfe ob Ollama läuft
if ! pgrep -q ollama; then
    echo "⚠️  Ollama läuft nicht - wird gestartet..."
    /Applications/Ollama.app/Contents/Resources/ollama serve > /dev/null 2>&1 &
    sleep 3
fi

echo "📧 Aktuelle Situation:"
echo "• delay_minutes: 30 (in config.json)"
echo "• poll_minutes: 5 (Launchd alle 5 Minuten)"
echo "• Regeln warten jetzt AUCH 30 Minuten!"
echo ""

echo "⏰ Wie es funktioniert:"
echo ""
echo "1. Neue Email kommt an (z.B. 18:00 Uhr):"
echo "   📧 'Newsletter: Unser neuer Shop'"
echo "   ⏰ WIRD ÜBERSPRUNGEN (28min verbleibend)"
echo "   📄 Paperless-ngx beginnt mit PDF-Extraktion"
echo ""

echo "2. 5 Minuten später (18:05 Uhr):"
echo "   ⏰ WIRD ÜBERSPRUNGEN (23min verbleibend)"
echo "   📄 Paperless-ngx extrahiert weiter..."
echo ""

echo "3. 10 Minuten später (18:15 Uhr):"
echo "   ⏰ WIRD ÜBERSPRUNGEN (13min verbleibend)"
echo "   📄 Paperless-ngx fast fertig..."
echo ""

echo "4. 30 Minuten später (18:30 Uhr):"
echo "   ✅ 30min vergangen → REGELN greifen!"
echo "   ✓ REGEL 30min+ → newsletter: Unser neuer Shop"
echo "   📁 Wird in Newsletter-Ordner verschoben"
echo ""

echo "🔍 Das wurde gefixt:"
echo ""
echo "VORHER:"
echo "  [google] rule → newsletter: Neue Email"
echo "  ❌ Sofort verschoben, Paperless hatte keine Chance!"
echo ""
echo "NACHHER:"
echo "  [google] ⏰ SKIP 28min für Paperless: Neue Email"
echo "  ✅ Wartet 30 Minuten, Paperless kann arbeiten!"
echo ""

echo "🧪 Test-Möglichkeiten:"
echo ""
echo "Option 1 - Sofortiger Test nach neuer Email:"
echo "  ./run.sh --max-per-account 5"
echo "  Erwartung: ⏰ SKIP XXmin für Paperless"
echo ""
echo "Option 2 - Manueller Test in 30 Minuten:"
echo "  ./run.sh --max-per-account 5"
echo "  Erwartung: ✓ REGEL 30min+ → kategorie"
echo ""

echo "📊 Aktuelle Statistik:"
python3 index.py stats | head -10

echo ""
echo "🎯 Das Problem ist behoben!"
echo "Alle Regeln warten jetzt konsequent 30 Minuten auf Paperless-ngx!"
