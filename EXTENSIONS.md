# 🚀 Mail AI Sorter - Erweiterungen mit Open Source Tools

## 🌟 Top 5 Most Valuable Extensions

### **1. 📄 Paperless-ngx Deep Integration (HOCHSTE PRIORITÄT)**

**Warum:** Perfekte Ergänzung zur 30-minütigen Regel!

**Features:**
```python
✅ API-Integration: Emails → Paperless Dokumente
✅ Auto-Tagging: Kategorien → Paperless Tags
✅ Document Type Recognition: Rechnung, Vertrag, etc.
✅ PDF-Preview: Anhänge automatisch importieren
✅ Storage Path: Intelligentes Ablegen
```

**Installation:**
```bash
# Paperless-ngx Docker
brew install docker
docker run -d --name paperless-ngx \
  -v /mnt/paperless/data:/usr/src/paperless/data \
  -v /mnt/paperless/media:/usr/src/paperless/media \
  -v /mnt/paperless/export:/usr/src/paperless/export \
  -v /mnt/paperless/consume:/usr/src/paperless/consume \
  -p 8000:8000 \
  ghcr.io/paperless-ngx/paperless-ngx:latest \
  paperless-ngx

# In sort.py integrieren
python3 -m pip install requests
```

**Value Add:**
- ⭐⭐⭐⭐⭐ Perfekte Synchronisation
- ⭐⭐⭐⭐⭐ Automatische Dokumenten-Klassifizierung
- ⭐⭐⭐⭐⭐ Weniger manuelle Arbeit

---

### **2. 🤖 KI-Zusammenfassungen & Entitäten-Extraktion**

**Warum:** Emails automatisch zusammenfassen und relevante Daten extrahieren!

**Features:**
```python
✅ Summarization: Lange Emails → 3-Satz Zusammenfassung
✅ Entity Extraction: Termine, Beträge, Telefonnummern
✅ Sentiment Analysis: Wichtigkeit erkennen
✅ Translation: Mehrsprachige Unterstützung
```

**Erweiterte Modelle:**
```bash
# Multimodale Modelle (für Bilder in Emails)
ollama pull llava-phi3  # Vision + Text
ollama pull bakllava  # Bilderkennung

# Spezialisierte Modelle
ollama pull mistral  # Französisch
ollama pull gemma2   # Google's neuestes
```

**Value Add:**
- ⭐⭐⭐⭐⭐ Zeitersparnis beim Email-Management
- ⭐⭐⭐⭐⭐ Wichtige Infos sofort sichtbar
- ⭐⭐⭐⭐⭐ Keine relevante Info mehr verpassen

---

### **3. 📅 Kalender-Integration**

**Warum:** Termine automatisch aus Emails extrahieren!

**Tools:**
```bash
# Google Calendar CLI
brew install gcalcli

# CalDAV Client
brew install khal

# Synchronisation
brew install vdirsyncer
```

**Automatisierung:**
```python
# Aus Emails automatisch Kalender-Einträge erstellen
• 15.04.2026 um 14:30 Uhr → Kalender
• Besprechung, Termin, Flug → Event
• Telegramm, Einladung → Teilnehmer
```

**Value Add:**
- ⭐⭐⭐⭐⭐ Termine nie verpassen
- ⭐⭐⭐⭐⭐ Automatische Organisation
- ⭐⭐⭐⭐⭐ Perfekt fürBusy People

---

### **4. ✅ Task-Management Integration**

**Warum:** Wichtige Emails automatisch als Aufgaben!

**Tools:**
```bash
# Taskwarrior (CLI Task Manager)
brew install taskwarrior

# Todo.txt (einfache Todo-Listen)
brew install todo-txt

# Alternative: todotxt-touch
brew tap owentc/todotxt-touch
brew install todotxt-touch
```

