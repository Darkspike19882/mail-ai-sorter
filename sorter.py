#!/usr/bin/env python3
"""
AI IMAP Mail Sorter — Gemma4 via Ollama
Features: 15 categories, sender cache, batch header fetch, global rules, parallel accounts
"""
import argparse
import concurrent.futures
import datetime as dt
import email
import email.generator
import email.utils
import imaplib
import io
import json
import os
import re
import ssl
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Optional index module (same directory)
try:
    import importlib.util, pathlib
    _spec = importlib.util.spec_from_file_location(
        "index", pathlib.Path(__file__).parent / "index.py"
    )
    _idx_mod = importlib.util.module_from_spec(_spec)  # type: ignore
    _spec.loader.exec_module(_idx_mod)  # type: ignore
    _index_email = _idx_mod.index_email
    _get_db      = _idx_mod.get_db
    _DB_PATH     = _idx_mod.DB_PATH
    HAS_INDEX = True
except Exception:
    HAS_INDEX = False

# Optional extensions module (same directory)
try:
    import importlib.util, pathlib
    _spec_ext = importlib.util.spec_from_file_location(
        "extensions", pathlib.Path(__file__).parent / "extensions.py"
    )
    _ext_mod = importlib.util.module_from_spec(_spec_ext)  # type: ignore
    _spec_ext.loader.exec_module(_ext_mod)  # type: ignore
    HAS_EXTENSIONS = True
except Exception:
    HAS_EXTENSIONS = False


# ── Config & Cache ─────────────────────────────────────────────────────────────

def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sender_cache(cache_path: str) -> Dict[str, str]:
    """Load learned sender→category mappings from disk."""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_sender_cache(cache_path: str, cache: Dict[str, str], lock: threading.Lock) -> None:
    """Atomically save sender cache (thread-safe)."""
    tmp = cache_path + ".tmp"
    with lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, cache_path)


def extract_email_addr(from_str: str) -> str:
    """Extract clean lowercase email address from 'Name <addr>' format."""
    m = re.search(r"<([^>]+)>", from_str)
    if m:
        return m.group(1).lower().strip()
    return from_str.lower().strip()


# ── Email parsing ───────────────────────────────────────────────────────────────

def decode_header_value(value: Any) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(chunk))
    return "".join(out)


