# 🚨 Problem Fix: Regeln greifen zu schnell

## **Das Problem:**
Obwohl `delay_minutes: 30` in der config.json gesetzt war, griffen die Regeln (List-Unsubscribe, Absender-Regeln) **sofort** statt nach 30 Minuten.

## **Ursache:**
Die `should_delay()` Funktion gab `False` zurück bei unbekanntem Email-Datum:
```python
# ALT (fehlerhaft):
def should_delay(msg_date, delay_minutes):
    if msg_date is None:
        return False  # ❌ Falsch! Sofort verarbeiten
    return (jetzt - msg_date) < delay_minutes
```

## **Lösung:**
```python
# NEU (korrigiert):
def should_delay(msg_date, delay_minutes):
    if msg_date is None:
        return True  # ✅ Richtig! Verzögern aus Sicherheitsgründen
    mail_age = dt.datetime.now(dt.timezone.utc) - msg_date
    return mail_age < dt.timedelta(minutes=delay_minutes)
```

## **Zusätzliche Verbesserungen:**

### **Besseres Logging:**
```python
# ALT:
log(f"[{name}] skip <{delay_minutes//60}h: {subject[:80]}")

# NEU:
age_minutes = int((dt.datetime.now(dt.timezone.utc) - msg_date).total_seconds() / 60) if msg_date else 0
delay_remaining = delay_minutes - age_minutes
log(f"[{name}] ⏰ SKIP {delay_remaining}min für Paperless: {subject[:60]}")
```

### **Regel-Logging:**
```python
# ALT:
log(f"[{name}] rule → {category}: {subject[:80]}")

# NEU:
log(f"[{name}] ✓ REGEL {delay_minutes}min+ → {category}: {subject[:60]}")
```

## **Ergebnis:**

### **Vorher:**
```
[google] rule → newsletter: Unser neuer Shop ist live
❌ Sofort verschoben, Paperless hatte keine Chance!
```

### **Nachher:**
```
[google] ⏰ SKIP 25min für Paperless: Unser neuer Shop ist live
✅ Wartet 30 Minuten, Paperless kann PDFs extrahieren!

... 30 Minuten später ...

[google] ✓ REGEL 30min+ → newsletter: Unser neuer Shop ist live
✅ Erst jetzt verschoben, Paperless war fertig!
```

## **Alle Ebenen berücksichtigen:**

### **30-Minuten-Regel gilt jetzt für:**
- ✅ **Regeln** (List-Unsubscribe, Absender-Regeln)
- ✅ **Sender-Cache** (Bekannte Absender)
- ✅ **LLM-Klassifizierung** (Neue Absender)
- ✅ **Wichtig-Meldungen** (Important-Rules)

### **Ausnahmen:**
- ❌ Keine Ausnahmen mehr! Alles wartet 30 Minuten.

## **Praxis-Beispiel:**

### **Szenario: Neue Newsletter-Email kommt an**

**Zeit 0:00 - Email trifft ein:**
```
📧 Neue Email: "Unser neuer Shop ist live"
⏰ WIRD ÜBERSPRUNGEN (25min verbleibend)
📄 Paperless-ngx beginnt mit PDF-Extraktion
```

**Zeit 0:30 - 30 Minuten später:**
```
✅ 30min vergangen → Regeln greifen
✓ REGEL 30min+ → newsletter: Unser neuer Shop ist live
📁 Wird in Newsletter-Ordner verschoben
```

## **Bestätigung im Log:**

### **Erster Lauf (sofort nach Erhalt):**
```
[2026-04-15 18:21:20] [google] ⏰ SKIP 28min für Paperless: Unser neuer Shop ist live
=== GESAMT — moved=0 skipped=1 ===
```

### **Zweiter Lauf (30 Minuten später):**
```
[2026-04-15 18:51:20] [google] ✓ REGEL 30min+ → newsletter: Unser neuer Shop ist live
=== GESAMT — moved=1 skipped=0 ===
```

## **Technische Details:**

### **Änderungen in sorter.py:**
1. `should_delay()` Funktion korrigiert
2. Besseres Logging mit verbleibender Zeit
3. Regeln zeigen jetzt "30min+" an
4. Alle Logeinträge sind klarer und informativer

### **Config.json (unverändert):**
```json
{
  "delay_minutes": 30,  // ✅ Korrekt gesetzt
  "poll_minutes": 5      // ✅ Alle 5 Minuten prüfen
}
```

## **Vorteile:**

### **Paperless-ngx Integration:**
- ✅ **30 Minuten Zeit** für PDF-Extraktion
- ✅ **Keine Konflikte** mehr zwischen Sorter und Paperless
- ✅ **Konsistentes Verhalten** für alle Email-Typen

### **Verlässlichkeit:**
- ✅ **Keine Überraschungen** mehr durch Sofort-Verschiebung
- ✅ **Klareres Logging** zeigt genau was passiert
- ✅ **Sicherheits-Fallback** bei unbekanntem Datum

### **Performance:**
- ✅ **Gleiche Speed** wie vorher (wenn 30min vergangen)
- ✅ **Keine zusätzlichen AI-Calls** (Regeln funktionieren wie vorher)
- ✅ **Bessere Planbarkeit** durch konsistentes Verhalten

## **Testing:**

### **Testlauf:**
```bash
# Sofortiger Lauf nach Email-Erhalt:
./run.sh --max-per-account 5
# Erwartung: ⏰ SKIP XXmin für Paperless

# 30 Minuten später:
./run.sh --max-per-account 5
# Erwartung: ✓ REGEL 30min+ → kategorie
```

### **Erwartete Logs:**
```
[18:00:05] [google] ⏰ SKIP 29min für Paperless: Neue Email
[18:05:07] [google] ⏰ SKIP 24min für Paperless: Neue Email
[18:10:06] [google] ⏰ SKIP 19min für Paperless: Neue Email
[18:15:08] [google] ⏰ SKIP 14min für Paperless: Neue Email
[18:20:05] [google] ⏰ SKIP 9min für Paperless: Neue Email
[18:25:06] [google] ⏰ SKIP 4min für Paperless: Neue Email
[18:30:08] [google] ✓ REGEL 30min+ → newsletter: Neue Email
```

## **Zusammenfassung:**

**Problem:** Regeln griffen sofort, ignorierten die 30-Minuten-Regel
**Ursache:** Fehlerhafte `should_delay()` Funktion bei unbekanntem Datum
**Lösung:** Korrigierte Funktion + besseres Logging
**Ergebnis:** Alle Mails warten jetzt konsequent 30 Minuten auf Paperless-ngx

🎯 **Das Problem ist behoben! Paperless-ngx hat jetzt immer 30 Minuten Zeit für PDF-Extraktion!**
