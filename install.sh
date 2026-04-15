#!/bin/bash
# Mail AI Sorter - macOS Installations-Script
# Führt alle Schritte automatisch aus

set -e  # Bei Fehlern stoppen

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  🤖 Mail AI Sorter - macOS Installer                   ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}➤ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Prüfe ob Apple Silicon
check_apple_silicon() {
    print_step "Prüfe Hardware..."

    if [[ $(uname -m) == 'arm64' ]]; then
        print_success "Apple Silicon erkannt"
        return 0
    else
        print_warning "Kein Apple Silicon erkannt"
        read -p "Trotzdem fortfahren? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Installation abgebrochen"
            exit 1
        fi
    fi
}

# Prüfe macOS Version
check_macos_version() {
    print_step "Prüfe macOS Version..."

    local version=$(sw_vers -productVersion)
    local major=$(echo $version | cut -d. -f1)

    if [[ $major -ge 12 ]]; then
        print_success "macOS $version (OK)"
    else
        print_error "macOS $version ist zu alt (Minimum: macOS 12 Monterey)"
        exit 1
    fi
}

# Prüfe und installiere Homebrew
check_homebrew() {
    print_step "Prüfe Homebrew..."

    if command -v brew &> /dev/null; then
        local version=$(brew --version | head -n1)
        print_success "Homebrew installiert: $version"
    else
        print_warning "Homebrew nicht gefunden - werde installieren..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Homebrew PATH setzen
        if [[ $(uname -m) == 'arm64' ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        print_success "Homebrew installiert"
    fi
}

# Prüfe und installiere Python
check_python() {
    print_step "Prüfe Python..."

    if command -v python3 &> /dev/null; then
        local version=$(python3 --version)
        print_success "Python installiert: $version"
    else
        print_warning "Python nicht gefunden - werde installieren..."
        brew install python@3.14
        print_success "Python installiert"
    fi
}

# Prüfe und installiere Ollama
check_ollama() {
    print_step "Prüfe Ollama..."

    if command -v ollama &> /dev/null; then
        local version=$(ollama --version)
        print_success "Ollama installiert: $version"
    else
        print_warning "Ollama nicht gefunden - werde installieren..."
        brew install ollama
        print_success "Ollama installiert"
    fi

    # Prüfe ob Ollama läuft
    if ! curl -s http://localhost:11434 > /dev/null; then
        print_info "Starte Ollama..."
        ollama serve &
        sleep 5
        print_success "Ollama gestartet"
    fi
}

# Prüfe llama3.1:8b Modell
check_model() {
    print_step "Prüfe llama3.1:8b Modell..."

    if ollama list | grep -q "llama3.1:8b"; then
        print_success "llama3.1:8b installiert"
    else
        print_warning "llama3.1:8b nicht gefunden - werde herunterladen (~4.7GB)..."
        print_info "Dies kann einige Minuten dauern..."

        if ollama pull llama3.1:8b; then
            print_success "llama3.1:8b heruntergeladen"
        else
            print_error "Download fehlgeschlagen"
            print_info "Bitte manuell installieren: ollama pull llama3.1:8b"
            exit 1
        fi
    fi
}

# Installiere Python Abhängigkeiten
install_python_deps() {
    print_step "Installiere Python Abhängigkeiten..."

    # Virtuelle Umgebung erstellen
    if [[ ! -d "venv" ]]; then
        print_info "Erstelle virtuelle Umgebung..."
        python3 -m venv venv
        print_success "Virtuelle Umgebung erstellt"
    else
        print_success "Virtuelle Umgebung vorhanden"
    fi

    # Aktivieren
    source venv/bin/activate

    # Installiere requirements
    if pip install -r requirements.txt; then
        print_success "Python Abhängigkeiten installiert"
    else
        print_error "Installation fehlgeschlagen"
        exit 1
    fi
}

# Erstelle Konfiguration
create_config() {
    print_step "Erstelle Konfiguration..."

    if [[ -f "config.json" ]]; then
        print_warning "config.json existiert bereits - überspringe..."
        return 0
    fi

    if [[ -f "config.example.json" ]]; then
        cp config.example.json config.json
        print_success "config.json erstellt"
        print_info "Bitte mit: nano config.json bearbeiten"
    else
        print_warning "config.example.json nicht gefunden"
    fi
}

# Erstelle secrets.env
create_secrets() {
    print_step "Erstelle secrets.env..."

    if [[ -f "secrets.env" ]]; then
        print_warning "secrets.env existiert bereits - überspringe..."
        return 0
    fi

    if [[ -f "secrets.example.env" ]]; then
        cp secrets.example.env secrets.env
        print_success "secrets.env erstellt"
        print_info "Bitte mit: nano secrets.env bearbeiten"
        print_warning "⚠️ WICHTIG: Passwörter eintragen!"
    else
        print_warning "secrets.example.env nicht gefunden"
    fi
}

# Haupt-Installation
main() {
    clear
    print_header

    echo -e "${BLUE}Willkommen beim Mail AI Sorter Installer!${NC}"
    echo ""
    echo "Dieser Installer wird:"
    echo "  ✓ Homebrew installieren (falls fehlt)"
    echo "  ✓ Python installieren (falls fehlt)"
    echo "  ✓ Ollama installieren (falls fehlt)"
    echo "  ✓ llama3.1:8b herunterladen (~4.7GB)"
    echo "  ✓ Python Abhängigkeiten installieren"
    echo "  ✓ Konfigurationsdateien erstellen"
    echo ""
    read -p "Fortfahren? (Y/n) " -n 1 -r
    echo
    echo ""

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_error "Installation abgebrochen"
        exit 1
    fi

    # Prüfungen
    check_apple_silicon
    check_macos_version
    check_homebrew
    check_python
    check_ollama
    check_model
    install_python_deps
    create_config
    create_secrets

    # Zusammenfassung
    echo ""
    print_header
    echo -e "${GREEN}✓ Installation abgeschlossen!${NC}"
    echo ""
    echo "Nächste Schritte:"
    echo ""
    echo "1. Konfiguration bearbeiten:"
    echo "   ${BLUE}nano config.json${NC}"
    echo ""
    echo "2. Passwörter eintragen:"
    echo "   ${BLUE}nano secrets.env${NC}"
    echo ""
    echo "3. Setup Wizard starten:"
    echo "   ${BLUE}source venv/bin/activate${NC}"
    echo "   ${BLUE}python3 web_ui.py${NC}"
    echo ""
    echo "4. Browser öffnen:"
    echo "   ${BLUE}http://localhost:5001/setup${NC}"
    echo ""
    echo "5. Oder Testlauf im Terminal:"
    echo "   ${BLUE}./run.sh --dry-run --max-per-account 10${NC}"
    echo ""
    echo -e "${YELLOW}⚠ WICHTIG:${NC} Bevor du Emails sortierst:"
    echo "   - 1 Testlauf mit --dry-run machen"
    echo "   - Ergebnisse prüfen"
    echo "   - Dann erst echte Sortierung"
    echo ""
    echo -e "${GREEN}Viel Spaß! 📧✨${NC}"
}

# Ausführen
main "$@"
