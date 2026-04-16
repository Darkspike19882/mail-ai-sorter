#!/usr/bin/env python3
"""
SMTP-Client — Mails senden, antworten und weiterleiten.
Verwendet nur Python-Stdlib (smtplib, email.*) — kein neuer Dependency.
"""

import os
import smtplib
import ssl
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate, formataddr, parseaddr
from typing import Any, Dict, List, Optional


class SMTPClient:
    """
    Thread-sicher: jeder Send-Call öffnet eine neue SMTP-Verbindung und
    schließt sie danach wieder — kein persistent state.
    """

    def __init__(self, account_cfg: Dict[str, Any]):
        self._cfg = account_cfg

    @property
    def _host(self) -> str:
        return self._cfg.get("smtp_host", "")

    @property
    def _port(self) -> int:
        return int(self._cfg.get("smtp_port", 587))

    @property
    def _encryption(self) -> str:
        return str(self._cfg.get("smtp_encryption", "starttls")).lower()

    @property
    def _username(self) -> str:
        return self._cfg.get("username", "")

    @property
    def _password(self) -> str:
        pw = self._cfg.get("smtp_password") or os.getenv(
            self._cfg.get("smtp_password_env", ""), ""
        )
        if not pw:
            # Fallback: IMAP-Passwort verwenden wenn dasselbe
            pw = self._cfg.get("password") or os.getenv(
                self._cfg.get("password_env", ""), ""
            )
        return pw

    @property
    def _from_name(self) -> str:
        return self._cfg.get("from_name", "")

    @property
    def _from_addr(self) -> str:
        return self._cfg.get("username", "")

    def _connect(self) -> smtplib.SMTP:
        """Öffnet eine SMTP-Verbindung und gibt sie zurück."""
        if not self._host:
            raise RuntimeError("smtp_host nicht konfiguriert")
        if not self._password:
            raise RuntimeError(
                f"SMTP-Passwort fehlt (smtp_password_env nicht gesetzt)"
            )

        if self._encryption == "ssl":
            ctx = ssl.create_default_context()
            server = smtplib.SMTP_SSL(self._host, self._port, context=ctx, timeout=30)
        else:
            server = smtplib.SMTP(self._host, self._port, timeout=30)
            server.ehlo()
            if self._encryption == "starttls":
                server.starttls(context=ssl.create_default_context())
                server.ehlo()

        server.login(self._username, self._password)
        return server

    def _build_message(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> MIMEMultipart:
        """Baut eine vollständige MIME-Nachricht zusammen."""
        msg = MIMEMultipart("mixed")

        # Absender mit optionalem Anzeige-Namen
        if self._from_name:
            msg["From"] = formataddr((self._from_name, self._from_addr))
        else:
            msg["From"] = self._from_addr

        msg["To"]      = ", ".join(to)
        msg["Subject"] = str(Header(subject, "utf-8"))
        msg["Date"]    = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        if cc:
            msg["Cc"] = ", ".join(cc)

        # Thread-Header für korrekte Einordnung in Mail-Clients
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        elif in_reply_to:
            msg["References"] = in_reply_to

        # Body: text/plain und optional text/html
        if body_html:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(body_text, "plain", "utf-8"))
            alt.attach(MIMEText(body_html,  "html",  "utf-8"))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

        # Anhänge
        for att in (attachments or []):
            part = MIMEBase("application", "octet-stream")
            part.set_payload(att["data"])
            encoders.encode_base64(part)
            filename = att.get("filename", "anhang")
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=str(Header(filename, "utf-8")),
            )
            msg.attach(part)

        return msg

    def send(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Sendet eine Mail. Gibt die Message-ID zurück.
        Raises: RuntimeError bei Verbindungs- oder Auth-Fehler.
        """
        msg = self._build_message(
            to=to, subject=subject, body_text=body_text, body_html=body_html,
            cc=cc, bcc=bcc, in_reply_to=in_reply_to, references=references,
            attachments=attachments,
        )
        all_recipients = list(to) + (cc or []) + (bcc or [])

        server = self._connect()
        try:
            server.sendmail(self._from_addr, all_recipients, msg.as_bytes())
        finally:
            try:
                server.quit()
            except Exception:
                pass

        return msg["Message-ID"]

    def build_reply(
        self,
        original: Dict[str, Any],
        reply_text: str,
        reply_html: Optional[str] = None,
        reply_all: bool = False,
    ) -> Dict[str, Any]:
        """
        Bereitet die Parameter für eine Antwort vor.
        Gibt ein Dict zurück das direkt an send() übergeben werden kann.
        """
        # Betreff: "Re: Original-Betreff" (nur einmal "Re:" voranstellen)
        orig_subj = original.get("subject", "")
        if not orig_subj.lower().startswith("re:"):
            subject = f"Re: {orig_subj}"
        else:
            subject = orig_subj

        # Empfänger
        orig_from = original.get("from_addr", "")
        _, reply_to_addr = parseaddr(orig_from)
        to = [reply_to_addr] if reply_to_addr else [orig_from]

        cc: List[str] = []
        if reply_all:
            # Alle original-Empfänger außer uns selbst hinzufügen
            for header in ["to", "cc"]:
                val = original.get(header, "")
                if val:
                    for addr_str in val.split(","):
                        _, addr = parseaddr(addr_str.strip())
                        if addr and addr.lower() != self._from_addr.lower() and addr not in to:
                            cc.append(addr)

        # Thread-Header
        in_reply_to = original.get("message_id", "")
        references_orig = original.get("references", "")
        if references_orig and in_reply_to:
            references = f"{references_orig} {in_reply_to}".strip()
        else:
            references = in_reply_to

        # Zitatblock anhängen
        orig_date = original.get("date_iso", "")[:10] if original.get("date_iso") else ""
        quote_header = f"\n\nAm {orig_date} schrieb {orig_from}:\n"
        quoted_body = "\n".join(
            f"> {line}"
            for line in (original.get("body_text") or "").splitlines()[:30]
        )
        full_body = reply_text + quote_header + quoted_body

        return {
            "to":          to,
            "subject":     subject,
            "body_text":   full_body,
            "body_html":   reply_html,
            "cc":          cc or None,
            "in_reply_to": in_reply_to,
            "references":  references,
        }

    def build_forward(
        self,
        original: Dict[str, Any],
        to: List[str],
        body_prefix: str = "",
    ) -> Dict[str, Any]:
        """
        Bereitet die Parameter für eine Weiterleitung vor.
        """
        orig_subj = original.get("subject", "")
        if not orig_subj.lower().startswith("fwd:") and not orig_subj.lower().startswith("wg:"):
            subject = f"WG: {orig_subj}"
        else:
            subject = orig_subj

        orig_date = original.get("date_iso", "")[:10] if original.get("date_iso") else ""
        fwd_header = (
            f"\n\n---------- Weitergeleitete Nachricht ----------\n"
            f"Von: {original.get('from_addr', '')}\n"
            f"Datum: {orig_date}\n"
            f"Betreff: {original.get('subject', '')}\n"
            f"An: {original.get('to', '')}\n\n"
        )
        body = (body_prefix or "") + fwd_header + (original.get("body_text") or "")

        return {
            "to":        to,
            "subject":   subject,
            "body_text": body,
        }
