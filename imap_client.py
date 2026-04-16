#!/usr/bin/env python3
"""
IMAP-Client — persistente, thread-sichere IMAP-Verbindungen für den Email-Client.

Wiederverwendet aus sorter.py:
  - SSL/STARTTLS-Verbindungslogik
  - decode_header_value()
  - extract_text()
  - parse_date()
  - extract_email_addr()
"""

import email
import email.header
import email.utils
import email.generator
import imaplib
import io
import os
import re
import ssl
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import nh3
    _HAS_NH3 = True
except ImportError:
    _HAS_NH3 = False


# ── Email-Hilfsfunktionen (aus sorter.py übernommen) ───────────────────────────

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


def extract_text(msg: email.message.Message, max_chars: int = 3000) -> str:
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


def extract_html(msg: email.message.Message) -> str:
    """Extrahiert den rohen HTML-Body (erster text/html-Part)."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                disp = str(part.get("Content-Disposition") or "").lower()
                if "attachment" in disp:
                    continue
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        if msg.get_content_type() == "text/html":
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
    return ""


def sanitize_html(html: str) -> str:
    """Bereinigt HTML mit nh3 (XSS-Schutz). Fallback: HTML-Escaping."""
    if not html:
        return ""
    if _HAS_NH3:
        return nh3.clean(
            html,
            tags={
                "p", "br", "b", "i", "strong", "em", "u", "s", "a",
                "blockquote", "ul", "ol", "li", "table", "thead", "tbody",
                "tr", "td", "th", "h1", "h2", "h3", "h4", "hr",
                "span", "div", "img", "pre", "code", "font",
            },
            attributes={
                "a":    {"href", "title", "target"},
                "img":  {"src", "alt", "width", "height"},
                "td":   {"colspan", "rowspan", "align", "valign"},
                "th":   {"colspan", "rowspan", "align", "valign"},
                "font": {"color", "size", "face"},
                "*":    {"style"},
            },
            url_schemes={"https", "http", "mailto"},
        )
    # Fallback ohne nh3: Plain-Text zurückgeben
    import html as _html
    return f"<pre>{_html.escape(html)}</pre>"


def parse_date(date_header: str):
    import datetime as dt
    try:
        parsed = email.utils.parsedate_to_datetime(date_header)
    except Exception:
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def extract_email_addr(from_str: str) -> str:
    m = re.search(r"<([^>]+)>", from_str)
    if m:
        return m.group(1).lower().strip()
    return from_str.lower().strip()


def _extract_bytes(fetched: Any) -> Optional[bytes]:
    for item in fetched:
        if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], (bytes, bytearray)):
            return bytes(item[1])
    return None


# ── Attachment-Parsing ─────────────────────────────────────────────────────────

def list_attachments(msg: email.message.Message) -> List[Dict[str, Any]]:
    """Gibt Liste der Anhänge zurück: [{part_id, filename, content_type, size}]."""
    attachments = []
    part_id = 0
    for part in msg.walk():
        part_id += 1
        disp = str(part.get("Content-Disposition") or "").lower()
        ctype = part.get_content_type()
        filename = decode_header_value(part.get_filename() or "")
        if "attachment" in disp or (filename and ctype != "text/plain" and ctype != "text/html"):
            payload = part.get_payload(decode=True)
            size = len(payload) if payload else 0
            if filename or "attachment" in disp:
                attachments.append({
                    "part_id":      part_id,
                    "filename":     filename or f"anhang_{part_id}",
                    "content_type": ctype,
                    "size":         size,
                })
    return attachments


def get_attachment_bytes(msg: email.message.Message, part_id: int) -> Tuple[bytes, str, str]:
    """Gibt (bytes, filename, content_type) eines Anhangs zurück."""
    current_id = 0
    for part in msg.walk():
        current_id += 1
        if current_id == part_id:
            payload = part.get_payload(decode=True) or b""
            filename = decode_header_value(part.get_filename() or f"anhang_{part_id}")
            return payload, filename, part.get_content_type()
    raise ValueError(f"Part {part_id} nicht gefunden")


# ── IMAPSession ─────────────────────────────────────────────────────────────────

class IMAPSession:
    """
    Thread-sichere persistente IMAP-Verbindung für einen Account.
    Nutzt einen internen Lock, damit mehrere Flask-Threads sicher zugreifen können.
    """

    def __init__(self, account_cfg: Dict[str, Any]):
        self._cfg = account_cfg
        self._conn: Optional[imaplib.IMAP4] = None
        self._lock = threading.Lock()
        self._last_folder: Optional[str] = None

    @property
    def name(self) -> str:
        return self._cfg.get("name", "?")

    def connect(self) -> None:
        host = self._cfg["imap_host"]
        port = int(self._cfg.get("imap_port", 993))
        encryption = str(self._cfg.get("imap_encryption", "ssl")).lower()
        timeout = int(self._cfg.get("imap_timeout_sec", 25))
        pw = self._cfg.get("password") or os.getenv(self._cfg.get("password_env", ""), "")
        if not pw:
            raise RuntimeError(f"[{self.name}] Passwort fehlt")

        # SSL/STARTTLS — identisch mit sorter.py:699-704
        if encryption == "starttls":
            conn = imaplib.IMAP4(host, port, timeout=timeout)
            conn.starttls(ssl_context=ssl.create_default_context())
        else:
            conn = imaplib.IMAP4_SSL(
                host, port, timeout=timeout,
                ssl_context=ssl.create_default_context(),
            )
        conn.login(self._cfg["username"], pw)
        self._conn = conn
        self._last_folder = None

    def reconnect_if_needed(self) -> None:
        """Prüft Verbindung via NOOP, reconnectet bei Fehler."""
        if self._conn is None:
            self.connect()
            return
        try:
            self._conn.noop()
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError):
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None
            self.connect()

    def _select(self, folder: str) -> None:
        """Selektiert einen Ordner (cached — kein extra Roundtrip wenn gleich)."""
        if self._last_folder != folder:
            typ, _ = self._conn.select(folder)
            if typ != "OK":
                raise RuntimeError(f"Ordner '{folder}' nicht gefunden")
            self._last_folder = folder

    def list_folders(self) -> List[Dict[str, Any]]:
        """Listet alle IMAP-Ordner mit Unread-Count."""
        with self._lock:
            self.reconnect_if_needed()
            typ, data = self._conn.list()
            if typ != "OK" or not data:
                return []

            folders = []
            for item in data:
                if not isinstance(item, bytes):
                    continue
                # Parst: (\HasNoChildren) "/" "INBOX"
                m = re.match(
                    rb'\(([^)]*)\)\s+"([^"]+)"\s+"?([^"]+)"?', item
                ) or re.match(
                    rb'\(([^)]*)\)\s+"([^"]+)"\s+(\S+)', item
                )
                if not m:
                    continue
                flags_raw = m.group(1).decode(errors="replace")
                name = m.group(3).decode(errors="replace").strip('"')
                if r"\Noselect" in flags_raw:
                    continue
                folders.append({"name": name, "flags": flags_raw})

            # Unread-Count per STATUS
            result = []
            for f in folders:
                try:
                    typ2, sdata = self._conn.status(
                        f'"{ f["name"] }"', "(MESSAGES UNSEEN)"
                    )
                    counts = {"total": 0, "unread": 0}
                    if typ2 == "OK" and sdata and sdata[0]:
                        raw = sdata[0].decode(errors="replace")
                        m2 = re.search(r"MESSAGES\s+(\d+)", raw)
                        m3 = re.search(r"UNSEEN\s+(\d+)", raw)
                        if m2:
                            counts["total"] = int(m2.group(1))
                        if m3:
                            counts["unread"] = int(m3.group(1))
                    result.append({**f, **counts})
                except Exception:
                    result.append({**f, "total": 0, "unread": 0})
            return result

    def fetch_headers(
        self,
        folder: str,
        limit: int = 50,
        offset: int = 0,
        search_criteria: str = "ALL",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lädt Mail-Header für einen Ordner (paginiert).
        Gibt (mails, total_count) zurück.
        IMAP hat kein natives OFFSET → UIDs werden clientseitig sortiert+sliced.
        """
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)

            typ, data = self._conn.uid("search", None, search_criteria)
            if typ != "OK" or not data or not data[0]:
                return [], 0

            all_uids = data[0].split()
            total = len(all_uids)
            # Neueste zuerst, dann Seite ausschneiden
            all_uids = list(reversed(all_uids))
            batch = all_uids[offset: offset + limit]
            if not batch:
                return [], total

            uid_set = b",".join(batch)
            typ2, fetched = self._conn.uid(
                "fetch", uid_set,
                "(FLAGS BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT MESSAGE-ID)])"
            )
            if typ2 != "OK" or not fetched:
                return [], total

            mails = []
            for item in fetched:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                if not isinstance(item[1], bytes):
                    continue
                uid_m = re.search(rb"UID\s+(\d+)", item[0])
                uid = uid_m.group(1).decode() if uid_m else None
                flags_m = re.search(rb"FLAGS\s+\(([^)]*)\)", item[0])
                flags_str = flags_m.group(1).decode(errors="replace") if flags_m else ""

                msg = email.message_from_bytes(item[1])
                date_obj = parse_date(msg.get("Date", ""))
                mails.append({
                    "uid":        uid,
                    "subject":    decode_header_value(msg.get("Subject")),
                    "from_addr":  decode_header_value(msg.get("From")),
                    "date_iso":   date_obj.isoformat() if date_obj else None,
                    "message_id": msg.get("Message-ID", "").strip(),
                    "seen":       "\\Seen" in flags_str,
                    "flagged":    "\\Flagged" in flags_str,
                    "flags":      flags_str,
                })
            return mails, total

    def fetch_message(self, folder: str, uid: str) -> Dict[str, Any]:
        """Lädt eine vollständige Mail. HTML wird mit nh3 bereinigt."""
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)

            typ, fetched = self._conn.uid("fetch", uid.encode(), "(FLAGS BODY.PEEK[])")
            if typ != "OK" or not fetched:
                raise RuntimeError(f"Mail UID {uid} nicht gefunden")

            raw = _extract_bytes(fetched)
            if not raw:
                raise RuntimeError(f"Kein Body für UID {uid}")

            flags_m = re.search(rb"FLAGS\s+\(([^)]*)\)", fetched[0][0] if isinstance(fetched[0], tuple) else b"")
            flags_str = flags_m.group(1).decode(errors="replace") if flags_m else ""

            msg = email.message_from_bytes(raw)
            date_obj = parse_date(msg.get("Date", ""))

            body_html_raw = extract_html(msg)
            body_html = sanitize_html(body_html_raw) if body_html_raw else ""
            body_text = extract_text(msg, max_chars=5000)

            # Als gelesen markieren
            try:
                self._conn.uid("store", uid.encode(), "+FLAGS", "\\Seen")
            except Exception:
                pass

            return {
                "uid":          uid,
                "folder":       folder,
                "subject":      decode_header_value(msg.get("Subject")),
                "from_addr":    decode_header_value(msg.get("From")),
                "to":           decode_header_value(msg.get("To")),
                "cc":           decode_header_value(msg.get("Cc", "")),
                "date_iso":     date_obj.isoformat() if date_obj else None,
                "message_id":   msg.get("Message-ID", "").strip(),
                "in_reply_to":  msg.get("In-Reply-To", "").strip(),
                "references":   msg.get("References", "").strip(),
                "body_html":    body_html,
                "body_text":    body_text,
                "attachments":  list_attachments(msg),
                "seen":         "\\Seen" in flags_str,
                "flagged":      "\\Flagged" in flags_str,
                "flags":        flags_str,
            }

    def set_flag(self, folder: str, uid: str, flag: str, value: bool) -> bool:
        """Setzt oder entfernt ein IMAP-Flag (z.B. \\Seen, \\Flagged)."""
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            op = "+FLAGS" if value else "-FLAGS"
            try:
                typ, _ = self._conn.uid("store", uid.encode(), op, flag)
                return typ == "OK"
            except Exception:
                return False

    def delete_message(self, folder: str, uid: str) -> bool:
        """Markiert als gelöscht und expungiert sofort."""
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            try:
                typ, _ = self._conn.uid("store", uid.encode(), "+FLAGS", "\\Deleted")
                if typ != "OK":
                    return False
                self._conn.expunge()
                self._last_folder = None  # Ordner-State nach Expunge zurücksetzen
                return True
            except Exception:
                return False

    def move_message(self, folder: str, uid: str, target: str) -> bool:
        """
        Verschiebt eine Mail in einen anderen Ordner.
        Versucht zuerst IMAP MOVE (RFC 6851), Fallback: COPY + DELETE.
        """
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            try:
                # RFC 6851 MOVE — wird von Gmail, iCloud, Fastmail unterstützt
                typ, _ = self._conn.uid("move", uid.encode(), target)
                if typ == "OK":
                    self._last_folder = None
                    return True
            except (imaplib.IMAP4.error, AttributeError):
                pass
            # Fallback: COPY + STORE \Deleted + EXPUNGE
            try:
                typ2, _ = self._conn.uid("copy", uid.encode(), target)
                if typ2 != "OK":
                    return False
                self._conn.uid("store", uid.encode(), "+FLAGS", "\\Deleted")
                self._conn.expunge()
                self._last_folder = None
                return True
            except Exception:
                return False

    def get_attachment(self, folder: str, uid: str, part_id: int) -> Tuple[bytes, str, str]:
        """Gibt (bytes, filename, content_type) eines Anhangs zurück."""
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            typ, fetched = self._conn.uid("fetch", uid.encode(), "(BODY.PEEK[])")
            if typ != "OK" or not fetched:
                raise RuntimeError(f"Mail UID {uid} nicht abrufbar")
            raw = _extract_bytes(fetched)
            if not raw:
                raise RuntimeError("Kein Body")
            msg = email.message_from_bytes(raw)
            return get_attachment_bytes(msg, part_id)

    def poll_new_messages(self, folder: str, last_uid: Optional[str]) -> List[str]:
        """
        Prüft ob neue Mails seit last_uid existieren.
        Gibt Liste neuer UIDs zurück (leer wenn keine neuen).
        """
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            if last_uid:
                criteria = f"UID {int(last_uid) + 1}:*"
            else:
                criteria = "UNSEEN"
            try:
                typ, data = self._conn.uid("search", None, criteria)
                if typ != "OK" or not data or not data[0]:
                    return []
                uids = data[0].split()
                # Filter: * bedeutet "ab last_uid" — IMAP gibt immer mind. 1 zurück
                if last_uid:
                    uids = [u for u in uids if int(u) > int(last_uid)]
                return [u.decode() for u in uids]
            except Exception:
                return []

    def bulk_set_flag(self, folder: str, uids: List[str], flag: str, value: bool) -> int:
        """
        Setzt/entfernt ein Flag für mehrere Mails gleichzeitig (eine IMAP-Anfrage).
        Gibt Anzahl der erfolgreich verarbeiteten Mails zurück.
        """
        if not uids:
            return 0
        uid_set = b",".join(u.encode() for u in uids)
        op = "+FLAGS" if value else "-FLAGS"
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            try:
                typ, _ = self._conn.uid("store", uid_set, op, flag)
                return len(uids) if typ == "OK" else 0
            except Exception:
                return 0

    def bulk_delete(self, folder: str, uids: List[str]) -> int:
        """Markiert mehrere Mails als gelöscht und expungiert."""
        if not uids:
            return 0
        uid_set = b",".join(u.encode() for u in uids)
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            try:
                typ, _ = self._conn.uid("store", uid_set, "+FLAGS", "\\Deleted")
                if typ != "OK":
                    return 0
                self._conn.expunge()
                self._last_folder = None
                return len(uids)
            except Exception:
                return 0

    def bulk_move(self, folder: str, uids: List[str], target: str) -> int:
        """Verschiebt mehrere Mails in einen anderen Ordner."""
        if not uids:
            return 0
        uid_set = b",".join(u.encode() for u in uids)
        with self._lock:
            self.reconnect_if_needed()
            self._select(folder)
            try:
                typ, _ = self._conn.uid("move", uid_set, target)
                if typ == "OK":
                    self._last_folder = None
                    return len(uids)
            except (imaplib.IMAP4.error, AttributeError):
                pass
            # Fallback: COPY + DELETE
            try:
                typ2, _ = self._conn.uid("copy", uid_set, target)
                if typ2 != "OK":
                    return 0
                self._conn.uid("store", uid_set, "+FLAGS", "\\Deleted")
                self._conn.expunge()
                self._last_folder = None
                return len(uids)
            except Exception:
                return 0

    def logout(self) -> None:
        try:
            if self._conn:
                self._conn.logout()
        except Exception:
            pass
        finally:
            self._conn = None


