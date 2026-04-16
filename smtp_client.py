#!/usr/bin/env python3
"""
SMTP Client for Mail AI Sorter.
Sends emails via SMTP with SSL/STARTTLS support.
Saves sent mails to IMAP Sent folder.
"""

import email as email_lib
import email.generator
import email.mime.application
import email.mime.base
import email.mime.multipart
import email.mime.text
import email.utils
import imaplib
import io
import os
import smtplib
import ssl
import time
from email.header import Header
from typing import Any, Dict, List, Optional


SMTP_PRESETS = {
    "gmail.com": {"host": "smtp.gmail.com", "port": 587, "encryption": "starttls"},
    "icloud.com": {"host": "smtp.mail.me.com", "port": 587, "encryption": "starttls"},
    "me.com": {"host": "smtp.mail.me.com", "port": 587, "encryption": "starttls"},
    "outlook.com": {
        "host": "smtp.office365.com",
        "port": 587,
        "encryption": "starttls",
    },
    "hotmail.com": {
        "host": "smtp.office365.com",
        "port": 587,
        "encryption": "starttls",
    },
    "live.com": {"host": "smtp.office365.com", "port": 587, "encryption": "starttls"},
    "yahoo.com": {"host": "smtp.mail.yahoo.com", "port": 465, "encryption": "ssl"},
    "yahoo.de": {"host": "smtp.mail.yahoo.com", "port": 465, "encryption": "ssl"},
    "gmx.net": {"host": "mail.gmx.net", "port": 587, "encryption": "starttls"},
    "gmx.de": {"host": "mail.gmx.net", "port": 587, "encryption": "starttls"},
    "gmx.com": {"host": "mail.gmx.net", "port": 587, "encryption": "starttls"},
    "web.de": {"host": "smtp.web.de", "port": 587, "encryption": "starttls"},
    "t-online.de": {"host": "securesmtp.t-online.de", "port": 465, "encryption": "ssl"},
    "freenet.de": {"host": "mx.freenet.de", "port": 587, "encryption": "starttls"},
    "1und1.de": {"host": "smtp.1und1.de", "port": 587, "encryption": "starttls"},
    "ionos.de": {"host": "smtp.ionos.de", "port": 587, "encryption": "starttls"},
    "mailbox.org": {"host": "smtp.mailbox.org", "port": 465, "encryption": "ssl"},
    "posteo.de": {"host": "posteo.de", "port": 587, "encryption": "starttls"},
}


def get_smtp_preset(username: str) -> Optional[Dict[str, Any]]:
    domain = username.lower().split("@")[-1] if "@" in username else ""
    return SMTP_PRESETS.get(domain)


def build_smtp_config(account: Dict[str, Any]) -> Dict[str, Any]:
    preset = get_smtp_preset(account.get("username", ""))
    return {
        "host": account.get("smtp_host", preset["host"] if preset else ""),
        "port": int(account.get("smtp_port", preset["port"] if preset else 587)),
        "encryption": account.get(
            "smtp_encryption", preset["encryption"] if preset else "starttls"
        ),
        "username": account["username"],
        "password": account.get("password")
        or os.getenv(account.get("password_env", ""), ""),
        "from_name": account.get("from_name", ""),
    }


def _create_smtp_connection(cfg: Dict[str, Any], timeout: int = 30) -> smtplib.SMTP:
    host = cfg["host"]
    port = cfg["port"]
    encryption = cfg.get("encryption", "starttls").lower()
    ctx = ssl.create_default_context()

    if encryption == "ssl":
        conn = smtplib.SMTP_SSL(host, port, context=ctx, timeout=timeout)
    else:
        conn = smtplib.SMTP(host, port, timeout=timeout)
        conn.ehlo()
        if encryption == "starttls":
            conn.starttls(context=ctx)
            conn.ehlo()
    return conn


