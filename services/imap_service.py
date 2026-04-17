#!/usr/bin/env python3
"""
IMAP helpers for Mail AI Sorter.
"""

import base64
import email as email_lib
import imaplib
import os
import re
import ssl
from typing import Any, Dict, List, Optional, Tuple

from services import inbox_service
from config_service import inject_account_secret


def connect(account: Dict[str, Any]):
    account = inject_account_secret(account)
    host = account.get("imap_host", "")
    port = int(account.get("imap_port", 993))
    username = account.get("username", "")
    password = account.get("password", "")
    encryption = str(account.get("imap_encryption", "ssl")).lower()
    timeout = int(account.get("imap_timeout_sec", 25))
    if not host:
        raise ValueError("IMAP-Host fehlt")
    if not username:
        raise ValueError("IMAP-Benutzername fehlt")
    if not password:
        raise ValueError("IMAP-Passwort fehlt")
    if encryption == "starttls":
        conn = imaplib.IMAP4(host, port, timeout=timeout)
        conn.starttls(ssl_context=ssl.create_default_context())
    else:
        conn = imaplib.IMAP4_SSL(
            host, port, timeout=timeout, ssl_context=ssl.create_default_context()
        )
    conn.login(username, password)
    return conn


def decode_header(value: Any) -> str:
    if not value:
        return ""
    parts = email_lib.header.decode_header(value)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(chunk))
    return "".join(out)


def parse_uid(data: List[Any]) -> Optional[str]:
    for item in data:
        if isinstance(item, tuple) and isinstance(item[0], bytes):
            match = re.search(rb"UID\s+(\d+)", item[0])
            if match:
                return match.group(1).decode()
    return None


def extract_envelope(raw_header: bytes) -> Dict[str, str]:
    msg = email_lib.message_from_bytes(raw_header)
    return {
        "subject": decode_header(msg.get("Subject", "")),
        "from": decode_header(msg.get("From", "")),
        "to": decode_header(msg.get("To", "")),
        "cc": decode_header(msg.get("Cc", "")),
        "date": msg.get("Date", ""),
        "message_id": msg.get("Message-ID", ""),
        "in_reply_to": msg.get("In-Reply-To", ""),
        "references": msg.get("References", ""),
        "list_unsubscribe": msg.get("List-Unsubscribe", ""),
    }


def parse_list_unsubscribe(header_value: str) -> List[str]:
    if not header_value:
        return []
    options = []
    for match in re.findall(r"<([^>]+)>", header_value):
        value = match.strip()
        if value:
            options.append(value)
    return options


def normalize_message_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.strip("<>").strip()


def extract_reference_ids(value: Any) -> List[str]:
    if not value:
        return []
    ids = []
    for match in re.findall(r"<([^>]+)>", str(value)):
        normalized = normalize_message_id(match)
        if normalized and normalized not in ids:
            ids.append(normalized)
    return ids


def search_header_ids(conn, header_name: str, message_id: str) -> List[bytes]:
    if not message_id:
        return []
    try:
        typ, data = conn.search("UTF-8", f'HEADER {header_name} "<{message_id}>"')
    except Exception:
        return []
    if typ != "OK" or not data or not data[0]:
        return []
    return data[0].split()


def fetch_thread_headers(
    conn,
    sequence_ids: List[bytes],
    account_name: str,
    folder: str,
    selected_uid: str,
) -> List[Dict[str, Any]]:
    if not sequence_ids:
        return []
    id_str = b",".join(sequence_ids)
    typ, fetched = conn.fetch(
        id_str,
        "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE MESSAGE-ID IN-REPLY-TO REFERENCES)])",
    )
    if typ != "OK" or not fetched:
        return []

    thread_items = []
    for item in fetched:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        header_bytes = item[1] if isinstance(item[1], bytes) else item[1].encode()
        flags_str = (
            item[0].decode(errors="replace")
            if isinstance(item[0], bytes)
            else str(item[0])
        )
        uid = parse_uid([item])
        if not uid:
            continue
        thread_items.append(
            inbox_service.normalize_mail_item(
                {
                    "uid": uid,
                    "account": account_name,
                    "folder": folder,
                    "seen": "\\Seen" in flags_str,
                    "flagged": "\\Flagged" in flags_str,
                    "is_selected": uid == str(selected_uid),
                    **extract_envelope(header_bytes),
                }
            )
        )
    return inbox_service.sort_mail_items(thread_items)