**Auto-Tasks:**
```python
# Aus Emails automatisch Aufgaben erstellen
• Finanzen-Kategorie → Rechnung prüfen
• Arbeit-Kategorie → Meeting vorbereiten
• Behörden-Kategorie → Frist eintragen
```

**Value Add:**
- ⭐⭐⭐⭐⭐ Produktivitäts-Boost
- ⭐⭐⭐⭐⭐ Automatische To-do Generierung
- ⭐⭐⭐⭐⭐ Keine wichtige Email vergessen

---

### **5. 🔔 Smart Notifications**

**Warum:** Wichtige Emails sofort auf dem Schirm!

**Tools:**
```python
# macOS Notifications (built-in)
osascript -e 'display notification "Nachricht"'

# Alternative: terminal-notifier
brew install terminal-notifier

# Pushover (Mobile Notifications)
pip install pushover-complete
```

**Smart Rules:**
```python
# Benachrichtigungen nur bei wichtigen Kategorien
WICHTIGE_KATEGORIEN = [
    "arbeit",      # Meeting-Einladungen
    "finanzen",    # Kontoauszüge
    "behoerden",   # Bescheide
    "vertraege",   # Vertragsende
    "rettung"      # Einsatzalarmierung
]
```

**Value Add:**
- ⭐⭐⭐⭐⭐ Sofortige Reaktion auf Wichtiges
- ⭐⭐⭐⭐⭐ Keine verpassten Fristen
- ⭐⭐⭐⭐⭐ Stressfreier Alltag

---

## 🛠️ Installation der Erweiterungen

### **Schritt 1: Erweiterungen installieren**

```bash
cd /path/to/mail-ai-sorter

# Erweiterungen-Script erstellen
cat > extensions.py << 'EOF'
[Code von oben]
EOF

# Benötigte Python-Pakete
source venv/bin/activate
pip install requests gcalcli taskwarrior pandas matplotlib

# Tools installieren
brew install gcalcli taskwarrior terminal-notifier vdirsyncer
```

### **Schritt 2: In sort.py integrieren**

```python
# Am Ende von sort.py hinzufügen:
from extensions import (
    PaperlessNGXIntegration,
    CalendarIntegration,
    TaskIntegration,
    NotificationIntegration,
    AIAutomationExtensions
)

# Nach der Sortierung Erweiterungen ausführen
def run_extensions(email_data, action):
    """Führt Erweiterungen basierend auf Kategorie aus"""
    
    category = email_data.get("category", "")
    
    # Paperless-ngx für Dokumenten-Kategorien
    if category in ["paperless", "finanzen", "vertraege"]:
        try:
            paperless = PaperlessNGXIntegration()
            paperless.create_document_from_email(email_data)
            print(f"✅ Nach Paperless-ngx gesendet")
        except Exception as e:
            print(f"❌ Paperless-ngx Fehler: {e}")
    
    # Kalender für Termin-Kategorien
    if category in ["arbeit", "reisen", "termin"]:
        try:
            calendar = CalendarIntegration()
            appointments = calendar.extract_appointments(email_data)
            for appointment in appointments:
                calendar.create_calendar_event(appointment, email_data)
            print(f"✅ {len(appointments)} Termine erstellt")
        except Exception as e:
            print(f"❌ Kalender Fehler: {e}")
    
    # Tasks für Aufgaben-Kategorien
    if category in ["arbeit", "finanzen", "behoerden"]:
        try:
            tasks = TaskIntegration()
            tasks.create_task_from_email(email_data)
            print(f"✅ Aufgabe erstellt")
        except Exception as e:
            print(f"❌ Task-Fehler: {e}")
    
    # Benachrichtigungen für wichtige Kategorien
    try:
        notifications = NotificationIntegration()
        notifications.notify_important_email(email_data)
    except Exception as e:
        print(f"❌ Benachrichtigungs-Fehler: {e}")
```

### **Schritt 3: Konfiguration erweitern**