def extract_text(msg: email.message.Message, max_chars: int) -> str:
    texts: List[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                texts.append(payload.decode(charset, errors="replace"))
            elif ctype == "text/html" and not texts:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                html = payload.decode(charset, errors="replace")
                html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
                html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
                html = re.sub(r"<[^>]+>", " ", html)
                html = re.sub(r"\s+", " ", html).strip()
                texts.append(html)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
                text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
            texts.append(text)
    return "\n".join(texts)[:max_chars]


def parse_date(date_header: str) -> Optional[dt.datetime]:
    try:
        parsed = email.utils.parsedate_to_datetime(date_header)
    except Exception:
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def should_delay(msg_date: Optional[dt.datetime], delay_minutes: int) -> bool:
    """
    Bestimmt ob eine Mail noch zu jung ist für die Verarbeitung.
    Gibt True zurück wenn die Mail NOCH nicht bearbeitet werden soll.
    """
    if msg_date is None:
        # Bei unbekanntem Datum: sicherheitshalber verzögern (Paperless Zeit geben!)
        return True
    mail_age = dt.datetime.now(dt.timezone.utc) - msg_date
    return mail_age < dt.timedelta(minutes=delay_minutes)


# ── Extensions ────────────────────────────────────────────────────────────────────

def run_extensions(category: str, from_addr: str, subject: str, body: str,
                   extensions_cfg: Dict[str, Any], global_cfg: Dict[str, Any]) -> None:
    """Führt Erweiterungen basierend auf Kategorie aus"""
    if not HAS_EXTENSIONS or not extensions_cfg.get("enabled", False):
        return

    email_data = {
        "category": category,
        "from_addr": from_addr,
        "subject": subject,
        "body": body,
    }

    # Paperless-ngx für Dokumenten-Kategorien
    if extensions_cfg.get("paperless_enabled", False):
        if category in ["paperless", "finanzen", "vertraege", "einkauf"]:
            try:
                paperless = _ext_mod.PaperlessNGXIntegration(
                    paperless_url=extensions_cfg.get("paperless_url", "http://localhost:8000"),
                    api_token=extensions_cfg.get("paperless_api_token")
                )
                paperless.create_document_from_email(email_data)
                log(f"✅ Nach Paperless-ngx gesendet")
            except Exception as e:
                log(f"❌ Paperless-ngx Fehler: {e}")

    # Kalender für Termin-Kategorien
    if extensions_cfg.get("calendar_enabled", False):
        if category in ["arbeit", "reisen", "termin"]:
            try:
                calendar = _ext_mod.CalendarIntegration()
                appointments = calendar.extract_appointments(email_data)
                for appointment in appointments:
                    calendar.create_calendar_event(appointment, email_data)
                if appointments:
                    log(f"✅ {len(appointments)} Termine erstellt")
            except Exception as e:
                log(f"❌ Kalender Fehler: {e}")

    # Tasks für Aufgaben-Kategorien
    if extensions_cfg.get("tasks_enabled", False):
        if category in ["arbeit", "finanzen", "behoerden", "vertraege"]:
            try:
                tasks = _ext_mod.TaskIntegration(
                    task_system=extensions_cfg.get("task_system", "taskwarrior")
                )
                tasks.create_task_from_email(email_data)
                log(f"✅ Aufgabe erstellt")
            except Exception as e:
                log(f"❌ Task-Fehler: {e}")

    # Benachrichtigungen für wichtige Kategorien
    if extensions_cfg.get("notifications_enabled", False):
        important_categories = extensions_cfg.get("notification_categories", [])
        if category in important_categories:
            try:
                notifications = _ext_mod.NotificationIntegration()
                notifications.notify_important_email(email_data)
            except Exception as e:
                log(f"❌ Benachrichtigungs-Fehler: {e}")


# ── Rules ───────────────────────────────────────────────────────────────────────

def first_match_rule(rules: List[Dict[str, Any]], from_addr: str, subject: str) -> Optional[str]:
    f = from_addr.lower()
    s = subject.lower()
    for r in rules:
        from_ok = not r.get("if_from_contains") or any(
            x.lower() in f for x in r["if_from_contains"]
        )
        subj_ok = not r.get("if_subject_contains") or any(
            x.lower() in s for x in r["if_subject_contains"]
        )
        if from_ok and subj_ok:
            return r.get("move_to")
    return None


def is_important_message(rules: List[Dict[str, Any]], from_addr: str, subject: str) -> bool:
    return any(
        (not r.get("if_from_contains") or any(x.lower() in from_addr.lower() for x in r["if_from_contains"]))
        and
        (not r.get("if_subject_contains") or any(x.lower() in subject.lower() for x in r["if_subject_contains"]))
        for r in rules
    )


# ── Ollama / Gemma4 ─────────────────────────────────────────────────────────────

_CATEGORY_DEFS = {
    "paperless":  "Rechnung/Beleg/Steuer/offizielles Dokument/Zahlungsnachweis",
    "apple":      "Apple/iCloud/Apple-ID/App Store",
    "finanzen":   "Bank/PayPal/Kreditkarte/Krypto/Lease-a-Bike",
    "vertraege":  "Abo/Mobilfunk/Strom/Internet/Versicherung/Mitgliedschaft",
    "einkauf":    "Online-Bestellung/Paket/DHL/Amazon/Shop",
    "reisen":     "Flug/Bahn/Hotel/Mietwagen/Booking/Opodo",
    "rettung":    "Rettungsdienst/Sanitätsdienst/Rettinar/EMS-Fortbildung/DRK/Johanniter",
    "arbeit":     "Job/Büro/FernUni/berufliche Kommunikation/WDR/Projekt",
    "politik":    "Partei/Grüne/OV/KV/LAG/Kreisverband/politische Einladung",
    "behoerden":  "Amt/Gemeinde/Finanzamt/staatliche Behörde/Geburtsurkunde",
    "wohnen":     "WEG/Eigentümerversammlung/Hausverwaltung/Immobilien/Notar",
    "tech":       "Server/GitHub/Nextcloud/IT-Alert/Monitoring/Deployment",
    "community":  "Verein/jüdische Community/Synagoge/kulturelle Events/Gottesdienst",
    "newsletter": "Marketing/Werbung/Massen-Newsletter/Updates/Promotions",
    "privat":     "persönlicher Rest/Freunde/Familie/Sonstiges",
}


# ── Model-Specific Prompts (HARDCODED & OPTIMIZED) ────────────────────────────────
# Basierend auf Best Practices für Prompt Engineering mit deutschen LLMs
# Diese Prompts sind optimiert durch umfangreiche Tests mit echten Emails

_MODEL_PROMPTS = {
    "llama3.1:8b": {
        # llama3.1:8b Best Practices:
        # - Strukturierte Prompts mit klaren Abschnitten
        # - System-Prompts sind sehr wichtig für Verhalten
        # - JSON-Format muss explizit gefordert werden
        # - Temperatur 0.1 für maximale Präzision
        # - repeat_penalty 1.1 verhindert Wiederholungen
        # - Top-P 0.9 für gute Balance zwischen Kreativität und Präzision
        "system": "Du bist ein präziser deutscher Email-Klassifizierer. Analysiere Emails basierend auf Absender, Betreff und Inhalt. Antworte nur im angeforderten JSON-Format.",
        "user": """Du bist ein Email-Klassifizierungs-Experte. Analysiere diese Email und wähle die PASSENDE Kategorie.

KATEGORIEN:
{category_list}

EMAIL ANALYSE:
Absender: {sender}
Betreff: {subject}
Inhalt: {body}

AUFGABE:
1. Wähle die EINE beste Kategorie basierend auf Absender, Betreff und Inhalt
2. Extrahiere 3-5 relevante Suchbegriffe (Substantive, wichtige Details)

Antworte exakt im JSON-Format: {{"category": "KATEGORIE", "keywords": ["begriff1","begriff2","begriff3"]}}""",
        "temperature": 0.1,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "num_predict": 60,
        "num_ctx": 4096,
    },

    "gemma4:e4b": {
        # gemma4:e4b Best Practices:
        # - Ausführliche Kontext-Beschreibungen führen zu besseren Ergebnissen
        # - Deutsche Sprache wird sehr gut verstanden
        # - Benötigt mehr Führung als llama3.1
        # - Temperatur 0.2 für etwas mehr Flexibilität
        # - Größeres Kontext-Fenster (8192) gut nutzen
        # - Höherer num_predict (80) für ausführlichere Antworten
        "system": "Du bist ein erfahrener deutscher Email-Analyser. Deine Aufgabe ist es, Emails in Kategorien einzuteilen. Konzentriere dich auf den Inhalt und den Absender.",
        "user": """Bitte analysiere diese Email und kategorisiere sie:

Verfügbare Kategorien:
{category_list}

Email-Details:
- Von: {sender}
- Betreff: {subject}
- Inhalt: {body}

Deine Aufgabe:
1. Bestimme die passendste Kategorie anhand von Absender und Inhalt
2. Nenne 3-5 wichtige Schlagwörter aus der Email

Gib das Ergebnis im JSON-Format zurück: {{"category": "KATEGORIE", "keywords": ["wort1","wort2","wort3"]}}""",
        "temperature": 0.2,
        "top_p": 0.85,
        "repeat_penalty": 1.0,
        "num_predict": 80,
        "num_ctx": 8192,
    },

    "phi3:mini": {
        # phi3:mini Best Practices:
        # - Sehr kurze, prägnante Promots
        # - Einfache, direkte Sprache
        # - Fokus auf Kerninformation
        # - Temperatur 0.0 für maximale Präzision
        # - Niedriger num_predict (40) für Effizienz
        # - repeat_penalty 1.15 um Wiederholungen zu vermeiden
        "system": "Email-Klassifizierer. Kategorisiere Emails korrekt.",
        "user": """Kategorisiere diese Email:

Kategorien: {category_list_simple}

Von: {sender}
Betreff: {subject}
Text: {body}

Wähle die beste Kategorie und nenne 3-5 Schlagwörter.
JSON: {{"category": "KATEGORIE", "keywords": ["wort1","wort2"]}}""",
        "temperature": 0.0,
        "top_p": 1.0,
        "repeat_penalty": 1.15,
        "num_predict": 40,
        "num_ctx": 4096,
    },

    "mistral": {
        # mistral Best Practices:
        # - Français system prompt für besseres Verständnis
        # - Strukturierte Aufgabenbeschreibung
        # - Temperatur 0.15 für Balance
        # - Großes Kontext-Fenster
        "system": "Tu es un classificateur d'emails allemand très précis. Analyse les emails et catégorise-les.",
        "user": """Analyse cet email et choisit la bonne catégorie:

CATÉGORIES:
{category_list}

EMAIL:
De: {sender}
Sujet: {subject}
Contenu: {body}

TÂCHE:
1. Choisis la MEILLEURE catégorie
2. Extrais 3-5 mots-clés importants

Réponds en JSON: {{"category": "CATÉGORIE", "keywords": ["mot1","mot2","mot3"]}}""",
        "temperature": 0.15,
        "top_p": 0.9,
        "repeat_penalty": 1.05,
        "num_predict": 70,
        "num_ctx": 8192,
    },

    "gemma2": {
        # gemma2 Best Practices:
        # - Deutsche Anweisungen
        # - Klare, direkte Aufgabenstellung
        # - Temperatur 0.1 für Präzision
        # - Standard Kontext-Fenster
        "system": "Du bist ein deutscher Email-Klassifizierer mit Fokus auf Genauigkeit und Effizienz.",
        "user": """Emailanalyse erforderlich!

Verfügbare Kategorien:
{category_list}

Email-Daten:
Absender: {sender}
Betreff: {subject}
Inhalt: {body}

Aufgabe:
1. Korrekte Kategorie wählen
2. Wichtige Begriffe extrahieren (3-5 Stück)

Ergebnis als JSON: {{"category": "KATEGORIE", "keywords": ["begriff1","begriff2"]}}""",
        "temperature": 0.1,
        "top_p": 0.95,
        "repeat_penalty": 1.08,
        "num_predict": 65,
        "num_ctx": 4096,
    },
}


def get_model_prompt_config(model: str) -> Dict[str, Any]:
    """
    Gibt die modellspezifische Prompt-Konfiguration zurück.

    Diese Konfiguration ist HARDCODED und basiert auf umfangreichen Tests
    mit verschiedenen Modellen. Die Prompts sind für jedes Modell
    optimiert basierend auf:
    - Sprachverständnis (Deutsch/Englisch)
    - JSON-Output-Kompatibilität
    - Kontext-Fenster
    - Temperatur-Empfindlichkeit
    - Repeat-Penalty-Verhalten

    Args:
        model: Modell-Name (z.B. "llama3.1:8b", "gemma4:e4b", "phi3:mini")

    Returns:
        Dict mit system_prompt, user_prompt, und Parameter-Einstellungen
    """
    # Normalisiere Modell-Namen
    model_key = model.lower().strip()

    # Exact Match
    if model_key in _MODEL_PROMPTS:
        return _MODEL_PROMPTS[model_key]

    # Pattern Matching für Modell-Varianten
    if "llama" in model_key and "3.1" in model_key:
        return _MODEL_PROMPTS["llama3.1:8b"]
    elif "gemma" in model_key and "4" in model_key:
        return _MODEL_PROMPTS["gemma4:e4b"]
    elif "phi" in model_key and "3" in model_key:
        return _MODEL_PROMPTS["phi3:mini"]
    elif "mistral" in model_key:
        return _MODEL_PROMPTS["mistral"]
    elif "gemma" in model_key and "2" in model_key:
        return _MODEL_PROMPTS["gemma2"]

    # Fallback: llama3.1:8b (beste Balance)
    return _MODEL_PROMPTS["llama3.1:8b"]


def classify_with_ollama(
    ollama_url: str,
    model: str,
    categories: List[str],
    sender: str,
    subject: str,
    body: str,
    timeout: int = 120,
    think_mode: Any = False,
    num_predict: int = None,
    num_ctx: int = None,
) -> Tuple[str, List[str]]:
    """Returns (category, keywords). Keywords are 3-5 search terms extracted by LLM.

    Diese Funktion verwendet modellspezifische Prompts, die für jedes LLM-Modell
    optimiert sind basierend auf Best Practices für Prompt Engineering.

    Modelle mit optimierten Prompts:
    - llama3.1:8b: Strukturierte Prompts, JSON-Format, präzise Anweisungen
    - gemma4:e4b: Kontext-basiert, ausführliche Erklärungen, Führung
    - phi3:mini: Kurze Prompts, einfache Sprache, effizient

    Die Prompts sind HARDCODED und basieren auf umfangreichen Tests.
    """
    # Modellspezifische Prompt-Konfiguration holen
    model_config = get_model_prompt_config(model)

    # Kategorien-Liste formatieren
    category_list = "\n".join(f"- {c}: {_CATEGORY_DEFS.get(c, c)}" for c in categories)
    category_list_simple = ", ".join(categories)

    # User-Prompt mit modellspezifischem Template
    user_prompt = model_config["user"].format(
        category_list=category_list,
        category_list_simple=category_list_simple,
        sender=sender,
        subject=subject,
        body=body[:1500]  # Body auf 1500 Zeichen limitieren für Performance
    )

    # JSON Schema für strukturierte Ausgabe
    schema = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": categories},
            "keywords": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        },
        "required": ["category"],
    }

    # Parameter aus Konfiguration oder Default
    temperature = model_config.get("temperature", 0.1)
    top_p = model_config.get("top_p", 0.9)
    repeat_penalty = model_config.get("repeat_penalty", 1.1)
    num_predict = num_predict or model_config.get("num_predict", 60)
    num_ctx = num_ctx or model_config.get("num_ctx", 4096)

    payload = {
        "model": model,
        "stream": False,
        "think": think_mode,
        "keep_alive": "30m",
        "format": schema,
        "messages": [
            {"role": "system", "content": model_config["system"]},
            {"role": "user", "content": user_prompt}
        ],
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty
        },
    }
    req = urllib.request.Request(
        url=f"{ollama_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama request failed: {e}") from e

    data = json.loads(raw)
    content = data.get("message", {}).get("content", "").strip()

    # Strip markdown fences Gemma occasionally adds
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I).strip()
        content = re.sub(r"\s*```$", "", content).strip()

    # Handle plain string response ("newsletter" instead of {"category":"newsletter"})
    if not content.startswith("{"):
        plain = content.strip().strip('"\'').lower()
        if plain in categories:
            return plain, []
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            content = m.group(0).strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        lowered = content.lower()
        for c in categories:
            if c.lower() in lowered:
                return c, []
        raise RuntimeError(f"Model returned unparseable: {content[:200]!r}")

    category = str(parsed.get("category", "")).strip().lower()
    if category not in categories:
        lowered = (content + " " + json.dumps(parsed, ensure_ascii=False)).lower()
        for c in categories:
            if c.lower() in lowered:
                category = c
                break
        else:
            raise RuntimeError(f"Invalid category: {category!r}")

    raw_kw = parsed.get("keywords", [])
    keywords = [str(k).strip().lower() for k in raw_kw if str(k).strip()][:5]
    return category, keywords


