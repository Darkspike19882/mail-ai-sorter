# 📖 Installationsanleitung - Mail AI Sorter

## 🎯 Ziel

Emails automatisch mit lokaler KI sortieren - ohne Cloud, komplett auf deinem Mac!

## 📋 Voraussetzungen

### Hardware
- **Mac** mit Apple Silicon (M1 Pro/M2/M3 empfohlen)
- **mindestens 8GB RAM** (16GB empfohlen für llama3.1:8b)
- **5GB freier Speicher** für das KI-Modell

### Software
- **macOS 12+** (Monterey oder neuer)
- **Python 3.14+**
- **Homebrew** (für einfache Installation)
- **Ollama** (lokale KI)
- **IMAP-Email-Zugänge** (GMail, Outlook, etc.)

## 🚀 Schnellinstallation (5 Minuten)

### Schritt 1: Homebrew installieren (falls nicht vorhanden)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Schritt 2: Python und Abhängigkeiten installieren
```bash
# Python installieren
brew install python@3.14

# Repository klonen (ersetze mit deinem GitHub)
git clone https://github.com/dein-username/mail-ai-sorter.git
cd mail-ai-sorter

# Python-Abhängigkeiten installieren
pip3 install -r requirements.txt
```

### Schritt 3: Ollama installieren
```bash
# Ollama installieren
brew install ollama

# Ollama starten
ollama serve

# In neuem Terminal: llama3.1:8b Modell herunterladen
ollama pull llama3.1:8b
```

### Schritt 4: Konfiguration erstellen
```bash
# Beispiel-Konfiguration kopieren
cp config.example.json config.json

# config.json bearbeiten
nano config.json
```

### Schritt 5: Passwörter setzen
```bash
# Umgebungsvariablen erstellen
cp secrets.example.env secrets.env

# secrets.env bearbeiten
nano secrets.env
```

### Schritt 6: Testlauf
```bash
# Web UI starten
python3 web_ui.py

# Browser öffnen: http://localhost:5000
```

## 🔧 Detaillierte Konfiguration

### config.json

```json
{
  "global": {
    "model": "llama3.1:8b",
    "delay_minutes": 30,
    "max_body_chars": 3000,
    "categories": ["paperless", "apple", "finanzen", ...]
  },
  "accounts": [
    {
      "name": "Gmail",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "username": "deine@gmail.com",
      "password_env": "GMAIL_PASSWORD",
      "source_folder": "INBOX",
      "target_folders": {
        "paperless": "Paperless",
        "apple": "Apple",
        ...
      }
    }
  ]
}
```

### Email-Accounts einrichten

#### Google Mail (Gmail)
1. [App-Passwort erstellen](https://myaccount.google.com/apppasswords)
2. IMAP aktivieren in Gmail Settings
3. App-Passwort in secrets.env speichern

#### Outlook / Microsoft
1. [App-Passwort erstellen](https://account.live.com/proofs/AppPassword)
2. IMAP-Server: `outlook.office365.com:993`
3. Passwort in secrets.env speichern

#### Apple iCloud
1. [App-spezifisches Passwort erstellen](https://appleid.apple.com/account/manage)
2. IMAP-Server: `imap.mail.me.com:993`
3. Passwort in secrets.env speichern

#### GMX / Web.de
1. IMAP-Server: `imap.gmx.net:993` oder `imap.web.de:993`
2. Normales Passwort verwenden
3. Passwort in secrets.env speichern

## 🎨 Web UI nutzen

### Starten
```bash
python3 web_ui.py
```

### Features
- **📊 Dashboard** - Statistiken und Übersicht
- **⚙️ Konfiguration** - Einstellungen anpassen
- **🔍 Suche** - Emails durchsuchen
- **📋 Logs** - Live-Logs ansehen
- **🚀 Aktionen** - Sortierung starten

## 🧪 Testlauf

### Dry-Run (keine Änderungen)
```bash
./run.sh --dry-run --max-per-account 10
```

### Echte Sortierung
```bash
./run.sh --max-per-account 50
```

## 📊 Überprüfen

### Statistiken
```bash
python3 index.py stats
```

### Suche
```bash
python3 index.py search "newsletter"
```

## 🔍 Fehlersuche

### Problem: Ollama läuft nicht
```bash
# Ollama starten
ollama serve

# Prüfen
ps aux | grep ollama
```

### Problem: IMAP-Verbindung fehlschlägt
```bash
# IMAP-Zugang prüfen
telnet imap.gmail.com 993

# Passwort prüfen
echo $GMAIL_PASSWORD
```

### Problem: Keine Mails werden sortiert
```bash
# Logs prüfen
./run.sh --dry-run --max-per-account 5

# Konfiguration prüfen
cat config.json | python3 -m json.tool
```

## 🚀 Automatischer Start (Optional)

### Launchd Job für automatische Sortierung
```bash
./install_launchd.sh
```

Sortiert alle 5 Minuten automatisch deine Emails!

## 📱 Mobile Apps (Optional)

### Paperless-ngx App
- iOS: [App Store](https://apps.apple.com/app/paperless-ngx/id...)
- Android: [Google Play](https://play.google.com/store/apps/details?id=...)

### Web UI von überall
Mit SSH-Tunneling kannst du die Web UI von unterwegs nutzen:
```bash
ssh -L 5000:localhost:5000 dein-mac.local
```

## 🎓 Nächste Schritte

1. **Erste Sortierung** - Manuelles Sortieren von alten Emails
2. **Regeln anpassen** - Eigene Regeln erstellen
3. **Kategorien erweitern** - Neue Kategorien hinzufügen
4. **Statistiken analysieren** - Email-Gewohnheiten verstehen

## 💡 Tipps

- **Start klein** - Beginne mit 10 Emails pro Lauf
- **Dry-run nutzen** - Testen bevor du echt sortierst
- **Logs beobachten** - Siehst du genau was passiert
- **Regeln优先** - Regeln sind schneller als KI
- **Paperless-Integration** - 30min Delay beachten

## 🆘 Hilfe

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/dein-username/mail-ai-sorter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dein-username/mail-ai-sorter/discussions)

## ✅ Fertig!

Dein Mail AI Sorter ist jetzt einsatzbereit! 🎉

```bash
# Web UI starten
python3 web_ui.py

# Browser öffnen
open http://localhost:5000
```

Viel Spaß mit automatisch sortierten Emails! 📧✨
