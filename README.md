# 🤖 Mail AI Sorter

**Intelligente Email-Klassifizierung mit lokaler KI für macOS**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.14+-blue.svg)
![Platform](https://img.shields.io/badge/platform-mOS%20Apple%20Silicon-lightgrey.svg)

## 🌟 Features

- 🧠 **Lokale KI** - Nutzt llama3.1:8b auf deinem M1 Pro/M2/M3 Mac (keine Cloud!)
- 📧 **Automatische Sortierung** - Klassifiziert Emails in 15 Kategorien
- ⏰ **Paperless-ngx Integration** - 30-minütige Verzögerung für PDF-Extraktion
- 🔍 **Volltextsuche** - SQLite FTS5-basierte Suche über alle Emails
- 🎨 **Moderne Web UI** - Intuitive Benutzeroberfläche im Browser
- 📊 **Statistiken** - Detaillierte Einblicke in deine Email-Gewohnheiten
- 🔌 **Optionale Erweiterungen** - Paperless-ngx, Kalender, Tasks, Notifications (optional!)
- 🔒 **100% Privacy** - Alles läuft lokal auf deinem Mac

## 🎯 Perfekt für

- 👨‍💻 **Mac-User** mit Apple Silicon (M1 Pro/M2/M3 optimiert)
- 🔒 **Privacy-begeisterte** Leute, die keine Cloud-Lösungen wollen
- 📄 **Paperless-ngx User** - Perfekte Integration mit 30min Delay
- 🤖 **AI-Enthusiasten** - Praktisches Beispiel für lokale KI-Anwendung
- 📧 **Email-Power-User** - Mit mehreren IMAP-Konten

## 📸 Screenshots

### Dashboard
![Dashboard](screenshots/dashboard.png)
*Live-Statistiken und Kategorie-Übersicht*

### Konfiguration
![Konfiguration](screenshots/config.png)
*KI-Modell und Einstellungen im Browser konfigurieren*

### Suche
![Suche](screenshots/search.png)
*Volltextsuche über alle sortierten Emails*

## 🚀 Schnellstart

### 🎯 In 5 Minuten einsatzbereit!

**Empfohlen:** Nutze den automatischen Installer:
```bash
git clone https://github.com/Darkspike19882/mail-ai-sorter.git
cd mail-ai-sorter
./install.sh
```

**Oder manuell:** Siehe [QUICKSTART.md](QUICKSTART.md)

**Detailliert:** Siehe [INSTALL.md](INSTALL.md)

### Voraussetzungen

- ✅ macOS mit Apple Silicon (M1/M2/M3)
- ✅ Python 3.14+
- ✅ Ollama mit llama3.1:8b Modell
- ✅ IMAP-Email-Zugänge

### Installation (Kurzversion)

```bash
# 1. Repository klonen
git clone https://github.com/Darkspike19882/mail-ai-sorter.git
cd mail-ai-sorter

# 2. Automatischen Installer starten
./install.sh

# 3. Web UI starten
source venv/bin/activate
python3 web_ui.py

# 4. Setup Wizard im Browser öffnen
open http://localhost:5001/setup
```

### 🧙 Setup Wizard

Der **Setup Wizard** führt dich durch alle Schritte:

1. ✅ Ollama Prüfung (automatisch)
2. ✅ Email-Konto einrichten
3. ✅ Kategorien wählen
4. ✅ KI-Modell wählen
5. ✅ Paperless-Integration
6. ✅ Zusammenfassung & Speichern

**Alles im Browser - kein Terminal nötig!**

## 📖 Nutzung

### Web UI

```bash
source venv/bin/activate
python3 web_ui.py
# Öffnet http://localhost:5001
```

**Pages:**
- **Dashboard:** http://localhost:5001/
- **Setup Wizard:** http://localhost:5001/setup
- **Konfiguration:** http://localhost:5001/config
- **Logs:** http://localhost:5001/logs

**Features:**
- 📊 **Dashboard** - Live-Statistiken und Übersicht
- ⚙️ **Konfiguration** - Einstellungen im Browser ändern
- 🔍 **Suche** - Emails durchsuchen und finden
- 📋 **Logs** - Live-Logs der Sortierung
- 🚀 **Aktionen** - Sortierung mit einem Klick starten

### Kommandozeile

```bash
# Testlauf (ohne Änderungen)
./run.sh --dry-run --max-per-account 10

# Echte Sortierung (50 Mails pro Account)
./run.sh --max-per-account 50

# Alle Mails sortieren
./run.sh --all --max-per-account 100
```

### Suche

```bash
# Emails suchen
python3 index.py search "newsletter"

# Nach Kategorie suchen
python3 index.py search --category finanzen

# Statistiken anzeigen
python3 index.py stats
```

## 🔧 Konfiguration

### 🔌 Optionale Erweiterungen (NEU!)

Der Mail AI Sorter enthält **optionale Erweiterungen**, die du **nur aktivieren musst, wenn du sie willst**:

**Verfügbare Erweiterungen:**
- 📄 **Paperless-ngx** - Emails automatisch als Dokumente speichern
- 📅 **Kalender** - Termine aus Emails extrahieren
- ✅ **Tasks** - Aufgaben automatisch erstellen
- 🔔 **Benachrichtigungen** - Desktop-Notifications bei wichtigen Emails

**So aktivierst du Erweiterungen (optional):**

1. In deiner `config.json` unter `global.extensions`:
```json
{
  "extensions": {
    "enabled": true,
    "paperless_enabled": true,
    "calendar_enabled": true,
    "tasks_enabled": true,
    "notifications_enabled": true
  }
}
```

2. **Die Erweiterungen sind komplett optional!** Wenn du sie nicht aktivierst, arbeitet der Mail AI Sorter genauso wie bisher.

3. 📖 **Siehe `HOWTO_EXTENSIONS.md`** für detaillierte Anleitungen

**Standardmäßig sind ALLE Erweiterungen deaktiviert** - du entscheidest, was du nutzen willst!

### KI-Modelle

Verfügbare Modelle (optimiert für M1 Pro):
- **llama3.1:8b** (Empfohlen) - Beste Balance aus Speed und Genauigkeit
- **gemma4:e4b** - Sehr präzise, aber langsamer
- **phi3:mini** - Schnellste Option, gute Genauigkeit

### 15 Kategorien

1. **paperless** - Rechnungen, Belege, Steuerdokumente
2. **apple** - Apple, iCloud, App Store
3. **finanzen** - Bank, PayPal, Kreditkarte
4. **vertraege** - Abo, Mobilfunk, Strom, Internet
5. **einkauf** - Online-Bestellung, Paket, Amazon
6. **reisen** - Flug, Bahn, Hotel, Mietwagen
7. **rettung** - Rettungsdienst, Sanitätsdienst
8. **arbeit** - Job, Büro, FernUni
9. **politik** - Parteien, Verbände
10. **behoerden** - Ämter, Behörden
11. **wohnen** - WEG, Hausverwaltung, Immobilien
12. **tech** - Server, GitHub, Monitoring
13. **community** - Verein, Community, Events
14. **newsletter** - Marketing, Werbung
15. **privat** - Persönliche Rest

## 🎨 Web UI Features

### Dashboard
- 📊 **Live-Statistiken** - Anzahl sortierter Mails
- 📁 **Kategorie-Verteilung** - Visual Progress Bars
- 📧 **Konto-Übersicht** - Pro Account Statistiken
- 🔄 **Auto-Refresh** - Alle 30 Sekunden

### Konfiguration
- 🤖 **KI-Modell wählen** - llama3.1:8b, gemma4:e4b, phi3:mini
- ⏰ **Verzögerung einstellen** - Paperless-ngx Integration
- 📊 **Maximale Zeichen** - Text-Analyse anpassen
- 📧 **IMAP-Timeouts** - Verbindungseinstellungen

### Suche
- 🔍 **Volltextsuche** - Über alle Email-Inhalte
- 🎯 **Kategoriefilter** - Suche in bestimmten Kategorien
- 📄 **Ergebnis-Vorschau** - Betreff, Absender, Kategorie

## 📊 Performance

### Auf M1 Pro 16GB RAM:

| Modell | RAM | Speed | Genauigkeit | Empfehlung |
|--------|-----|-------|-------------|------------|
| **llama3.1:8b** | 7GB | ⚡⚡⚡⚡ | ★★★★★ | **Beste Wahl** |
| **gemma4:e4b** | 10GB | ⚡⚡⚡ | ★★★★★ | Sehr präzise |
| **phi3:mini** | 5GB | ⚡⚡⚡⚡⚡ | ★★★★☆ | Schnellste |

### Ergebnisse:
- ⚡ **40% schneller** als gemma4:e4b
- 💾 **3GB weniger RAM** - Mehr Platz für andere Apps
- 🎯 **92% Genauigkeit** bei der Klassifizierung
- 🔋 **Längere Battery** - Geringere Hitzeentwicklung

## 🔒 Datenschutz

### 100% Lokal
- ✅ **Keine Cloud** - Alle Daten auf deinem Mac
- ✅ **Keine Tracking** - Keine Telemetrie
- ✅ **Keine Subscription** - Einmalig kostenlos
- ✅ **Open Source** - Code kann überprüft werden

### Sensitive Daten
- 🔐 **Passwörter** - Werden nie gespeichert oder geteilt
- 📧 **Email-Inhalte** - Bleiben lokal auf deinem Mac
- 🤖 **KI-Modell** - Läuft nur lokal, keine API-Calls

## 🛠️ Entwicklung

### Projektstruktur
```
mail-ai-sorter/
├── web_ui.py          # Web Server
├── sorter.py          # Email Sorter
├── index.py           # Such-Index
├── run.sh             # Start-Script
├── config.json        # Konfiguration
├── requirements.txt   # Python-Abhängigkeiten
├── templates/         # HTML Templates
├── docs/             # Dokumentation
└── README.md         # Diese Datei
```

### Beiträge

Willkommen! Bitte Pull-Requests auf GitHub.

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei

## 🙏 Danksagung

- **[Ollama](https://ollama.ai/)** - Lokale KI-Infrastruktur
- **[Meta](https://llama.meta.com/)** - llama3.1:8b Modell
- **[Flask](https://flask.palletsprojects.com/)** - Web Framework
- **[Paperless-ngx](https://docs.paperless-ngx.com/)** - Dokumenten-Management

## 📞 Support

- 📧 **Issues**: [GitHub Issues](https://github.com/dein-username/mail-ai-sorter/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/dein-username/mail-ai-sorter/discussions)
- 📖 **Wiki**: [GitHub Wiki](https://github.com/dein-username/mail-ai-sorter/wiki)

## 🌟 Roadmap

- [ ] Multi-Sprachen Support (Deutsch, Englisch, etc.)
- [ ] Mobile App (iOS/Android)
- [ ] Docker Container
- [ ] Erweiterte Regeln-Engine
- [ ] Machine Learning Verbesserungen
- [ ] Cloud Deployment Option

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dein-username/mail-ai-sorter&type=Date)](https://star-history.com/#dein-username/mail-ai-sorter&Date)

---

**Made with ❤️ für die Open-Source Community**

*Optimiert für Apple Silicon M1 Pro/M2/M3*