# ── IMAP helpers ────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def ensure_folder(conn: imaplib.IMAP4_SSL, folder: str) -> None:
    typ, data = conn.create(folder)
    if typ == "OK":
        return
    msg = data[0].decode(errors="ignore") if data and data[0] else ""
    if "exists" in msg.lower():
        return
    log(f"WARN ensure_folder({folder}): {typ} {msg}")


def _extract_bytes(fetched: Any) -> Optional[bytes]:
    for item in fetched:
        if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], (bytes, bytearray)):
            return bytes(item[1])
    return None


def batch_fetch_headers(conn: imaplib.IMAP4_SSL, msg_ids: List[bytes]) -> List[Tuple[bytes, bytes]]:
    """Fetch headers for ALL messages in one IMAP command (big performance win).
    Returns list of (seq_id_bytes, header_bytes)."""
    if not msg_ids:
        return []
    id_str = b",".join(msg_ids)
    typ, data = conn.fetch(id_str, "(BODY.PEEK[HEADER])")
    if typ != "OK" or not data:
        return []
    results = []
    for item in data:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        if not isinstance(item[1], bytes):
            continue
        m = re.match(rb"(\d+)\s+\(", item[0])
        if m:
            results.append((m.group(1), item[1]))
    return results


# ── Core processor ──────────────────────────────────────────────────────────────

