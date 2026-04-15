# 🚀 Mail AI Sorter - Erweiterungen aktivieren

## ⚡ Schnellstart für Erweiterungen

### **Schritt 1: Erweiterungen aktivieren**

In deiner `config.json` unter `global.extensions`:

```json
{
  "global": {
    "extensions": {
      "enabled": true,
      "paperless_enabled": true,
      "calendar_enabled": true,
      "tasks_enabled": true,
      "notifications_enabled": true
    }
  }
}
```

### **Schritt 2: Paperless-ngx installieren (optional)**

```bash
# Docker installieren
brew install docker

# Paperless-ngx starten
docker run -d --name paperless-ngx \
  -v paperless_data:/usr/src/paperless/data \
  -v paperless_media:/usr/src/paperless/media \
  -v paperless_export:/usr/src/paperless/export \
  -v paperless_consume:/usr/src/paperless/consume \
  -p 8000:8000 \
  ghcr.io/paperless-ngx/paperless-ngx:latest \
  paperless-ngx

# API Token erstellen
open http://localhost:8000
# Einstellungen → API Tokens → Neuer Token

# Token in config.json eintragen
"paperless_api_token": "DEIN_TOKEN_HIER"
```

### **Schritt 3: Kalender installieren (optional)**

```bash
# gcalcli installieren
brew install gcalcli

# Google Calendar autorisieren
gcalcli list

# Erster Test
gcalcli --calendar "Hauptkalender" add --title "Test" --when "tomorrow 10:00" --duration "60"
```

### **Schritt 4: Task-Management installieren (optional)**

```bash
# Taskwarrior installieren
brew install taskwarrior

# Erste Aufgabe
task add "Testaufgabe von Mail AI Sorter"

# Alle Aufgaben anzeigen
task list
```

## 🎯 Welche Erweiterungen gibt es?

### **1. 📄 Paperless-ngx Integration**
- **Was:** Emails automatisch als Dokumente in Paperless-ngx speichern
- **Für welche Kategorien:** `paperless`, `finanzen`, `vertraege`, `einkauf`
- **Vorteil:** Alle wichtigen Dokumente automatisch zentralisiert

### **2. 📅 Kalender-Integration**
- **Was:** Termine automatisch aus Emails extrahieren und eintragen
- **Für welche Kategorien:** `arbeit`, `reisen`, `termin`
- **Vorteil:** Nie mehr Termine verpassen

### **3. ✅ Task-Management**
- **Was:** Aus Emails automatisch Aufgaben erstellen
- **Für welche Kategorien:** `arbeit`, `finanzen`, `behoerden`, `vertraege`
- **Vorteil:** Wichtige To-dos nicht vergessen

### **4. 🔔 Smart Notifications**
- **Was:** Desktop-Benachrichtigungen bei wichtigen Emails
- **Für welche Kategorien:** `arbeit`, `finanzen`, `behoerden`
- **Vorteil:** Sofortige Reaktion auf Wichtiges

## 🔧 Konfiguration

### **Paperless-ngx**

```json
{
  "paperless_enabled": true,
  "paperless_url": "http://localhost:8000",
  "paperless_api_token": "DEIN_TOKEN_AUS_PAPERLESS"
}
```

**API Token erstellen:**
1. Paperless-ngx öffnen: `http://localhost:8000`
2. Rechts oben auf dein Profil klicken
3. "API Tokens" → "Neuer Token"
4. Token kopieren und in config.json einfügen

### **Kalender**

```json
{
  "calendar_enabled": true
}
```

**Kalender-Namen anpassen:**
In `extensions.py` den Kalender-Namen ändern:
```python
"--calendar", "DEIN_KALENDER_NAME",
```

### **Tasks**

```json
{
  "tasks_enabled": true,
  "task_system": "taskwarrior"
}
```

**Verfügbare Systeme:**
- `taskwarrior` (empfohlen, mächtig)
- `todo.txt` (einfach, textbasiert)

### **Benachrichtigungen**

```json
{
  "notifications_enabled": true,
  "notification_categories": ["arbeit", "finanzen", "behoerden"]
}
```

**Kategorien anpassen:**
Nur diese Kategorien lösen Benachrichtigungen aus.

## 🎛️ Pro-Tipps

### **Nur bestimmte Erweiterungen aktivieren**

```json
{
  "extensions": {
    "enabled": true,
    "notifications_enabled": true,
    "notification_categories": ["arbeit", "finanzen"]
  }
}
```

### **Erweiterungen pro Kategorie steuern**

Du kannst in `extensions.py` die Zeile mit:
```python
if category in ["arbeit", "reisen", "termin"]:
```
anpassen, um genau zu steuern, wann welche Erweiterung aktiv wird.

### **Testlauf ohne Aktionen**

```bash
# Dry-run um zu sehen, was passieren würde
python3 sorter.py --dry-run --max-per-account 5
```

## 🐛 Troubleshooting

### **Paperless-ngx Verbindung fehlgeschlagen**
- ✅ Paperless-ngx läuft: `docker ps | grep paperless`
- ✅ API Token korrekt: Einstellungen → API Tokens → Neuer Token
- ✅ URL korrekt: `http://localhost:8000` (nicht https!)

### **Kalender funktioniert nicht**
- ✅ gcalcli installiert: `brew install gcalcli`
- ✅ Google Calendar autorisiert: `gcalcli list`
- ✅ Kalender-Name existiert: `gcalcli list` zeigt alle Kalender

### **Tasks werden nicht erstellt**
- ✅ taskwarrior installiert: `brew install taskwarrior`
- ✅ TaskSystem korrekt: `"task_system": "taskwarrior"`

### **Benachrichtigungen fehlen**
- ✅ macOS Benachrichtigungen aktiv: Systemeinstellungen → Benachrichtigungen
- ✅ Kategorie in `notification_categories` enthalten

## 📊 Was passiert im Hintergrund?

### **Bei jeder Email:**

1. **Kategorisierung** (wie bisher)
2. **Erweiterungen prüfen** (ist category in der Liste?)
3. **Aktion ausführen** (Paperless, Kalender, Task, Benachrichtigung)
4. **Log schreiben** (✅ oder ❌)

### **Beispiel Ablauf:**

```
[2026-04-15 10:30:00] [Gmail] llm → finanzen: Rechnung von Amazon
✅ Nach Paperless-ngx gesendet
✅ Aufgabe erstellt
[Gmail] moved → Finanzen: Rechnung von Amazon
```

## 🚀 nächste Schritte

1. **Paperless-ngx installieren** (wenn du Dokumente verwalten willst)
2. **Kalender autorisieren** (wenn du Termine automatisieren willst)
3. **Tasks installieren** (wenn du produktiver sein willst)
4. **Benachrichtigungen aktivieren** (wenn du sofort reagieren willst)

## 💡 Mehr Infos

- Detaillierte Dokumentation: `EXTENSIONS.md`
- Video-Tutorials: Kommen bald
- Community: GitHub Discussions

---

**Viel Erfolg mit deinen Erweiterungen!** 🎉
