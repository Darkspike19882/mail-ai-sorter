#!/usr/bin/env python3
"""
AI-Features für den Email-Client — Zusammenfassung, Reply-Vorschläge, Phishing-Erkennung.
Baut auf der Ollama-Infrastruktur aus sorter.py auf (gleiche HTTP-Logik, neue Prompts).
"""

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


# ── Ollama-Basis-Call ──────────────────────────────────────────────────────────

def _call_ollama(
    ollama_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_schema: Optional[Dict[str, Any]] = None,
    temperature: float = 0.3,
    num_predict: int = 256,
    timeout: int = 120,
) -> str:
    """
    Generischer Ollama-Call. Gibt den Roh-Content-String zurück.
    Identische urllib-Logik wie classify_with_ollama() in sorter.py.
    """
    payload: Dict[str, Any] = {
        "model":      model,
        "stream":     False,
        "keep_alive": "30m",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "options": {
            "temperature":    temperature,
            "num_predict":    num_predict,
            "top_p":          0.9,
            "repeat_penalty": 1.1,
        },
    }
    if response_schema:
        payload["format"] = response_schema

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
        raise RuntimeError(f"Ollama nicht erreichbar: {e}") from e

    data = json.loads(raw)
    content = data.get("message", {}).get("content", "").strip()

    # Markdown-Code-Fences entfernen (Gemma macht das manchmal)
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I).strip()
        content = re.sub(r"\s*```$", "", content).strip()

    return content


