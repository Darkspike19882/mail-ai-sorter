# 🚀 Quick Start - Mail AI Sorter

**In 5 Minuten einsatzbereit auf deinem Mac!**

---

## 🎯 Die Schnellste Methode (Automatisch)

```bash
# 1. Terminal öffnen (Cmd + Space → "Terminal")

# 2. In den Download-Ordner wechseln
cd Downloads

# 3. Repository klonen
git clone https://github.com/Darkspike19882/mail-ai-sorter.git
cd mail-ai-sorter

# 4. Automatischen Installer starten
./install.sh

# 5. Fertig! Im Setup Wizard einrichten:
source venv/bin/activate
python3 web_ui.py

# 6. Browser öffnen: http://localhost:5001/setup
```

**Das ist alles!** 🎉

---

## 📋 Manuelle Installation (falls Script fehlschlägt)

Siehe [INSTALL.md](INSTALL.md) für detaillierte Schritte.

Kurzversion:
```bash
# 1. Homebrew installieren
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Ollama installieren
brew install ollama
ollama serve &
ollama pull llama3.1:8b

# 3. Python Abhängigkeiten
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Konfiguration
cp config.example.json config.json
cp secrets.example.env secrets.env

# 5. Starten
python3 web_ui.py

# 6. Browser: http://localhost:5001/setup
```

---

## 🎬 Erste Schritte nach der Installation

### 1. Setup Wizard ausfüllen

Öffne http://localhost:5001/setup und folge den 7 Schritten:

- ✅ Willkommen
- ✅ Ollama Prüfung (automatisch)
- ✅ Email-Konto hinzufügen
- ✅ Kategorien wählen
- ✅ KI-Modell wählen
- ✅ Paperless-Integration
- ✅ Zusammenfassung

### 2. Erster Testlauf

**Im Dashboard:**
- Klick "Testlauf (Dry-Run, 10 Mails)"
- Prüfe die Ergebnisse

**Oder Terminal:**
```bash
./run.sh --dry-run --max-per-account 10
```

### 3. Echte Sortierung

Nach erfolgreichem Test:
```bash
./run.sh --max-per-account 50
```

---

## 📧 Email-Konto einrichten

### Gmail
1. [App-Passwort erstellen](https://myaccount.google.com/apppasswords)
2. IMAP aktivieren in Settings
3. Im Setup Wizard eintragen

### iCloud
1. [App-Passwort erstellen](https://appleid.apple.com/account/manage)
2. IMAP: imap.mail.me.com:993
3. Im Setup Wizard eintragen

### Outlook
1. [App-Passwort erstellen](https://account.live.com/proofs/AppPassword)
2. IMAP: outlook.office365.com:993
3. Im Setup Wizard eintragen

### GMX
- IMAP: imap.gmx.net:993
- Normales Passwort verwenden

---

## ❌ Probleme?

### "Ollama not found"
```bash
brew install ollama
ollama serve &
ollama pull llama3.1:8b
```

### "No module named 'flask'"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "IMAP connection failed"
- App-Passwort verwenden (nicht Account-Passwort!)
- IMAP im Email-Service aktivieren
- Firewall prüfen

**Mehr Lösungen:** Siehe [INSTALL.md](INSTALL.md) → FAQ & Troubleshooting

---

## 🎉 Fertig!

Dein Mail AI Sorter läuft!

- **Dashboard:** http://localhost:5001
- **Konfiguration:** http://127.0.0.1:5001/config
- **Logs:** http://127.0.0.1:5001/logs

**Viel Spaß!** 📧✨

---

*Need help?* [GitHub Issues](https://github.com/Darkspike19882/mail-ai-sorter/issues)