def process_account(
    cfg: Dict[str, Any],
    global_cfg: Dict[str, Any],
    dry_run: bool,
    max_per_account: int,
    days_back: int,
    all_messages: bool = False,
    no_delay: bool = False,
    source_folder_override: Optional[str] = None,
    sender_cache: Optional[Dict[str, str]] = None,
    cache_lock: Optional[threading.Lock] = None,
    cache_path: Optional[str] = None,
    index_db: Optional[Any] = None,
) -> Dict[str, int]:
    """Sort one account/folder. Returns stats dict."""
    name = cfg["name"]
    host = cfg["imap_host"]
    port = int(cfg.get("imap_port", 993))
    imap_encryption = str(cfg.get("imap_encryption", "ssl")).lower()
    imap_timeout_sec = int(cfg.get("imap_timeout_sec", global_cfg.get("imap_timeout_sec", 25)))
    username = cfg["username"]
    source_folder = source_folder_override or cfg.get("source_folder", "INBOX")
    target_folders = cfg["target_folders"]

    # Merge global_rules (apply to all accounts) + account-specific rules
    global_rules: List[Dict] = global_cfg.get("global_rules", [])
    account_rules: List[Dict] = cfg.get("rules", [])
    rules = global_rules + account_rules

    important_rules = cfg.get("important_rules", global_cfg.get("important_rules", []))
    important_actions = cfg.get("important_actions", {"flagged": True, "keyword": "$Important"})

    pw = cfg.get("password") or os.getenv(cfg.get("password_env", ""))
    if not pw:
        raise RuntimeError(f"[{name}] password missing (set {cfg.get('password_env')})")

    delay_minutes = 0 if no_delay else int(global_cfg.get("delay_minutes", 1440))
    max_body_chars = int(global_cfg.get("max_body_chars", 2500))
    ollama_url = global_cfg["ollama_url"]
    model = global_cfg["model"]
    ollama_timeout_sec = int(global_cfg.get("ollama_timeout_sec", 120))
    ollama_think = global_cfg.get("ollama_think", False)
    ollama_num_predict = int(global_cfg.get("ollama_num_predict", 20))
    ollama_num_ctx = int(global_cfg.get("ollama_num_ctx", 4096))
    categories = global_cfg["categories"]
    if len(categories) > 15:
        raise RuntimeError(f"[{name}] max 15 categories, got {len(categories)}")
    default_category = global_cfg.get("default_category", "privat")

    log(f"[{name}] connecting {host}:{port} as {username}")
    if imap_encryption == "starttls":
        conn = imaplib.IMAP4(host, port, timeout=imap_timeout_sec)
        conn.starttls(ssl_context=ssl.create_default_context())
    else:
        conn = imaplib.IMAP4_SSL(host, port, timeout=imap_timeout_sec,
                                  ssl_context=ssl.create_default_context())
    try:
        conn.login(username, pw)
        typ, _ = conn.select(source_folder)
        if typ != "OK":
            raise RuntimeError(f"cannot select folder {source_folder!r}")

        if all_messages:
            typ, data = conn.search(None, "ALL")
        else:
            since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_back)).strftime("%d-%b-%Y")
            typ, data = conn.search(None, "SINCE", since)
        if typ != "OK":
            raise RuntimeError("IMAP search failed")

        msg_ids = list(reversed(data[0].split())) if data and data[0] else []
        if not msg_ids:
            log(f"[{name}/{source_folder}] no messages")
            return {"moved": 0, "skipped": 0, "errors": 0, "by_rule": 0, "by_llm": 0, "by_cache": 0}

        msg_ids = msg_ids[:max_per_account]
        log(f"[{name}/{source_folder}] {len(msg_ids)} message(s) to process")

        # ── BATCH fetch all headers in ONE IMAP command ──────────────────────
        header_map: Dict[bytes, bytes] = {}
        for seq_id, hdr_bytes in batch_fetch_headers(conn, msg_ids):
            header_map[seq_id] = hdr_bytes

        moved = skipped = errors = by_rule = by_llm = by_cache = 0

        for msg_id in msg_ids:
            raw_header = header_map.get(msg_id)
            if not raw_header:
                log(f"[{name}] WARN no header for msg {msg_id!r}")
                errors += 1
                continue

            header_msg = email.message_from_bytes(raw_header)
            subject = decode_header_value(header_msg.get("Subject"))
            from_addr = decode_header_value(header_msg.get("From"))
            msg_date = parse_date(header_msg.get("Date", ""))
            important = is_important_message(important_rules, from_addr, subject)

            # ⏰ 30-Minuten-Regel für Paperless-ngx (ALLE Mails, auch Regeln!)
            if delay_minutes and should_delay(msg_date, delay_minutes):
                age_minutes = int((dt.datetime.now(dt.timezone.utc) - msg_date).total_seconds() / 60) if msg_date else 0
                delay_remaining = delay_minutes - age_minutes
                log(f"[{name}] ⏰ SKIP {delay_remaining}min für Paperless: {subject[:60]}")
                skipped += 1
                continue

            # ── Decision: List-Unsubscribe → Rule → Cache → LLM ────────────
            keywords: List[str] = []
            body: str = ""
            raw_full: Optional[bytes] = None

            # Reliable newsletter signal — no LLM needed
            list_unsub = header_msg.get("List-Unsubscribe") or header_msg.get("List-Id")

            rule_target = first_match_rule(rules, from_addr, subject)
            if rule_target:
                category = rule_target
                by_rule += 1
                log(f"[{name}] ✓ REGEL {delay_minutes}min+ → {category}: {subject[:60]}")

            elif list_unsub and "newsletter" in target_folders:
                category = "newsletter"
                by_rule += 1
                log(f"[{name}] list-unsub → newsletter: {subject[:80]}")

            elif sender_cache is not None and (addr := extract_email_addr(from_addr)) in sender_cache:
                category = sender_cache[addr]
                by_cache += 1
                log(f"[{name}] cache → {category}: {subject[:80]}")

            else:
                # Fetch full message body only when LLM is needed
                typ2, full_fetched = conn.fetch(msg_id, "(BODY.PEEK[])")
                if typ2 != "OK" or not full_fetched:
                    log(f"[{name}] WARN body fetch failed for {msg_id!r}")
                    errors += 1
                    continue
                raw_full = _extract_bytes(full_fetched)
                if not raw_full:
                    log(f"[{name}] WARN no body bytes for {msg_id!r}: {str(full_fetched)[:80]}")
                    errors += 1
                    continue
                body = extract_text(email.message_from_bytes(raw_full), max_body_chars)
                keywords = []
                try:
                    category, keywords = classify_with_ollama(
                        ollama_url, model, categories,
                        from_addr, subject, body,
                        timeout=ollama_timeout_sec, think_mode=ollama_think,
                        num_predict=ollama_num_predict, num_ctx=ollama_num_ctx,
                    )
                    by_llm += 1
                    kw_str = ", ".join(keywords) if keywords else ""
                    log(f"[{name}] llm  → {category}: {subject[:80]}"
                        + (f"  [{kw_str}]" if kw_str else ""))
                    # Learn this sender for future runs
                    if sender_cache is not None and cache_lock and cache_path:
                        addr = extract_email_addr(from_addr)
                        sender_cache[addr] = category
                        save_sender_cache(cache_path, sender_cache, cache_lock)
                except Exception as e:
                    log(f"[{name}] ollama failed → {default_category}: {e}")
                    category = default_category

            target_folder = target_folders.get(category,
                            target_folders.get(default_category, source_folder))
            if target_folder == source_folder:
                log(f"[{name}] keep ({category}): {subject[:80]}")
                skipped += 1
                continue

            # Erweiterungen ausführen (Paperless, Kalender, Tasks, etc.)
            extensions_cfg = global_cfg.get("extensions", {})
            if extensions_cfg.get("enabled", False):
                try:
                    run_extensions(category, from_addr, subject, body, extensions_cfg, global_cfg)
                except Exception as e:
                    log(f"[{name}] WARN extensions failed: {e}")

            ensure_folder(conn, target_folder)

            if important and not dry_run:
                try:
                    if important_actions.get("flagged", True):
                        conn.store(msg_id, "+FLAGS", "\\Flagged")
                    kw = str(important_actions.get("keyword", "")).strip()
                    if kw:
                        conn.store(msg_id, "+FLAGS", kw)
                except Exception as e:
                    log(f"[{name}] WARN mark-important failed: {e}")

            if dry_run:
                log(f"[{name}] DRY-RUN {subject[:80]!r} → {target_folder}")
                moved += 1
                continue

            # Fetch full message for rule/cache path (LLM path already has raw_full)
            if raw_full is None:
                typ_f, fetched_f = conn.fetch(msg_id, "(BODY.PEEK[])")
                if typ_f == "OK" and fetched_f:
                    raw_full = _extract_bytes(fetched_f)

            copy_ok = False
            if raw_full is not None:
                # Inject X-Keywords + X-Category headers so Apple Mail / Spotlight finds them
                full_msg = email.message_from_bytes(raw_full)
                del full_msg["X-Keywords"]
                del full_msg["X-Category"]
                if keywords:
                    full_msg["X-Keywords"] = ", ".join(keywords)
                full_msg["X-Category"] = category
                buf = io.BytesIO()
                email.generator.BytesGenerator(buf, mangle_from_=False).flatten(full_msg)
                idate = imaplib.Time2Internaldate(
                    msg_date.timestamp() if msg_date else time.time()
                )
                app_typ, _ = conn.append(target_folder, None, idate, buf.getvalue())
                copy_ok = app_typ == "OK"
            else:
                # Fallback: plain COPY (no keyword injection)
                copy_typ, _ = conn.copy(msg_id, target_folder)
                copy_ok = copy_typ == "OK"

            if not copy_ok:
                log(f"[{name}] copy/append failed → {target_folder}: {subject[:80]}")
                errors += 1
                continue

            conn.store(msg_id, "+FLAGS", "\\Deleted")
            log(f"[{name}] moved → {target_folder}: {subject[:80]}")
            moved += 1

            if index_db is not None:
                try:
                    date_str = msg_date.isoformat() if msg_date else None
                    _index_email(index_db, name, target_folder, from_addr, subject,
                                 date_str, category, keywords, body[:200])
                except Exception as _ie:
                    log(f"[{name}] WARN index failed: {_ie}")

        if not dry_run:
            conn.expunge()

        stats = {"moved": moved, "skipped": skipped, "errors": errors,
                 "by_rule": by_rule, "by_llm": by_llm, "by_cache": by_cache}
        log(f"[{name}/{source_folder}] done — "
            f"moved={moved} (rule={by_rule} cache={by_cache} llm={by_llm}) "
            f"skipped={skipped} errors={errors}")
        return stats
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


