# 🍎 macOS Installationsanleitung - Mail AI Sorter

**Intelligente Email-Sortierung mit lokaler KI - komplett auf deinem Mac!**

---

## 📋 Inhaltsverzeichnis

1. [Voraussetzungen prüfen](#voraussetzungen-prüfen)
2. [Installation in 5 Minuten](#installation-in-5-minuten)
3. [Einrichtung mit Setup-Wizard](#einrichtung-mit-setup-wizard)
4. [Email-Konto einrichten](#email-konto-einrichten)
5. [Erste Sortierung](#erste-sortierung)
6. [Automatischer Start](#automatischer-start)
7. [FAQ & Troubleshooting](#faq--troubleshooting)

---

## ✅ Voraussetzungen prüfen

### Hardware Check
Öffne **Über diesen Mac** ( → Über diesen Mac):

```
✅ Apple Silicon (M1/M2/M3/M1 Pro/M2 Pro/M3 Pro)
✅ Mindestens 8GB RAM (16GB empfohlen)
✅ 5GB freier Speicher
✅ macOS 12+ (Monterey oder neuer)
```

### Software Check
```bash
# Terminal öffnen (Cmd + Space → "Terminal")
# Diese Befehle nacheinander ausführen:

# Python Version prüfen
python3 --version
# Sollte: Python 3.14.3 oder höher

# Homebrew prüfen
brew --version
# Sollte: Homebrew 4.x.x
```

**Fehlt etwas?** Keine Sorge, wird installiert!

---

## 🚀 Installation in 5 Minuten

### Schritt 1: Homebrew installieren (falls fehlt)

**Warum?** Homebrew ist der Paketmanager für macOS - macht Installationen einfach.

```bash
# Terminal öffnen und diesen Befehl ausführen:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Erfolgsprüfung:**
```bash
brew --version
# Sollte anzeigen: Homebrew 4.x.x
```

---

### Schritt 2: Repository herunterladen

**Option A: Mit Git (empfohlen)**
```bash
# Git installieren (falls fehlt)
brew install git

# Repository klonen
git clone https://github.com/Darkspike19882/mail-ai-sorter.git
cd mail-ai-sorter
```

**Option B: Ohne Git (Download)**
1. Lade [ZIP von GitHub](https://github.com/Darkspike19882/mail-ai-sorter/archive/refs/heads/main.zip)
2. Entpacke die ZIP-Datei
3. Öffne Terminal im entpackten Ordner (Rechtsklick → "Dienstprogramme → Terminal")

**Erfolgsprüfung:**
```bash
ls
# Sollte anzeigen: INSTALL.md, README.md, web_ui.py, etc.
```

---

### Schritt 3: Python-Abhängigkeiten installieren

```bash
# Virtuelle Umgebung erstellen (empfohlen)
python3 -m venv venv

# Umgebung aktivieren
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

**Erfolgsprüfung:**
```bash
pip list | grep Flask
# Sollte anzeigen: Flask 3.1.3
```

---

### Schritt 4: Ollama installieren

**Ollama** ist die Software für die lokale KI.

```bash
# Ollama installieren
brew install ollama

# Ollama starten (läuft im Hintergrund)
ollama serve &

# Prüfen ob Ollama läuft
curl http://localhost:11434
# Sollte anzeigen: "Ollama is running"
```

---

### Schritt 5: KI-Modell herunterladen

**llama3.1:8b** - Das beste Modell für M1 Pro (16GB RAM).

```bash
# Modell herunterladen (~4.7GB)
ollama pull llama3.1:8b

# Prüfen ob Modell installiert
ollama list
# Sollte anzeigen: llama3.1:8b
```

**💡 Andere Modelle:**
```bash
# Falls weniger RAM: phi3:mini (~2GB)
ollama pull phi3:mini

# Falls mehr Präzision: gemma4:e4b (~4GB)
ollama pull gemma4:e4b
```

---

### Schritt 6: Testlauf!

```bash
# Terminal IMMER im mail-ai-sorter Ordner
# Virtuelle Umgebung aktivieren (falls nicht aktiv)
source venv/bin/activate

# Web UI starten
python3 web_ui.py
```

**Browser öffnen:**
```
http://localhost:5001/setup
```

**🎉 Sollte anzeigen: Setup Wizard mit Willkommensseite!**

---

## 🧙 Einrichtung mit Setup-Wizard

Der **Setup Wizard** führt dich durch 7 Schritte:

### Schritt 1: Willkommen 🎉
- Überblick der Features
- Voraussetzungen Check

### Schritt 2: Ollama Prüfung 🔍
- **Automatische Prüfung** ob Ollama läuft
- **Automatische Prüfung** ob llama3.1:8b installiert
- Zeigt Fehlerfalls Installations-Befehle

**Troubleshooting:**
```bash
# Falls Ollama nicht gefunden:
ollama serve &
ollama pull llama3.1:8b
```

### Schritt 3: Email-Konto hinzufügen 📧

**Schnell-Vorlagen wählen:**

| Anbieter | IMAP Server | Port |
|----------|-------------|------|
| **Gmail** | imap.gmail.com | 993 |
| **iCloud** | imap.mail.me.com | 993 |
| **Outlook** | outlook.office365.com | 993 |
| **GMX** | imap.gmx.net | 993 |

**Beispiel Gmail:**
```
Konto-Name: Gmail
IMAP Server: imap.gmail.com
Port: 993
Benutzername: deine@gmail.com
Passwort: [App-Passwort siehe unten]
Quellordner: INBOX
```

**Kategorien-Ordner werden automatisch erstellt!**

### Schritt 4: Kategorien wählen 📁

Alle 15 Kategorien aktivieren oder wählen:
- ✅ paperless (Rechnungen, Belege)
- ✅ apple (Apple-Dienste)
- ✅ finanzen (Bank, PayPal)
- ✅ einkauf (Amazon, DHL)
- ✅ privat (Alles andere)

### Schritt 5: KI-Modell wählen 🤖

| Modell | RAM | Speed | Genauigkeit | Für wen? |
|--------|-----|-------|-------------|----------|
| **llama3.1:8b** | 7GB | ⚡⚡⚡⚡ | 92% | **M1 Pro 16GB** (Empfohlen) |
| **gemma4:e4b** | 10GB | ⚡⚡⚡ | 95% | Präzision > Speed |
| **phi3:mini** | 5GB | ⚡⚡⚡⚡⚡ | 88% | Weniger RAM |

### Schritt 6: Paperless-Integration 📄

**30-Minuten Regel:**
```
0 Minuten   = Sofort sortieren
30 Minuten  = Empfohlen für Paperless-ngx
60 Minuten  = Falls PDF-Extraktion länger dauert
```

**Ohne Paperless?** Auf 0 Minuten stellen!

### Schritt 7: Zusammenfassung ✅

Prüfen:
- ✅ KI-Modell: llama3.1:8b
- ✅ Konten: 1 konfiguriert
- ✅ Kategorien: 15 aktiv
- ✅ Verzögerung: 30 Minuten

**Klick auf "Setup abschließen"**

---

## 📧 Email-Konto einrichten

### Google Mail (Gmail)

**Schritt 1: App-Passwort erstellen**
1. Öffne [Google App-Passwörter](https://myaccount.google.com/apppasswords)
2. Wähle "Mail" und dein Mac
3. Kopiere das generierte Passwort (16 Zeichen)

**Schritt 2: IMAP aktivieren**
1. Öffne [Gmail Settings](https://mail.google.com/mail/u/0/#settings/fwdandpop)
2. Aktiviere "IMAP-Zugriff"
3. Speichern

**Schritt 3: Eintragen**
```
IMAP Server: imap.gmail.com
Port: 993
Benutzername: deine@gmail.com
Passwort: xxxx xxxx xxxx xxxx (App-Passwort)
```

### Apple iCloud

**Schritt 1: App-spezifisches Passwort**
1. Öffne [appleid.apple.com](https://appleid.apple.com/account/manage)
2. "App-spezifische Passwörter" → "Passwort erstellen"
3. Label: "Mail AI Sorter"
4. Kopiere das Passwort

**Schritt 2: Eintragen**
```
IMAP Server: imap.mail.me.com
Port: 993
Benutzername: deine@icloud.com
Passwort: [App-Passwort]
```

### Outlook / Microsoft 365

**Schritt 1: App-Passwort**
1. Öffne [Microsoft Account](https://account.live.com/proofs/AppPassword)
2. "Neues Passwort erstellen"
3. Kopiere das Passwort

**Schritt 2: Eintragen**
```
IMAP Server: outlook.office365.com
Port: 993
Benutzername: deine@outlook.com
Passwort: [App-Passwort]
```

### GMX / Web.de

**Kein App-Passwort nötig!** Normales Passwort verwenden.

```
IMAP Server: imap.gmx.net (bzw. imap.web.de)
Port: 993
Benutzername: deine@gmx.de
Passwort: [Dein normales Passwort]
```

---

## 🎬 Erste Sortierung

### Testlauf (Dry-Run) - **EMPFOHLEN!**

**Web UI:**
1. Öffne http://localhost:5001
2. Klick "Testlauf (Dry-Run, 10 Mails)"
3. Prüfe die Ergebnisse

**Oder Terminal:**
```bash
# Terminal im mail-ai-sorter Ordner
source venv/bin/activate

./run.sh --dry-run --max-per-account 10
```

**Was passiert:**
- ✅ Prüft 10 Emails pro Konto
- ✅ Kategorisiert mit KI
- ✅ Zeigt Ergebnisse an
- ❌ **Verschiebt NICHTS** (sicher!)

### Echte Sortierung

**Nach erfolgreichem Testlauf:**

**Web UI:**
1. Klick "Emails sortieren (50)"
2. Bestätige mit "OK"
3. Sortiert 50 Emails pro Konto

**Terminal:**
```bash
./run.sh --max-per-account 50
```

**⚠️ WARNUNG:** Jetzt werden Emails **wirklich verschoben!**

---

## ⚙️ Automatischer Start

### Option 1: Launch Agent (macOS native)

**Vorteil:** Startet automatisch beim Login

```bash
# Im mail-ai-sorter Ordner
cat > ~/Library/LaunchAgents/com.mailaisorter.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mailaisorter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd /Users/$USER/mail-ai-sorter && source venv/bin/activate && ./run.sh --max-per-account 10</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

# Pfad anpassen!
nano ~/Library/LaunchAgents/com.mailaisorter.plist
# Ändere: /Users/$USER/mail-ai-sorter
# Zu deinem echten Pfad: /Users/dein-username/mail-ai-sorter

# Aktivieren
launchctl load ~/Library/LaunchAgents/com.mailaisorter.plist

# Prüfen
launchctl list | grep mailaisorter
```

**Deaktivieren:**
```bash
launchctl unload ~/Library/LaunchAgents/com.mailaisorter.plist
```

### Option 2: Cron Job (Einfach)

**Alle 5 Minuten:**
```bash
# Crontab Editor öffnen
crontab -e

# Diese Zeile hinzufügen (Pfad anpassen!):
*/5 * * * * cd /Users/dein-username/mail-ai-sorter && source venv/bin/activate && ./run.sh --max-per-account 10 >> mail_sorter.log 2>&1

# Speichern: Esc + :wq + Enter
```

**Cron prüfen:**
```bash
crontab -l
```

**Cron löschen:**
```bash
crontab -e
# Zeile löschen und speichern
```

---

## 🔧 FAQ & Troubleshooting

### ❌ "Ollama not found"

**Problem:** Ollama ist nicht installiert oder nicht in PATH.

**Lösung:**
```bash
# Ollama installieren
brew install ollama

# Ollama starten
ollama serve &

# Prüfen
curl http://localhost:11434
```

---

### ❌ "llama3.1:8b not found"

**Problem:** Modell nicht heruntergeladen.

**Lösung:**
```bash
# Modell herunterladen
ollama pull llama3.1:8b

# Prüfen
ollama list
```

---

### ❌ "IMAP connection failed"

**Problem:** Verbindung zum Email-Server fehlschlägt.

**Lösung:**
```bash
# IMAP-Zugang prüfen
telnet imap.gmail.com 993
# Sollte: Connected to imap.gmail.com

# Falls "Connection refused":
# 1. IMAP im Email-Service aktivieren
# 2. Firewall prüfen
# 3. App-Passwort verwenden (nicht normales Passwort!)
```

---

### ❌ "Authentication failed"

**Problem:** Falsches Passwort oder Benutzername.

**Lösung:**
```bash
# 1. App-Passwort verwenden (nicht Account-Passwort!)
# 2. Benutzername prüfen (komplette Email-Adresse)
# 3. IMAP im Email-Service aktiviert?

# Für Gmail:
# Settings → Forwarding and POP/IMAP → IMAP access: Enable
```

---

### ❌ "Port 5001 already in use"

**Problem:** Web UI läuft bereits.

**Lösung:**
```bash
# Prozess beenden
lsof -ti:5001 | xargs kill -9

# Neu starten
python3 web_ui.py
```

---

### ❌ "No module named 'flask'"

**Problem:** Python-Abhängigkeiten nicht installiert.

**Lösung:**
```bash
# Virtuelle Umgebung aktivieren
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

---

### ❌ "Sortierung läuft ewig"

**Problem:** Zu viele Emails auf einmal.

**Lösung:**
```bash
# Weniger Emails auf einmal
./run.sh --max-per-account 10

# Oder schnelleres Modell
# In config.json:
"model": "phi3:mini"  # Statt llama3.1:8b
```

---

### ❌ "Emails werden nicht verschoben"

**Problem:** Dry-Run aktiv oder Zielordner existieren nicht.

**Lösung:**
```bash
# 1. Dry-Run deaktivieren
./run.sh --max-per-account 10  # Ohne --dry-run!

# 2. Zielordner manuell erstellen
# In Gmail/Outlook/etc. die Ordner erstellen:
# - Paperless
# - Apple
# - Finanzen
# - etc.
```

---

### ❌ "Memory Error"

**Problem:** Zu wenig RAM für Modell.

**Lösung:**
```bash
# Kleineres Modell verwenden
ollama pull phi3:mini

# In config.json ändern:
"model": "phi3:mini"
```

---

## 🎓 Tipps & Tricks

### Performance optimieren

```json
// config.json
{
  "global": {
    "max_body_chars": 2000,      // Weniger Text = Schneller
    "delay_minutes": 0,           // Keine Verzögerung = Sofort
    "model": "phi3:mini"          // Schnelleres Modell
  }
}
```

### Genauigkeit verbessern

```json
// config.json
{
  "global": {
    "max_body_chars": 5000,      // Mehr Text = Genauer
    "model": "gemma4:e4b"         // Präziseres Modell
  }
}
```

### Alte Emails sortieren

```bash
# Alle Emails (VORSICHT!)
./run.sh --all --max-per-account 1000

# Mit Timeout für langsame Konten
export IMAP_TIMEOUT_SEC=60
./run.sh --max-per-account 100
```

### Logs analysieren

```bash
# Live Logs ansehen
tail -f mail_sorter.log

# Fehler suchen
grep ERROR mail_sorter.log

# Statistiken
python3 index.py stats
```

---

## 🆘 Hilfe bekommen

### Debug Modus

```bash
# Ausführliche Logs
./run.sh --dry-run --max-per-account 5 -v
```

### Logs teilen

```bash
# Letzte 50 Zeilen
tail -n 50 mail_sorter.log

# In GitHub Issue posten
```

### Community

- **GitHub Issues:** [Hier klicken](https://github.com/Darkspike19882/mail-ai-sorter/issues)
- **GitHub Discussions:** [Hier klicken](https://github.com/Darkspike19882/mail-ai-sorter/discussions)

---

## ✅ Erfolgsprüfung

### Quick Check

```bash
# Terminal im mail-ai-sorter Ordner
source venv/bin/activate

# 1. Web UI starten
python3 web_ui.py

# 2. Browser öffnen
open http://localhost:5001

# 3. Sollte anzeigen: Dashboard mit Statistiken
```

### Funktionsprüfung

```bash
# Testlauf
./run.sh --dry-run --max-per-account 5

# Sollte:
# ✅ "Sortiere Emails von Konto..."
# ✅ "KI-Klassifizierung läuft..."
# ✅ "Kategorisiert als: xxx"
# ❌ "Verschoben nach: xxx" (Dry-Run!)
```

---

## 🎉 Fertig!

Dein **Mail AI Sorter** ist jetzt einsatzbereit!

### Nächste Schritte:

1. **📊 Dashboard öffnen** - http://localhost:5001
2. **🧪 Testlauf starten** - 10 Emails testen
3. **📧 Erste Sortierung** - 50 Emails sortieren
4. **⚙️ Regeln anpassen** - Bei Bedarf
5. **🔄 Automatisierung** - Launch Agent einrichten

### Web UI Features:

- 📊 **Dashboard** - Live-Statistiken
- ⚙️ **Konfiguration** - Alles editierbar
- 🔍 **Suche** - Emails finden
- 📋 **Logs** - Live-Monitoring

---

**Viel Spaß mit automatisch sortierten Emails!** 📧✨

*Fragen? Probleme? GitHub Issues erstellen!*
