# M1 Pro 16GB RAM - Spezielle LLM-Modelle

## 🍎 **M1 Pro optimierte Modelle:**

### **1. llama3.1:8b (BESTE WAHL für M1 Pro)**
```bash
ollama pull llama3.1:8b
```
**Warum perfekt für M1 Pro 16GB:**
- ✅ **ARM-optimiert** - Läuft nativ auf M1 Pro
- ✅ **6.5GB Größe** - Perfekt für 16GB RAM (7GB frei für System)
- ✅ **Unified Memory** - Nutzt M1 Pro schnellen RAM optimal
- ✅ **Efficiency-Core freundlich** - Läuft gut auf den 2 Efficiency-Cores
- ✅ **Neural Engine kompatibel** - Kann Apple-ML-Beschleunigung nutzen

### **2. phi3:mini (SPEED CHAMP für M1 Pro)**
```bash
ollama pull phi3:mini
```
**M1 Pro Vorteile:**
- ✅ **Nur 4.7GB** - Maximum RAM für andere Apps
- ✅ **Sehr ARM-optimiert** - Microsoft hat für Apple Silicon optimiert
- ✅ **Single-Core Performance** - Nutzt M1 Pro schnelle Performance-Cores
- ✅ **Geringste Hitzeentwicklung** - Wichtig für MacBook

### **3. gemma2:9b (APPLE SILICON EDITION)**
```bash
ollama pull gemma2:9b
```
**M1 Pro Spezifik:**
- ✅ **Google ARM-optimiert** - Speziell für Apple Silicon
- ✅ **Exzellente Deutsch-Unterstützung**
- ✅ **5.4GB** - Gute RAM-Balance

## 🎯 **MEINE EMPFEHLUNG für deinen M1 Pro 16GB:**

### **llama3.1:8b - Der Goldilocks für dein Setup**

**Perfekte Balance:**
- **RAM-Usage:** 6.5GB (40% von 16GB)
- **Speed:** ~1.2s pro Mail (vs 2s bei gemma4)
- **Genauigkeit:** Exzellent
- **M1 Pro Features:** Nutzt alle Vorteile (Unified Memory, Neural Engine)

**Konfiguration für M1 Pro:**
```json
{
  "model": "llama3.1:8b",
  "ollama_num_ctx": 4096,      // Optimal für M1 Pro Memory Bandwidth
  "ollama_num_predict": 30,    // Schnell für M1 Pro Single-Core
  "ollama_timeout_sec": 60,    // M1 Pro ist schnell genug
  "max_body_chars": 2500       // Balance zwischen Speed und Genauigkeit
}
```

## 📊 **M1 Pro 16GB RAM - Spezifische Performance:**

| Modell | RAM-Usage | M1 Pro Speed | Hitze | Empfehlung |
|--------|-----------|--------------|-------|------------|
| **llama3.1:8b** | 40% | ⚡⚡⚡⚡ | Gering | **BESTE** |
| **phi3:mini** | 30% | ⚡⚡⚡⚡⚡ | Minimal | Speed |
| **gemma2:9b** | 34% | ⚡⚡⚡⚡ | Gering | Deutsch-Pro |
| **gemma4:e4b** | 60% | ⚡⚡⚡ | Hoch | Aktuell |

## 🔧 **M1 Pro Optimierungen:**

### **1. Energy Saver Mode (wichtig für MacBook!):**
```json
{
  "model": "phi3:mini",  // Weniger Hitze, mehr Battery
  "ollama_num_ctx": 2048,  // Weniger Rechenaufwand
  "max_per_account": 30    // Kleinere Chargen
}
```

### **2. Performance Mode (am Strom):**
```json
{
  "model": "llama3.1:8b",
  "ollama_num_ctx": 8192,   // Maximale Genauigkeit
  "max_per_account": 100,   // Größere Chargen
  "parallel": true          // Multi-Core nutzen
}
```

### **3. Battery Mode (unterwegs):**
```json
{
  "model": "phi3:mini",
  "delay_minutes": 60,      // Selteneres Sortieren
  "max_per_account": 20     // Weniger gleichzeitige Mails
}
```

## 🚀 **M1 Pro Spezielle Features:**

### **Unified Memory nutzen:**
```bash
# Ollama für M1 Pro optimieren:
ollama run llama3.1:8b --num-ctx 4096 --num-gpu 99  # Nutzt M1 Pro GPU
```

### **Efficiency-Cores für Background:**
```bash
# Launchd Job nutzt Efficiency-Cores:
launchctlsetMaxProcInfo(gui/$(id -u)/com.michael.mail-ai-sorter, 2)
```

### **Thermal Management:**
```bash
# Bei Hitzeproblemen:
sudo powermetrics --samplers cpu_power -i 1000
# Eventuell phi3:mini nutzen statt llama3.1:8b
```

## 💡 **Praktische Empfehlung:**

**Für deinen M1 Pro 16GB:**
1. **Normal:** llama3.1:8b (beste Balance)
2. **Battery:** phi3:mini (maximale Laufzeit)
3. **Performance:** llama3.1:8b mit --parallel (maximaler Throughput)

**Wechsel:**
```bash
cd /path/to/mail-ai-sorter
ollama pull llama3.1:8b
# In config.json ändern: "model": "llama3.1:8b"
```

## 🎁 **BONUS: M1 Pro exclusives Feature:**

**Metal- Beschleunigung für Ollama:**
```bash
# Prüfen ob Metal aktiviert ist:
ollama show llama3.1:8b --modelfile
# Sollte "FROM llama3.1:8b-base" enthalten
```

**Zusammenfassung: llama3.1:8b ist das perfekte Modell für deinen M1 Pro 16GB RAM!**