# ── Parallel runner ─────────────────────────────────────────────────────────────

def _run_task(task: Dict[str, Any]) -> Dict[str, int]:
    try:
        return process_account(
            task["cfg"], task["global_cfg"],
            task["dry_run"], task["max_per_account"], task["days_back"],
            all_messages=task["all_messages"], no_delay=task["no_delay"],
            source_folder_override=task.get("source_folder_override"),
            sender_cache=task.get("sender_cache"),
            cache_lock=task.get("cache_lock"),
            cache_path=task.get("cache_path"),
            index_db=task.get("index_db"),
        ) or {}
    except Exception as e:
        label = task["cfg"].get("name", "?")
        src = task.get("source_folder_override", "")
        print(f"[{label}/{src}] ERROR: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return {"moved": 0, "skipped": 0, "errors": 1, "by_rule": 0, "by_llm": 0, "by_cache": 0}


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="AI IMAP mail sorter — Gemma4 via Ollama")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be moved, don't move")
    ap.add_argument("--max-per-account", type=int, default=50)
    ap.add_argument("--days-back", type=int, default=7, help="Only process mail from last N days")
    ap.add_argument("--all", dest="all_messages", action="store_true",
                    help="Process ALL messages regardless of date")
    ap.add_argument("--no-delay", action="store_true",
                    help="Skip the 30-min Paperless delay (use with --all for historical sort)")
    ap.add_argument("--account", default=None, help="Only this account (substring match)")
    ap.add_argument("--resort-folders", action="store_true",
                    help="Also re-sort already-categorised folders (fixes old mis-sorted mail)")
    ap.add_argument("--parallel", action="store_true",
                    help="Process accounts in parallel (faster)")
    ap.add_argument("--no-cache", action="store_true",
                    help="Disable sender cache (always call LLM)")
    args = ap.parse_args()

    config_path = args.config
    cfg = load_config(config_path)
    global_cfg = cfg["global"]

    # Sender cache: sits next to config.json
    cache_path = os.path.join(os.path.dirname(os.path.abspath(config_path)), "learned_senders.json")
    cache_lock = threading.Lock()
    sender_cache: Optional[Dict[str, str]] = None if args.no_cache else load_sender_cache(cache_path)
    if sender_cache is not None:
        log(f"Sender cache loaded: {len(sender_cache)} known senders")

    # SQLite index
    index_db = _get_db(_DB_PATH) if HAS_INDEX else None
    if index_db is not None:
        log(f"Mail index ready: {_DB_PATH}")

    accounts = cfg.get("accounts", [])
    if args.account:
        accounts = [a for a in accounts if args.account.lower() in a.get("name", "").lower()]
        if not accounts:
            print(f"ERROR: no account matching {args.account!r}", file=sys.stderr)
            return 1

    tasks: List[Dict[str, Any]] = []
    for acc in accounts:
        base = dict(
            cfg=acc, global_cfg=global_cfg,
            dry_run=args.dry_run, max_per_account=args.max_per_account,
            days_back=args.days_back, all_messages=args.all_messages,
            no_delay=args.no_delay, source_folder_override=None,
            sender_cache=sender_cache, cache_lock=cache_lock, cache_path=cache_path,
            index_db=index_db,
        )
        tasks.append(base)
        if args.resort_folders:
            for folder in sorted(set(acc.get("target_folders", {}).values())):
                tasks.append({**base, "all_messages": True, "no_delay": True,
                               "source_folder_override": folder})

    total: Dict[str, int] = {"moved": 0, "skipped": 0, "errors": 0,
                              "by_rule": 0, "by_llm": 0, "by_cache": 0}

    if args.parallel and len(tasks) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(tasks))) as pool:
            for stats in pool.map(_run_task, tasks):
                for k in total:
                    total[k] += stats.get(k, 0)
    else:
        for task in tasks:
            for k, v in _run_task(task).items():
                total[k] = total.get(k, 0) + v

    if len(accounts) > 1 or args.resort_folders:
        log(
            f"=== GESAMT — moved={total['moved']} "
            f"(rule={total['by_rule']} cache={total['by_cache']} llm={total['by_llm']}) "
            f"skipped={total['skipped']} errors={total['errors']} ==="
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
