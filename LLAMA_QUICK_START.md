#!/bin/bash
# llama3.1:8b Quick Start Script - Die besten Anwendungen

echo "🚀 llama3.1:8b - Quick Start Anwendungen"
echo "=========================================="
echo ""

# Prüfen ob Ollama läuft
if ! pgrep -q ollama; then
    echo "⚠️  Ollama läuft nicht - wird gestartet..."
    /Applications/Ollama.app/Contents/Resources/ollama serve > /dev/null 2>&1 &
    sleep 3
fi

echo "Wähle eine Kategorie:"
echo "1. 📝 Texterstellung & Korrektur"
echo "2. 💻 Programmierung & Code-Hilfe"
echo "3. 🌍 Übersetzung"
echo "4. 📚 Zusammenfassung & Analyse"
echo "5. 🎓 Lernen & Erklärung"
echo "6. 💡 Alltagshilfen & Entscheide"
echo "7. 🍳 Rezepte & Haushalt"
echo "8. 🎮 Kreativität & Spiele"
echo "9. 💼 Geschäft & Karriere"
echo "10. 🛠️  Terminal & Automatisierung"
echo "0. 🎲 Zufällige Demo"
echo ""
read -p "Deine Wahl (0-10): " choice

case $choice in
  1)
    echo "📝 Texterstellung & Korrektur"
    echo "Optionen:"
    echo "a) E-Mail schreiben"
    echo "b) Text korrigieren"
    echo "c) Blog-Artikel erstellen"
    read -p "Wähle (a-c): " text_choice
    read -p "Dein Text/Prompt: " prompt
    case $text_choice in
      a) ollama run llama3.1:8b "Schreibe eine professionelle E-Mail: $prompt" ;;
      b) ollama run llama3.1:8b "Korrigiere diesen Text grammatikalisch und stilistisch: $prompt" ;;
      c) ollama run llama3.1:8b "Schreibe einen interessanten Blog-Artikel über: $prompt" ;;
    esac
    ;;
  2)
    echo "💻 Programmierung & Code-Hilfe"
    echo "Optionen:"
    echo "a) Code erklären"
    echo "b) Code schreiben"
    echo "c) Bug finden"
    read -p "Dein Code/Prompt: " prompt
    read -p "Sprache (python/bash/javascript): " lang
    case $lang in
      python) ollama run llama3.1:8b "Python-Code Hilfe: $prompt" ;;
      bash) ollama run llama3.1:8b "Bash-Script Hilfe: $prompt" ;;
      *) ollama run llama3.1:8b "Code-Hilfe ($lang): $prompt" ;;
    esac
    ;;
  3)
    echo "🌍 Übersetzung"
    read -p "Text zum Übersetzen: " text
    echo "Zielsprache (en/de/fr/es): " lang
    ollama run llama3.1:8b "Übersetze folgenden Text ins $lang: $text"
    ;;
  4)
    echo "📚 Zusammenfassung & Analyse"
    echo "Optionen:"
    echo "a) Text zusammenfassen"
    echo "b) Schlüssel Punkte extrahieren"
    echo "c) Stimmung analysieren"
    read -p "Dein Text: " text
    ollama run llama3.1:8b "Analysiere diesen Text: $text"
    ;;
  5)
    echo "🎓 Lernen & Erklärung"
    read -p "Was möchtest du lernen? " topic
    ollama run llama3.1:8b "Erkläre $topic so, dass es ein Anfänger verstehen kann"
    ;;
  6)
    echo "💡 Alltagshilfen & Entscheidungen"
    read -p "Situation: " situation
    ollama run llama3.1:8b "Hilf mir bei folgender Entscheidung: $ituation. Erstelle Pro- und Contra-Liste."
    ;;
  7)
    echo "🍳 Rezepte & Haushalt"
    read -p "Was hast du im Kühlschrank? " ingredients
    ollama run llama3.1:8b "Erstelle ein einfaches Rezept mit folgenden Zutaten: $ingredients"
    ;;
  8)
    echo "🎮 Kreativität & Spiele"
    echo "Optionen:"
    echo "a) Geschichte schreiben"
    echo "b) Gedicht verfassen"
    echo "c) Rätsel erstellen"
    read -p "Thema: " topic
    ollama run llama3.1:8b "Sei kreativ zum Thema: $topic"
    ;;
  9)
    echo "💼 Geschäft & Karriere"
    read -p "Deine Anfrage: " business_query
    ollama run llama3.1:8b "Karriere-Beratung: $business_query"
    ;;
  10)
    echo "🛠️  Terminal & Automatisierung"
    read -p "Was möchtest du automatisieren? " task
    ollama run llama3.1:8b "Schreibe ein Bash-Script für: $task"
    ;;
  0)
    echo "🎲 Zufällige Demo"
    demos=(
      "Schreibe ein kurzes Gedicht über KI"
      "Erkläre Quantenphysik einfach"
      "Erstelle ein 3-Tage-Reiseprogramm für Tokyo"
      "Schreibe ein Rezept für Schokoladenkuchen"
      "Erkläre den Unterschied zwischen Git und GitHub"
    )
    random_demo=${demos[$RANDOM % ${#demos[@]}]}
    echo "Demo: $random_demo"
    ollama run llama3.1:8b "$random_demo"
    ;;
  *)
    echo "Ungültige Wahl"
    exit 1
    ;;
esac

echo ""
echo "✅ Done! Mehr Infos mit: ollama run llama3.1:8b"
