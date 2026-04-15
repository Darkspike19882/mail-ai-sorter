#!/usr/bin/env python3
import argparse
import imaplib
import json
import os
import re
import ssl
from typing import Any, Dict, List, Optional

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


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_list_entry(raw_line: bytes) -> Optional[Dict[str, Any]]:
    s = raw_line.decode("utf-8", errors="replace")
    upper = s.upper()
    noselect = "\\NOSELECT" in upper
    m = re.findall(r'"([^\"]*)"\s*$', s)
    if m:
        return {"name": m[-1], "noselect": noselect}
    parts = s.split(" ")
    if parts:
        return {"name": parts[-1].strip('"'), "noselect": noselect}
    return None


def imap_quote(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def is_protected(folder: str, target_folders: List[str]) -> bool:
    if folder in target_folders:
        return True
    if folder in SYSTEM_FOLDERS:
        return True
    if folder.startswith("[") or folder.startswith("/"):
        return True
    if folder.lower().startswith("orphanedaccount"):
        return True
    return False


def parse_status_messages(data: Any) -> Optional[int]:
    if not data:
        return None
    raw = data[0]
    if isinstance(raw, bytes):
        s = raw.decode("utf-8", errors="replace")
    else:
        s = str(raw)
    m = re.search(r"MESSAGES\s+(\d+)", s, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def folder_count(conn: imaplib.IMAP4, folder: str) -> Optional[int]:
    # STATUS is less invasive and works better across providers for bulk scans.
    try:
        typ, data = conn.status(imap_quote(folder), "(MESSAGES)")
        if typ == "OK":
            parsed = parse_status_messages(data)
            if parsed is not None:
                return parsed
    except Exception:
        pass

    # Fallback to SELECT/SEARCH if STATUS is unsupported.
    try:
        typ, _ = conn.select(imap_quote(folder))
        if typ != "OK":
            return None
        typ, data = conn.search(None, "ALL")
        if typ != "OK" or not data or data[0] is None:
            return None
        return len(data[0].split()) if data[0] else 0
    except Exception:
        return None


def connect_account(acc: Dict[str, Any], global_cfg: Dict[str, Any]) -> imaplib.IMAP4:
    host = acc["imap_host"]
    port = int(acc.get("imap_port", 993))
    enc = str(acc.get("imap_encryption", "ssl")).lower()
    timeout = int(acc.get("imap_timeout_sec", global_cfg.get("imap_timeout_sec", 25)))
    if enc == "starttls":
        conn = imaplib.IMAP4(host, port, timeout=timeout)
        conn.starttls(ssl_context=ssl.create_default_context())
        return conn
    return imaplib.IMAP4_SSL(host, port, timeout=timeout, ssl_context=ssl.create_default_context())


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan all folders and delete empty legacy folders")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    global_cfg = cfg.get("global", {})

    for acc in cfg.get("accounts", []):
        name = acc["name"]
        user = acc["username"]
        pw = acc.get("password") or os.getenv(acc.get("password_env", ""))
        if not pw:
            print(f"[{name}] ERROR missing env: {acc.get('password_env')}")
            continue

        target_folders = sorted(set(acc.get("target_folders", {}).values()))

        print(f"\n[{name}] scanning folders as {user}")
        conn = connect_account(acc, global_cfg)
        try:
            conn.login(user, pw)
            typ, boxes = conn.list()
            if typ != "OK" or boxes is None:
                print(f"[{name}] ERROR list failed")
                continue

            entries: List[Dict[str, Any]] = []
            for row in boxes:
                if isinstance(row, (bytes, bytearray)):
                    parsed = parse_list_entry(bytes(row))
                    if parsed and parsed.get("name"):
                        entries.append(parsed)

            # Inspect all folders
            report = []
            for ent in entries:
                folder = str(ent["name"])
                if ent.get("noselect"):
                    report.append((folder, None))
                    continue
                cnt = folder_count(conn, folder)
                report.append((folder, cnt))

            report.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else 10**9, x[0].lower()))
            print(f"[{name}] folders total={len(report)}")
            for folder, cnt in report:
                c = "ERR" if cnt is None else str(cnt)
                print(f"[{name}] count {c:>4} | {folder}")

            # Delete only empty, non-protected folders
            to_delete = [f for f, cnt in report if cnt == 0 and not is_protected(f, target_folders)]
            print(f"[{name}] empty legacy folders to delete={len(to_delete)}")

            for folder in to_delete:
                if args.dry_run:
                    print(f"[{name}] DRY-RUN delete {folder}")
                    continue
                try:
                    conn.select(imap_quote("INBOX"))
                    dtyp, ddata = conn.delete(imap_quote(folder))
                    msg = ddata[0].decode(errors="ignore") if ddata and ddata[0] else ""
                    print(f"[{name}] delete {folder}: {dtyp} {msg}".strip())
                except Exception as e:
                    print(f"[{name}] delete {folder}: ERROR {e}")

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