# ── IMAPSessionPool ─────────────────────────────────────────────────────────────

class IMAPSessionPool:
    """
    Verwaltet eine persistente IMAPSession pro Account.
    Thread-sicher: get() kann von mehreren Flask-Threads gleichzeitig aufgerufen werden.
    """

    def __init__(self):
        self._sessions: Dict[str, IMAPSession] = {}
        self._lock = threading.Lock()

    def init_from_config(self, accounts: List[Dict[str, Any]]) -> None:
        """Registriert alle Accounts aus der Config (lazy — keine Verbindung hier)."""
        with self._lock:
            for acc in accounts:
                name = acc.get("name", "")
                if name and name not in self._sessions:
                    self._sessions[name] = IMAPSession(acc)

    def get(self, account_name: str) -> IMAPSession:
        """Gibt Session zurück. Verbindet lazy beim ersten Zugriff."""
        with self._lock:
            session = self._sessions.get(account_name)
        if session is None:
            raise KeyError(f"Account '{account_name}' nicht konfiguriert")
        session.reconnect_if_needed()
        return session

    def get_all(self) -> List[IMAPSession]:
        with self._lock:
            return list(self._sessions.values())

    def account_names(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())

    def close_all(self) -> None:
        with self._lock:
            for session in self._sessions.values():
                session.logout()
            self._sessions.clear()


# Singleton — wird in web_ui.py beim Start initialisiert
pool = IMAPSessionPool()
