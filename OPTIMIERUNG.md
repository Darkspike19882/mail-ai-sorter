# AI Mail Sorter & Mac Optimierungen

## ✅ Durchgeführte Optimierungen

### 📧 Mail-Sorter (gemma4:e4b Modell)
- **delay_minutes: 30** - Paperless-ngx bekommt 30min für PDF-Extraktion
- **ollama_num_ctx: 8192** - Doppelter Context für bessere Klassifizierung
- **max_body_chars: 3000** - Mehr Text für genauere AI-Entscheidungen
- **ollama_num_predict: 50** - Optimiert für gemma4 Geschwindigkeit
- **Sender-Cache: 524 Einträge** - Spart ~80% AI-Calls durch gelernte Absender

### 💻 Mac-System
- **Brave Cache geleert** (+1.4GB freier Speicher)
- **Logitech Updater gestoppt** (sparte 35% CPU)
- **RAM optimiert** (+1.3GB freier RAM)
- **Ollama optimiert** - Läuft nur wenn benötigt

## 🚀 Weitere Optimierungsmöglichkeiten

### 1. Gemma4-Spezifische Optimierungen
```bash
# Testen Sie kleinere Gemma4-Varianten für mehr Speed:
ollama pull gemma4:9b  # 9B Parameter statt 12B (schneller)

# In config.json ändern:
"model": "gemma4:9b",
"ollama_num_predict": 30,  # Noch schnellere Antworten
"ollama_num_ctx": 4096,     # Standard context
```

### 2. System-Optimierungen
```bash
# Spotlight neu indizieren (bei CPU-Problemen):
sudo mdutil -E /

# TimeMachine lokale Snapshots reduzieren:
sudo tmutil disablelocal
# oder alle Snapshot auführen:
tmutil listlocalsnapshots /

# Hintergrund-Apps optimieren:
# • Brave Tabs schließen wenn nicht benötigt
# • WhatsApp manuell statt im Hintergrund
# • Spotify nur bei Bedarf starten
```

### 3. Mail-Sorter Performance
```bash
# Parallele Verarbeitung für mehrere Accounts:
./run.sh --parallel --max-per-account 100

# Testlauf bei Problemen:
./run.sh --dry-run --max-per-account 10 --days-back 1

# Alte Mails neu sortieren:
./run.sh --resort-folders --max-per-account 50
```

### 4. Monitoring & Debugging
```bash
# Status überblick:
./MONITORING.sh

# Mail-Suche im Index:
python3 index.py search "rettung"
python3 index.py search --category finanzen --since 2025-01-01

# Sender-Cache analysieren:
jq -r '.[]' learned_senders.json | sort | uniq -c | sort -rn | head -10
```

### 5. Automatisierung
```bash
# Launchd Job Status:
launchctl list | grep mail-ai-sorter

# Manuell neu starten:
launchctl kickstart -k gui/$(id -u)/com.michael.mail-ai-sorter

# Logs ansehen:
log show --predicate 'process == "mail-ai-sorter"' --last 1h
```

## 📊 Aktuelle Performance

**Mail-Sorter:**
- • 3.740 Mails indiziert
- • 524 gelernte Sender
- • Newsletter: 897 (meistens Regeln, keine AI-Kosten!)
- • Durchschnitt: ~2 Sekunden pro Mail (mit Cache)

**Mac-System:**
- • Freier RAM: ~2.5 GB (verbessert von ~1.3 GB)
- • Freier Speicher: 70 GB
- • CPU-Last: Reduziert durch Logitech-Stopp

## 🔧 Troubleshooting

**Ollama langsam?**
```bash
# Kleinere Modellvariante testen
ollama pull gemma4:9b
# In config.json: "model": "gemma4:9b"
```

**Mails werden nicht sortiert?**
```bash
# Delay prüfen (sollte 30 für Paperless):
grep "delay_minutes" config.json

# Dry-run für Debugging:
./run.sh --dry-run --max-per-account 5
```

**System zu langsam?**
```bash
# Cache leeren:
rm -rf ~/Library/Caches/BraveSoftware/*

# Spotlight neu indizieren:
sudo mdutil -E /

# Hintergrundsprozesse prüfen:
ps aux | sort -rk 3 | head -10
```

## 💡 Empfohlene Wartung

**Wöchentlich:**
- ./MONITORING.sh für Status-Check
- Mail-Suche bei Bedarf: `python3 index.py search "begriff"`

**Monatlich:**
- Cache leeren: Brave, WhatsApp
- TimeMachine Snapshots aufräumen
- Ollama Modelle updaten: `ollama pull gemma4:e4b`

**Bei Problemen:**
- Dry-run Testlauf
- Logs prüfen
- Ollama neustarten: `killall ollama && ollama serve`