def build_thread_timeline(
    conn,
    account_name: str,
    folder: str,
    uid: str,
    envelope: Dict[str, Any],
    flags_str: str,
) -> List[Dict[str, Any]]:
    current_message_id = normalize_message_id(envelope.get("message_id"))
    related_ids = extract_reference_ids(envelope.get("references"))
    in_reply_to = normalize_message_id(envelope.get("in_reply_to"))
    if in_reply_to and in_reply_to not in related_ids:
        related_ids.append(in_reply_to)
    if current_message_id and current_message_id not in related_ids:
        related_ids.append(current_message_id)

    if not related_ids:
        return [
            inbox_service.normalize_mail_item(
                {
                    "uid": uid,
                    "account": account_name,
                    "folder": folder,
                    "seen": "\\Seen" in flags_str,
                    "flagged": "\\Flagged" in flags_str,
                    "is_selected": True,
                    **envelope,
                }
            )
        ]

    sequence_ids = []
    seen_sequence_ids = set()
    for message_id in related_ids:
        for header_name in ("Message-ID", "References", "In-Reply-To"):
            for sequence_id in search_header_ids(conn, header_name, message_id):
                if sequence_id in seen_sequence_ids:
                    continue
                seen_sequence_ids.add(sequence_id)
                sequence_ids.append(sequence_id)

    thread_items = fetch_thread_headers(
        conn, sequence_ids[:25], account_name, folder, uid
    )
    current_key = str(uid)
    if not any(item.get("uid") == current_key for item in thread_items):
        thread_items.append(
            inbox_service.normalize_mail_item(
                {
                    "uid": uid,
                    "account": account_name,
                    "folder": folder,
                    "seen": "\\Seen" in flags_str,
                    "flagged": "\\Flagged" in flags_str,
                    "is_selected": True,
                    **envelope,
                }
            )
        )
    return inbox_service.sort_mail_items(thread_items)