def _parse_json_safe(content: str, fallback: Any = None) -> Any:
    """Parst JSON aus LLM-Antwort — tolerant gegenüber umgebenden Texten."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        m2 = re.search(r"\[[\s\S]*\]", content)
        if m2:
            try:
                return json.loads(m2.group(0))
            except json.JSONDecodeError:
                pass
    return fallback


# ── Zusammenfassung ────────────────────────────────────────────────────────────

def summarize(
    subject: str,
    body: str,
    from_addr: str,
    ollama_url: str,
    model: str,
    max_sentences: int = 3,
    timeout: int = 60,
) -> str:
    """
    Fasst eine Mail in max. {max_sentences} Sätzen zusammen.
    Gibt den Zusammenfassungs-String zurück.
    """
    system = (
        "Du bist ein präziser Email-Assistent. "
        "Fasse Emails kurz und klar auf Deutsch zusammen. "
        "Antworte NUR mit der Zusammenfassung, ohne Einleitung oder Schluss."
    )
    body_excerpt = (body or "")[:2000]
    user = (
        f"Betreff: {subject}\n"
        f"Von: {from_addr}\n\n"
        f"{body_excerpt}\n\n"
        f"---\n"
        f"Fasse diese Email in maximal {max_sentences} Sätzen zusammen."
    )
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
        },
        "required": ["summary"],
    }
    try:
        content = _call_ollama(
            ollama_url, model, system, user,
            response_schema=schema,
            temperature=0.2,
            num_predict=200,
            timeout=timeout,
        )
        parsed = _parse_json_safe(content)
        if parsed and isinstance(parsed, dict) and parsed.get("summary"):
            return parsed["summary"].strip()
        # Fallback: roher Text wenn JSON-Parsing fehlschlägt
        return content[:500].strip()
    except RuntimeError as e:
        raise


# ── Reply-Vorschläge ───────────────────────────────────────────────────────────

def suggest_replies(
    subject: str,
    body: str,
    from_addr: str,
    ollama_url: str,
    model: str,
    timeout: int = 90,
) -> List[Dict[str, str]]:
    """
    Schlägt 2 Antwort-Varianten vor: kurz-informell und professionell.
    Gibt [{"tone": str, "text": str}, ...] zurück.
    """
    system = (
        "Du bist ein hilfreicher Email-Assistent. "
        "Erstelle prägnante, natürliche Antworten auf Deutsch. "
        "Antworte im vorgegebenen JSON-Format."
    )
    body_excerpt = (body or "")[:1500]
    user = (
        f"Betreff: {subject}\n"
        f"Von: {from_addr}\n\n"
        f"{body_excerpt}\n\n"
        f"---\n"
        f"Erstelle 2 verschiedene Antwort-Entwürfe auf diese Email:\n"
        f"1. Kurz und freundlich (max. 3 Sätze)\n"
        f"2. Professionell und ausführlicher\n\n"
        f"Antworte als JSON mit diesem Format:\n"
        f'{{"replies": [{{"tone": "kurz", "text": "..."}}, {{"tone": "professionell", "text": "..."}}]}}'
    )
    schema = {
        "type": "object",
        "properties": {
            "replies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tone": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["tone", "text"],
                },
            },
        },
        "required": ["replies"],
    }
    try:
        content = _call_ollama(
            ollama_url, model, system, user,
            response_schema=schema,
            temperature=0.5,
            num_predict=400,
            timeout=timeout,
        )
        parsed = _parse_json_safe(content)
        if parsed and isinstance(parsed, dict) and parsed.get("replies"):
            return [
                {"tone": r.get("tone", ""), "text": r.get("text", "")}
                for r in parsed["replies"]
                if r.get("text")
            ][:3]
        return []
    except RuntimeError:
        raise


# ── Phishing-Erkennung ─────────────────────────────────────────────────────────

_PHISHING_KEYWORDS = [
    "dringend", "sofort handeln", "konto gesperrt", "verifizieren sie",
    "klicken sie hier", "passwort bestätigen", "gewonnen", "preis",
    "suspicious", "verify your account", "click here immediately",
    "account suspended", "unusual activity", "confirm your identity",
    "wire transfer", "bitcoin", "gift card", "inheritance",
    "ihr paket", "dhl benachrichtigung", "fedex", "zollgebühr",
    "rechnung überfällig", "letzte mahnung", "inkasso",
]

_SUSPICIOUS_URL_PATTERNS = [
    r"bit\.ly/", r"tinyurl\.com/", r"t\.co/",
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # Roh-IP als URL
    r"[a-z0-9\-]{20,}\.(tk|ml|ga|cf|pw|top|xyz|click|link)",
]


def _rule_based_phishing(
    from_addr: str,
    subject: str,
    body: str,
) -> Tuple[float, List[str]]:
    """Schnelle regelbasierte Vorprüfung. Gibt (score_0_to_1, reasons) zurück."""
    score = 0.0
    reasons: List[str] = []
    text = f"{subject} {body}".lower()

    # Urgency-Keywords
    matched_kw = [kw for kw in _PHISHING_KEYWORDS if kw.lower() in text]
    if matched_kw:
        score += min(0.4, len(matched_kw) * 0.1)
        reasons.append(f"Dringlichkeits-Begriffe gefunden: {', '.join(matched_kw[:3])}")

    # Domain-Mismatch: Angezeigter Name vs. tatsächliche Absender-Domain
    display_m = re.search(r'"?([^"<@]+(?:paypal|amazon|apple|google|dhl|bank|sparkasse|volksbank)[^"<@]*)"?\s*<', from_addr, re.I)
    domain_m  = re.search(r"@([^>]+)>?", from_addr)
    if display_m and domain_m:
        domain = domain_m.group(1).lower()
        displayed_brand = re.search(r"paypal|amazon|apple|google|dhl|bank|sparkasse|volksbank", display_m.group(1), re.I)
        if displayed_brand and displayed_brand.group(0).lower() not in domain:
            score += 0.4
            reasons.append(f"Domain-Mismatch: Absendername nennt '{displayed_brand.group(0)}', Domain ist '{domain}'")

    # Verdächtige URL-Muster im Body
    suspicious_urls = []
    for pattern in _SUSPICIOUS_URL_PATTERNS:
        found = re.findall(pattern, body, re.I)
        suspicious_urls.extend(found)
    if suspicious_urls:
        score += min(0.3, len(suspicious_urls) * 0.15)
        reasons.append(f"Verdächtige URLs gefunden")

    return min(score, 1.0), reasons


def check_phishing(
    from_addr: str,
    subject: str,
    body: str,
    ollama_url: str,
    model: str,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Kombinierte Phishing-Erkennung: regelbasiert (schnell) + LLM (gründlich).
    Gibt {risk_score, risk_level, reasons, suspicious_links} zurück.
    """
    # 1. Regelbasierter Schnell-Check
    rule_score, rule_reasons = _rule_based_phishing(from_addr, subject, body)

    # 2. LLM-Analyse
    system = (
        "Du bist ein Cybersecurity-Experte. "
        "Analysiere Emails auf Phishing, Betrug und Social Engineering. "
        "Antworte ausschließlich im JSON-Format."
    )
    body_excerpt = (body or "")[:1000]
    user = (
        f"Analysiere diese Email auf Phishing/Betrug:\n\n"
        f"Von: {from_addr}\n"
        f"Betreff: {subject}\n\n"
        f"{body_excerpt}\n\n"
        f"Antworte als JSON:\n"
        f'{{"risk_score": 0.0-1.0, "is_suspicious": true/false, '
        f'"reasons": ["Grund1", "Grund2"], "verdict": "sicher|verdächtig|phishing"}}'
    )
    schema = {
        "type": "object",
        "properties": {
            "risk_score":    {"type": "number"},
            "is_suspicious": {"type": "boolean"},
            "reasons":       {"type": "array", "items": {"type": "string"}},
            "verdict":       {"type": "string"},
        },
        "required": ["risk_score", "is_suspicious", "verdict"],
    }

    llm_score   = rule_score
    llm_reasons = list(rule_reasons)
    try:
        content = _call_ollama(
            ollama_url, model, system, user,
            response_schema=schema,
            temperature=0.1,
            num_predict=200,
            timeout=timeout,
        )
        parsed = _parse_json_safe(content)
        if parsed and isinstance(parsed, dict):
            llm_raw = float(parsed.get("risk_score", 0))
            # Kombiniere: 40% Regeln + 60% LLM
            llm_score = rule_score * 0.4 + llm_raw * 0.6
            llm_reasons = list(rule_reasons) + [
                r for r in (parsed.get("reasons") or [])
                if r and r not in llm_reasons
            ]
    except RuntimeError:
        pass  # Nur Regel-Score wenn Ollama nicht erreichbar

    # Risk-Level bestimmen
    if llm_score >= 0.65:
        level = "high"
    elif llm_score >= 0.35:
        level = "medium"
    else:
        level = "low"

    # Verdächtige URLs extrahieren
    urls = re.findall(r"https?://[^\s<>\"']+", body)
    suspicious_urls = [
        u for u in urls
        if any(re.search(p, u, re.I) for p in _SUSPICIOUS_URL_PATTERNS)
    ]

    return {
        "risk_score":      round(llm_score, 2),
        "risk_level":      level,
        "reasons":         llm_reasons[:5],
        "suspicious_links": suspicious_urls[:5],
    }


