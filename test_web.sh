#!/bin/bash
# Test-Script für Web UI

echo "🧪 Web UI Test-Script"
echo "===================="
echo ""

# Prüfe ob venv existiert
if [ ! -d "venv" ]; then
    echo "❌ venv nicht gefunden!"
    echo "Erstelle venv..."
    python3 -m venv venv
    source venv/bin/activate
    pip install flask
fi

echo "✅ Flask installiert"
echo ""

# Prüfe ob Flask importiert werden kann
source venv/bin/activate
python3 -c "from flask import Flask; print('✅ Flask import erfolgreich')"

echo ""
echo "🚀 Web UI starten..."
echo "Öffne http://localhost:5000 im Browser"
echo "Drücke STRG+C zum Beenden"
echo ""

python3 web_ui.py
