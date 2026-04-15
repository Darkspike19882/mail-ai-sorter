# 🤝 Contributing to Mail AI Sorter

Vielen Dank für dein Interesse an Mail AI Sorter! Wir freuen uns über jeden Beitrag.

## 🚀 Wie du helfen kannst

### 🐛 Bugs melden

**Bevor du ein Bug meldest:**
1. Suche nach [existing issues](https://github.com/Darkspike19882/mail-ai-sorter/issues)
2. Checke ob es schon eine Lösung gibt
3. Nutze die Bug-Report Template

**Gute Bug-Reports enthalten:**
- ✅ Deine macOS Version
- ✅ Python Version (`python3 --version`)
- ✅ Ollama Version (`ollama --version`)
- ✅ Genauer Fehlerbeschreibung
- ✅ Steps to reproduce
- ✅ Logs (ohne persönliche Daten!)

### 💡 Feature Requests

**Gute Feature-Requests:**
- ✅ Beschreibe das Problem, nicht die Lösung
- ✅ Warum ist das Feature wichtig?
- ✅ Use Cases und Beispiele
- ✅ Wie würdest du es implementieren?

### 📖 Dokumentation verbessern

**Wo wir Hilfe brauchen:**
- [ ] INSTALL.md verbessern
- [ ] Mehr Screenshots hinzufügen
- [ ] Video-Tutorials
- [ ] Übersetzungen (Englisch, Französisch, etc.)
- [ ] FAQ erweitern

### 🔧 Code beitragen

**Setup für Development:**
```bash
# Fork das Repository
git clone https://github.com/YOUR_USERNAME/mail-ai-sorter.git
cd mail-ai-sorter

# Virtuelle Environment erstellen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Deine Feature Branch erstellen
git checkout -b feature/dein-feature-name

# Änderungen machen und testen
python3 sorter.py --dry-run --max-per-account 5
python3 web_ui.py

# Commit und Push
git add .
git commit -m "feat: deine feature beschreibung"
git push origin feature/dein-feature-name

# Pull Request erstellen
```

**Code Style:**
- Python: PEP 8
- HTML/JS: Modern ES6+
- Kommentare: Deutsch oder Englisch
- Docstrings: Englisch

**Pull Request Guidelines:**
- ✅ Beschreibe was dein PR macht
- ✅ Screenshots für UI-Änderungen
- ✅ Tests für neue Features
- ✅ Docs aktualisieren
- ✅ Keine persönlichen Daten!

## 📋 Development Priorities

### High Priority
- [ ] Regeln-Editor in Web UI
- [ ] Undo-Funktion
- [ ] Preview-Mode
- [ ] Mehr Tests

### Medium Priority
- [ ] Performance Optimierungen
- [ ] Bessere Error Messages
- [ ] More Rule Templates
- [ ] Multi-Sprachen

### Low Priority
- [ ] Docker Support
- [ ] Mobile App
- [ ] Cloud Deployment

## 🧪 Testing

**Bevor du einen PR erstellst:**
```bash
# Dry-run Test
python3 sorter.py --dry-run --max-per-account 10

# Web UI Test
python3 web_ui.py
# Öffne http://localhost:5001

# Ollama Test
curl http://localhost:11434/api/tags
```

## 📄 License

Durch das Beitragen stimmst du zu, dass deine Beiträge unter der **MIT License** veröffentlicht werden.

## 💬 Kommunikation

- 📧 **Issues**: Für Bugs und Features
- 💬 **Discussions**: Für Fragen und Ideen
- 🔔 **Releases**: Release Notes subscriben

## 🙏 Danksagung

Besonderer Dank an:
- **[Ollama](https://ollama.ai/)** - Lokale KI-Infrastruktur
- **[Meta](https://llama.meta.com/)** - llama3.1:8b Modell
- **[Flask](https://flask.palletsprojects.com/)** - Web Framework
- Alle Contributors!

---

**Made with ❤️ by the Open Source Community**