# ── Termin- und Aufgaben-Erkennung ────────────────────────────────────────────

def extract_events(
    subject: str,
    body: str,
    from_addr: str,
    ollama_url: str,
    model: str,
    timeout: int = 90,
) -> List[Dict[str, Any]]:
    """
    Erkennt Termine, Deadlines und Aufgaben in einer Mail.

    Gibt eine Liste von Ereignissen zurück:
    [
      {
        "title":    str,   # Bezeichnung des Termins/der Aufgabe
        "type":     str,   # "meeting" | "deadline" | "task" | "event"
        "date":     str,   # ISO-Datum oder beschreibend, z.B. "2025-06-15"
        "time":     str,   # Uhrzeit z.B. "14:30" oder ""
        "location": str,   # Ort oder Videolink oder ""
        "notes":    str,   # Zusätzliche Hinweise oder ""
      }
    ]
    Leere Liste wenn keine Ereignisse erkannt.
    """
    system = (
        "Du bist ein intelligenter Email-Assistent. "
        "Extrahiere alle Termine, Meetings, Deadlines und Aufgaben aus der Email. "
        "Antworte NUR mit einem JSON-Array. Wenn nichts gefunden, antworte mit []."
    )
    body_excerpt = (body or "")[:2500]
    user = (
        f"Betreff: {subject}\n"
        f"Von: {from_addr}\n\n"
        f"{body_excerpt}\n\n"
        f"---\n"
        f"Extrahiere alle Termine, Meetings, Deadlines und Aufgaben als JSON-Array.\n"
        f"Jedes Element hat: title, type (meeting/deadline/task/event), date, time, location, notes.\n"
        f"Fehlende Felder als leeren String. Nur tatsächlich erkannte Ereignisse zurückgeben."
    )
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title":    {"type": "string"},
                "type":     {"type": "string", "enum": ["meeting", "deadline", "task", "event"]},
                "date":     {"type": "string"},
                "time":     {"type": "string"},
                "location": {"type": "string"},
                "notes":    {"type": "string"},
            },
            "required": ["title", "type", "date"],
        },
    }

    try:
        content = _call_ollama(
            ollama_url, model, system, user,
            response_schema=schema,
            temperature=0.1,
            num_predict=500,
            timeout=timeout,
        )
        parsed = _parse_json_safe(content, fallback=[])
        if isinstance(parsed, list):
            events = []
            for ev in parsed:
                if not isinstance(ev, dict) or not ev.get("title"):
                    continue
                events.append({
                    "title":    str(ev.get("title", ""))[:120],
                    "type":     ev.get("type", "event") if ev.get("type") in ("meeting", "deadline", "task", "event") else "event",
                    "date":     str(ev.get("date", "")),
                    "time":     str(ev.get("time", "")),
                    "location": str(ev.get("location", "")),
                    "notes":    str(ev.get("notes", ""))[:200],
                })
            return events
        return []
    except RuntimeError:
        return []