def list_folders(account: Dict[str, Any]) -> Dict[str, Any]:
    conn = connect(account)
    try:
        typ, data = conn.list()
        folders = []
        delimiter = "/"
        if typ == "OK" and data:
            for item in data:
                if not item:
                    continue
                text = item.decode(errors="replace")
                match = re.match(r'\(([^)]*)\)\s+"([^"]+)"\s+"?([^"]*)"?\s*$', text)
                if match:
                    flags_str, delimiter, name = (
                        match.group(1),
                        match.group(2),
                        match.group(3).strip('"').strip(),
                    )
                else:
                    parts = text.rsplit(' "/" ', 1)
                    if len(parts) > 1:
                        flags_str, name = parts[0].strip(), parts[-1].strip('"').strip()
                        delimiter = "/"
                    else:
                        continue
                if not name:
                    continue
                path_parts = name.split(delimiter) if delimiter else [name]
                folders.append(
                    {
                        "name": name,
                        "display": path_parts[-1] if len(path_parts) > 1 else name,
                        "delimiter": delimiter,
                        "depth": len(path_parts) - 1,
                        "flags": flags_str,
                        "parent": delimiter.join(path_parts[:-1])
                        if len(path_parts) > 1
                        else "",
                    }
                )

        unread = {}
        for folder in folders:
            try:
                status = conn.status(folder["name"], "(UNSEEN)")
                if status[0] == "OK" and status[1]:
                    value = (
                        status[1][0].decode(errors="replace")
                        if isinstance(status[1][0], bytes)
                        else str(status[1][0])
                    )
                    match = re.search(r"UNSEEN\s+(\d+)", value)
                    if match:
                        unread[folder["name"]] = int(match.group(1))
            except Exception:
                pass

        for folder in folders:
            folder["unread"] = unread.get(folder["name"], 0)
        return {"folders": folders, "delimiter": delimiter}
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def list_folder_emails(
    account: Dict[str, Any],
    folder: str,
    page: int,
    per_page: int,
) -> Tuple[List[Dict[str, Any]], int]:
    conn = connect(account)
    try:
        typ, _ = conn.select(folder, readonly=True)
        if typ != "OK":
            raise ValueError(f"Ordner {folder} nicht gefunden")

        typ, data = conn.search(None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return [], 0

        all_ids = data[0].split()
        total = len(all_ids)
        ordered_ids = list(reversed(all_ids))
        start = (page - 1) * per_page
        end = start + per_page
        page_ids = ordered_ids[start:end]
        if not page_ids:
            return [], total

        id_str = b",".join(page_ids)
        typ, fetched = conn.fetch(
            id_str,
            "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE MESSAGE-ID IN-REPLY-TO REFERENCES LIST-UNSUBSCRIBE)])",
        )
        emails = []
        if typ == "OK" and fetched:
            for item in fetched:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                header_bytes = (
                    item[1] if isinstance(item[1], bytes) else item[1].encode()
                )
                flags_str = (
                    item[0].decode(errors="replace")
                    if isinstance(item[0], bytes)
                    else str(item[0])
                )
                uid = parse_uid([item])
                if not uid:
                    continue
                emails.append(
                    {
                        "uid": uid,
                        "seen": "\\Seen" in flags_str,
                        "flagged": "\\Flagged" in flags_str,
                        "folder": folder,
                        "account": account["name"],
                        **extract_envelope(header_bytes),
                    }
                )
        return emails, total
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def list_unified_inbox(
    accounts: List[Dict[str, Any]], page: int, per_page: int
) -> Tuple[List[Dict[str, Any]], int]:
    emails = []
    for account in accounts:
        try:
            account_emails, _ = list_folder_emails(account, "INBOX", 1, per_page * page)
            emails.extend(account_emails)
        except Exception:
            pass
    emails = inbox_service.sort_mail_items(emails)
    total = len(emails)
    start = (page - 1) * per_page
    return emails[start : start + per_page], total


def get_email_detail(account: Dict[str, Any], folder: str, uid: str) -> Dict[str, Any]:
    conn = connect(account)
    try:
        typ, _ = conn.select(folder, readonly=True)
        if typ != "OK":
            raise ValueError(f"Ordner {folder} nicht gefunden")

        typ, data = conn.uid("fetch", uid, "(FLAGS BODY.PEEK[])")
        if typ != "OK" or not data:
            raise ValueError("Email nicht gefunden")

        raw_bytes = None
        flags_str = ""
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2:
                flags_str = (
                    item[0].decode(errors="replace")
                    if isinstance(item[0], bytes)
                    else str(item[0])
                )
                raw_bytes = item[1] if isinstance(item[1], bytes) else item[1].encode()

        if not raw_bytes:
            raise ValueError("Email-Inhalt leer")

        msg = email_lib.message_from_bytes(raw_bytes)
        envelope = extract_envelope(raw_bytes)
        body_text = ""
        body_html = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition") or "").lower()
                filename = part.get_filename()
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                if (
                    "attachment" in disp
                    or "inline" in disp
                    or (filename and ctype not in {"text/plain", "text/html"})
                ):
                    attachments.append(
                        {
                            "filename": decode_header(filename)
                            if filename
                            else "attachment",
                            "size": len(payload),
                            "content_type": ctype,
                            "data_b64": base64.b64encode(payload).decode("ascii"),
                        }
                    )
                elif ctype == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")
                elif ctype == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    body_html = payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                content = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    body_html = content
                else:
                    body_text = content

        try:
            thread = build_thread_timeline(
                conn,
                account["name"],
                folder,
                uid,
                envelope,
                flags_str,
            )
        except Exception:
            thread = [
                inbox_service.normalize_mail_item(
                    {
                        "uid": uid,
                        "account": account["name"],
                        "folder": folder,
                        "seen": "\\Seen" in flags_str,
                        "flagged": "\\Flagged" in flags_str,
                        "is_selected": True,
                        **envelope,
                    }
                )
            ]

        return {
            "uid": uid,
            "folder": folder,
            "account": account["name"],
            "seen": "\\Seen" in flags_str,
            "flagged": "\\Flagged" in flags_str,
            **envelope,
            "body_text": body_text,
            "body_html": body_html,
            "attachments": attachments,
            "unsubscribe_options": parse_list_unsubscribe(
                envelope.get("list_unsubscribe", "")
            ),
            "thread": thread,
        }
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def get_attachment(
    account: Dict[str, Any], folder: str, uid: str, att_index: int
) -> Dict[str, Any]:
    detail = get_email_detail(account, folder, uid)
    attachments = detail.get("attachments", [])
    if att_index >= len(attachments):
        raise ValueError("Anhang nicht gefunden")
    attachment = attachments[att_index]
    return {
        "filename": attachment["filename"],
        "content_type": attachment["content_type"],
        "data": base64.b64decode(attachment["data_b64"]),
    }


def set_flag(account: Dict[str, Any], folder: str, uid: str, action: str) -> None:
    conn = connect(account)
    try:
        conn.select(folder)
        if action == "flag":
            conn.uid("store", uid, "+FLAGS", "\\Flagged")
        elif action == "unflag":
            conn.uid("store", uid, "-FLAGS", "\\Flagged")
        elif action == "read":
            conn.uid("store", uid, "+FLAGS", "\\Seen")
        elif action == "unread":
            conn.uid("store", uid, "-FLAGS", "\\Seen")
        elif action == "delete":
            conn.uid("store", uid, "+FLAGS", "\\Deleted")
            conn.expunge()
        else:
            raise ValueError("Unbekannte Aktion")
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def bulk_update(
    account: Dict[str, Any],
    folder: str,
    uids: List[str],
    action: str,
    target_folder: Optional[str] = None,
) -> None:
    conn = connect(account)
    try:
        conn.select(folder)
        uid_set = ",".join(uids)
        if action == "read":
            conn.uid("store", uid_set, "+FLAGS", "\\Seen")
        elif action == "unread":
            conn.uid("store", uid_set, "-FLAGS", "\\Seen")
        elif action == "flag":
            conn.uid("store", uid_set, "+FLAGS", "\\Flagged")
        elif action == "unflag":
            conn.uid("store", uid_set, "-FLAGS", "\\Flagged")
        elif action == "delete":
            conn.uid("store", uid_set, "+FLAGS", "\\Deleted")
            conn.expunge()
        elif action == "move":
            if not target_folder:
                raise ValueError("Zielordner fehlt")
            conn.uid("COPY", uid_set, target_folder)
            conn.uid("store", uid_set, "+FLAGS", "\\Deleted")
            conn.expunge()
        else:
            raise ValueError("Unbekannte Aktion")
    finally:
        try:
            conn.logout()
        except Exception:
            pass