def test_smtp_connection(account: Dict[str, Any]) -> Dict[str, Any]:
    cfg = build_smtp_config(account)
    if not cfg["host"]:
        return {
            "success": False,
            "error": "Kein SMTP-Server konfiguriert. smtp_host in config.json setzen.",
        }
    if not cfg["password"]:
        return {"success": False, "error": "Passwort fehlt."}
    try:
        conn = _create_smtp_connection(cfg)
        conn.login(cfg["username"], cfg["password"])
        conn.quit()
        return {"success": True, "host": cfg["host"], "port": cfg["port"]}
    except smtplib.SMTPAuthenticationError as e:
        return {"success": False, "error": f"Authentifizierung fehlgeschlagen: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def build_message(
    from_addr: str,
    from_name: str,
    to: List[str],
    cc: List[str],
    bcc: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    reply_to: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    has_attachments = attachments and len(attachments) > 0
    has_html = bool(body_html and body_html.strip())

    if has_attachments:
        msg = email.mime.multipart.MIMEMultipart("mixed")
        alt = email.mime.multipart.MIMEMultipart("alternative")
        alt.attach(email.mime.text.MIMEText(body_text, "plain", "utf-8"))
        if has_html:
            alt.attach(email.mime.text.MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt)
        for att in attachments:
            part = email.mime.base.MIMEBase("application", "octet-stream")
            part.set_payload(att["data"])
            email_lib.encoders.encode_base64(part)
            filename = att.get("filename", "attachment")
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)
    elif has_html:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg.attach(email.mime.text.MIMEText(body_text, "plain", "utf-8"))
        msg.attach(email.mime.text.MIMEText(body_html, "html", "utf-8"))
    else:
        msg = email.mime.text.MIMEText(body_text, "plain", "utf-8")

    from_header = f"{from_name} <{from_addr}>" if from_name else from_addr
    msg["From"] = from_header
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = reply_to
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    msg["Subject"] = Header(subject, "utf-8")
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid()
    msg["MIME-Version"] = "1.0"
    msg["User-Agent"] = "Mail-AI-Sorter/1.0"

    buf = io.BytesIO()
    email.generator.BytesGenerator(buf, mangle_from_=False).flatten(msg)
    return buf.getvalue()


def send_email(
    account: Dict[str, Any],
    to: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    cfg = build_smtp_config(account)
    if not cfg["host"]:
        return {"success": False, "error": "Kein SMTP-Server konfiguriert."}
    if not cfg["password"]:
        return {"success": False, "error": "Passwort fehlt."}

    cc = cc or []
    bcc = bcc or []
    all_recipients = to + cc + bcc

    raw = build_message(
        from_addr=cfg["username"],
        from_name=cfg["from_name"],
        to=to,
        cc=cc,
        bcc=bcc,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        reply_to=reply_to,
        in_reply_to=in_reply_to,
        references=references,
        attachments=attachments,
    )

    try:
        conn = _create_smtp_connection(cfg)
        conn.login(cfg["username"], cfg["password"])
        conn.sendmail(cfg["username"], all_recipients, raw)
        conn.quit()
    except smtplib.SMTPRecipientsRefused as e:
        return {"success": False, "error": f"Empfänger abgelehnt: {e}"}
    except smtplib.SMTPAuthenticationError as e:
        return {"success": False, "error": f"Authentifizierung fehlgeschlagen: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

    _save_to_sent(account, raw)

    return {
        "success": True,
        "message_id": email_lib.message_from_bytes(raw)["Message-ID"],
    }


def _save_to_sent(account: Dict[str, Any], raw_msg: bytes) -> bool:
    try:
        imap_host = account["imap_host"]
        imap_port = int(account.get("imap_port", 993))
        imap_encryption = str(account.get("imap_encryption", "ssl")).lower()
        username = account["username"]
        pw = account.get("password") or os.getenv(account.get("password_env", ""), "")
        if not pw:
            return False

        if imap_encryption == "starttls":
            conn = imaplib.IMAP4(imap_host, imap_port, timeout=30)
            conn.starttls(ssl_context=ssl.create_default_context())
        else:
            conn = imaplib.IMAP4_SSL(
                imap_host, imap_port, ssl_context=ssl.create_default_context()
            )
        conn.login(username, pw)

        sent_folder = None
        for candidate in [
            "Sent",
            "INBOX.Sent",
            "INBOX/sent",
            "Sent Messages",
            "Gesendet",
        ]:
            typ, _ = conn.select(candidate)
            if typ == "OK":
                sent_folder = candidate
                break

        if sent_folder is None:
            conn.create("Sent")
            sent_folder = "Sent"

        conn.append(sent_folder, None, imaplib.Time2Internaldate(time.time()), raw_msg)
        conn.logout()
        return True
    except Exception:
        return False