```json
// config.json - Erweitert
{
  "global": {
    ...,
    "extensions": {
      "paperless_enabled": true,
      "paperless_url": "http://localhost:8000",
      "paperless_api_token": "PAPERLESS_API_TOKEN",
      
      "calendar_enabled": true,
      "calendar_name": "Hauptkalender",
      
      "tasks_enabled": true,
      "task_system": "taskwarrior",
      
      "notifications_enabled": true,
      "notification_categories": ["arbeit", "finanzen", "behoerden"],
      
      "summarization_enabled": true,
      "entity_extraction_enabled": true
    }
  }
}
```

---

## 📊 Roadmap für Erweiterungen

### **Phase 1: Core Extensions (1-2 Wochen)**
- ✅ Paperless-ngx API Integration
- ✅ Kalender-Termin Extraktion
- ✅ Smart Notifications
- ✅ Auto-Tasks Generierung

### **Phase 2: AI Extensions (2-3 Wochen)**
- ✅ Email-Zusammenfassungen
- ✅ Entitäten-Extraktion (Termine, Beträge)
- ✅ Sentiment Analysis
- ✅ Multilingual Support

### **Phase 3: Analytics (1 Woche)**
- ✅ Email-Statistiken Dashboard
- ✅ Zeitverlauf-Analyse
- ✅ Absender-Netzwerk
- ✅ Export-Funktionen

### **Phase 4: Automation (2 Wochen)**
- ✅ Regel-Engine erweitern
- ✅ Workflows erstellen
- ✅ Batch-Operationen
- ✅ Backup/Automation

---

## 🎯 Nützlichste Open Source Tools

### **Dokumenten-Management**
- **Paperless-ngx** (Dokumenten Management)
- **Tesseract** (OCR Texterkennung)
- **Img2PDF** (Screenshot zu PDF)
- **Poppler** (PDF Verarbeitung)

### **Produktivität**
- **Taskwarrior** (CLI Todo-Manager)
- **Todo.txt** (Todo-Listen)
- **gcalcli** (Google Calendar CLI)
- **khal** (CalDAV Client)

### **Monitoring**
- **Glances** (System Monitoring)
- **htop** (Process Viewer)
- **netdata** (Dashboard)

### **Automation**
- **Habitica** (Gamification)
- **Gotify** (Notifications)
- **ntfy** (Push Service)

---

## 💡 Value Proposition

### **User Benefits:**
- ⏰ **Zeitersparnis**: 2-3 Stunden pro Woche
- 🎯 **Keine verpassten Termine**: 100% Zuverlässigkeit
- 📄 **Bessere Dokumenten-Organisation**: Automatisch
- ✅ **Weniger Stress**: Automatische Erinnerungen
- 📊 **Bessere Übersicht**: Analytics & Statistiken

### **Technical Benefits:**
- 🔧 **Modular**: Erweiterungen einzeln aktivierbar
- 🚀 **Performant**: Asynchrone Verarbeitung
- 🔒 **Sicher**: Alles lokal, keine Cloud
- 🌐 **Open Source**: Community kann mitbauen
- 📚 **Gut dokumentiert**: Einfach zu erweitern

---

## 🚀 Quick Start für erste Erweiterung

```bash
# 1. Paperless-ngx Installieren
brew install docker
docker run -d --name paperless-ngx \
  -p 8000:8000 \
  -v paperless_data:/usr/src/paperless/data \
  -v paperless_media:/usr/src/paperless/media \
  -v paperless_export:/usr/src/paperless/export \
  -v paperless_consume:/usr/src/paperless/consume \
  ghcr.io/paperless-ngx/paperless-ngx:latest

# 2. In sort.py integrieren
# [Code von oben]

# 3. Testlauf
python3 sorter.py --dry-run --max-per-account 5

# 4. Ergebnisse in Paperless-ngx prüfen
open http://localhost:8000
```

---

**Mit diesen Erweiterungen wird dein Mail AI Sorter zu einem COMPLETEN Produktivitäts-System!** 🚀
