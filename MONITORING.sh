#!/usr/bin/env bash
# Mail-Sorter Monitoring & Optimierung Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📧 AI Mail Sorter - Status & Optimierung"
echo "=========================================="
echo ""

# 1. Status prüfen
echo "🔍 Aktueller Status:"
python3 index.py stats | tail -15

# 2. Sender Cache Analyse
echo ""
echo "🧠 Sender-Cache Analyse:"
SENDERS=$(wc -l < learned_senders.json)
CATEGORIES=$(jq -r '.[]' learned_senders.json | sort | uniq -c | sort -rn | head -5)
echo "   ${SENDERS} gelernte Sender"
echo "   Top Kategorien:"
echo "$CATEGORIES" | head -5

# 3. Letzte Laufzeit
echo ""
echo "⏱️  Letzte Laufzeit:"
if [ -f "last_run.log" ]; then
    tail -3 last_run.log
else
    echo "   Keine Log-Datei gefunden"
fi

# 4. System-Check
echo ""
echo "💻 System-Check:"
RAM_FREE=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
RAM_FREE_GB=$((RAM_FREE * 16384 / 1024 / 1024 / 1024))
echo "   Freier RAM: ~${RAM_FREE_GB} GB"

DISK_FREE=$(df -h / | tail -1 | awk '{print $4}')
echo "   Freier Speicher: ${DISK_FREE}"

# 5. Ollama Status
echo ""
echo "🤖 Ollama Status:"
if pgrep -q ollama; then
    OLLAMA_RAM=$(ps aux | grep ollama | grep -v grep | awk '{print $6}' | head -1)
    echo "   ✓ Läuft (RAM: $((OLLAMA_RAM/1024)) MB)"
else
    echo "   ✗ Gestoppt"
fi

# 6. Launchd Job Status
echo ""
echo "🔄 Launchd Job:"
if launchctl list | grep -q mail-ai-sorter; then
    echo "   ✓ Aktiv (läuft alle 5 Minuten)"
else
    echo "   ✗ Nicht aktiv - installiere mit:"
    echo "     sudo ./install_launchd.sh"
fi

echo ""
echo "=========================================="
echo "Optimierungen:"
echo "  • Sender-Cache: ${SENDERS} Einträge (spart AI-Calls)"
echo "  • Paperless-Delay: 30min (für PDF-Extraktion)"
echo "  • IMAP-Timeout: 30s (stabilere Verbindung)"
echo "  • Ollama Context: 8192 tokens (bessere Klassifizierung)"
echo ""
echo "Manueller Testlauf:"
echo "  ./run.sh --dry-run --max-per-account 10"
echo ""
