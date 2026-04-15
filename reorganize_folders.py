#!/usr/bin/env python3
import argparse
import imaplib
import json
import os
import re
import ssl
from typing import Any, Dict, List, Optional, Tuple

SYSTEM_FOLDERS = {
    "INBOX",
    "Sent",
    "Sent Messages",
    "Gesendet",
    "Gesendete Elemente",
    "Drafts",
    "Entwürfe",
    "Trash",
    "Deleted Messages",
    "Papierkorb",
    "Junk",
    "Spam",
    "Spamverdacht",
    "Archive",
    "All Mail",
    "Outbox",
    "OUTBOX",
    "SendLater",
}

TARGET_BY_CATEGORY = {
    "paperless": "Paperless",
    "apple": "Apple",
    "finanzen": "Finanzen",
    "vertraege": "Vertraege",
    "einkauf": "Einkauf",
    "reisen": "Reisen",
    "arbeit": "Arbeit",
    "behoerden": "Behoerden",
    "newsletter": "Newsletter",
    "privat": "Privat",
}


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_list_name(raw_line: bytes) -> Optional[str]:
    s = raw_line.decode("utf-8", errors="replace")
    # Prefer last quoted part as folder name.
    m = re.findall(r'"([^\"]*)"\s*$', s)
    if m:
        return m[-1]
    # Fallback: try trailing token
    parts = s.split(" ")
    if parts:
        return parts[-1].strip('"')
    return None


def imap_quote(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def classify_by_folder_name(folder: str) -> str:
    f = folder.lower()
    if any(x in f for x in ["apple", "icloud"]):
        return "apple"
    if any(x in f for x in ["rechnung", "steuer", "beleg", "paperless", "versicherung", "vertrag"]):
        return "paperless"
    if any(x in f for x in ["sparkasse", "bank", "paypal", "crypto", "finanz"]):
        return "finanzen"
    if any(x in f for x in ["telekom", "o2", "check24", "vertrag", "tarif"]):
        return "vertraege"
    if any(x in f for x in ["amazon", "bestellung", "dhl", "paket", "produktkey", "shop"]):
        return "einkauf"
    if any(x in f for x in ["reise", "flug", "bahn", "hotel", "booking", "israel"]):
        return "reisen"
    if any(x in f for x in ["arbeit", "fortbildung", "server", "fernuni", "uni", "job"]):
        return "arbeit"
    if any(x in f for x in ["grüne", "gruene", "behörd", "behoerd", "amt", "kritik"]):
        return "behoerden"
    if any(x in f for x in ["newsletter", "marketing", "cold", "fyi", "notification", "meeting update"]):
        return "newsletter"
    return "privat"


def is_system_or_protected(folder: str, target_folders: List[str]) -> bool:
    if folder in target_folders:
        return True
    if folder in SYSTEM_FOLDERS:
        return True
    if folder.startswith("[") or folder.startswith("/"):
        return True
    # Keep provider internals / virtual folders safe.
    if folder.lower().startswith("orphanedaccount"):
        return True
    return False


def chunked(seq: List[bytes], size: int) -> List[List[bytes]]:
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def move_all_messages(conn: imaplib.IMAP4_SSL, src: str, dst: str, dry_run: bool) -> Tuple[int, int]:
    typ, _ = conn.select(imap_quote(src))
    if typ != "OK":
        return (0, 0)
    typ, data = conn.search(None, "ALL")
    if typ != "OK" or not data or not data[0]:
        return (0, 0)

    ids = data[0].split()
    total = len(ids)
    moved = 0
    if dry_run:
        return (total, total)

    for batch in chunked(ids, 200):
        id_str = b",".join(batch)
        ctyp, _ = conn.copy(id_str, imap_quote(dst))
        if ctyp == "OK":
            conn.store(id_str, "+FLAGS", "\\Deleted")
            moved += len(batch)
    conn.expunge()
    return (total, moved)


def main() -> int:
    ap = argparse.ArgumentParser(description="Consolidate legacy IMAP folders into 10 target folders and delete legacy folders")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--account", default="", help="Only process account name (exact match)")
    ap.add_argument("--delete-after-move", action="store_true", help="Delete legacy folder after successful move")
    args = ap.parse_args()

    cfg = load_config(args.config)
    accounts = cfg.get("accounts", [])

    for acc in accounts:
        name = acc["name"]
        if args.account and name != args.account:
            continue
        host = acc["imap_host"]
        port = int(acc.get("imap_port", 993))
        imap_encryption = str(acc.get("imap_encryption", "ssl")).lower()
        imap_timeout_sec = int(acc.get("imap_timeout_sec", cfg.get("global", {}).get("imap_timeout_sec", 25)))
        user = acc["username"]
        pw = acc.get("password") or os.getenv(acc.get("password_env", ""))
        if not pw:
            print(f"[{name}] ERROR missing env: {acc.get('password_env')}")
            continue

        target_folders = sorted(set(acc.get("target_folders", {}).values()))

        print(f"[{name}] connect {host}:{port} ({imap_encryption}) as {user}")
        if imap_encryption == "starttls":
            conn = imaplib.IMAP4(host, port, timeout=imap_timeout_sec)
            conn.starttls(ssl_context=ssl.create_default_context())
        else:
            conn = imaplib.IMAP4_SSL(host, port, timeout=imap_timeout_sec, ssl_context=ssl.create_default_context())
        try:
            conn.login(user, pw)

            # Ensure targets exist
            for tf in target_folders:
                conn.create(imap_quote(tf))

            typ, boxes = conn.list()
            if typ != "OK" or boxes is None:
                print(f"[{name}] WARN cannot list folders")
                continue

            folder_names: List[str] = []
            for b in boxes:
                if not isinstance(b, (bytes, bytearray)):
                    continue
                fn = parse_list_name(bytes(b))
                if fn:
                    folder_names.append(fn)

            legacy = [f for f in folder_names if not is_system_or_protected(f, target_folders)]
            if not legacy:
                print(f"[{name}] no legacy folders to consolidate")
                continue

            for src in legacy:
                cat = classify_by_folder_name(src)
                dst = TARGET_BY_CATEGORY.get(cat, "Privat")
                total, moved = move_all_messages(conn, src, dst, args.dry_run)
                print(f"[{name}] {src} -> {dst} | total={total} moved={moved}")

                if args.dry_run or not args.delete_after_move:
                    continue

                # Delete source folder if possible after move.
                try:
                    conn.select(imap_quote("INBOX"))
                    dtyp, ddata = conn.delete(imap_quote(src))
                    if dtyp == "OK":
                        print(f"[{name}] deleted folder: {src}")
                    else:
                        msg = ddata[0].decode(errors="ignore") if ddata and ddata[0] else ""
                        print(f"[{name}] keep folder (delete failed): {src} | {dtyp} {msg}")
                except Exception as e:
                    print(f"[{name}] keep folder (exception): {src} | {e}")

        except Exception as e:
            print(f"[{name}] ERROR {e}")
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
