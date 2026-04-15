#!/usr/bin/env python3
import argparse
import imaplib
import json
import os
import ssl
from typing import Dict, Any


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_folder(conn: imaplib.IMAP4_SSL, folder: str) -> str:
    typ, data = conn.create(folder)
    if typ == "OK":
        return "created"
    msg = (data[0].decode(errors="ignore") if data and data[0] else "")
    if "already exists" in msg.lower() or "exists" in msg.lower() or typ == "NO":
        return "exists"
    return f"{typ}: {msg}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Create target IMAP folders for all configured accounts")
    ap.add_argument("--config", default="config.json")
    args = ap.parse_args()

    cfg = load_config(args.config)
    for acc in cfg.get("accounts", []):
        name = acc["name"]
        host = acc["imap_host"]
        port = int(acc.get("imap_port", 993))
        imap_encryption = str(acc.get("imap_encryption", "ssl")).lower()
        imap_timeout_sec = int(acc.get("imap_timeout_sec", cfg.get("global", {}).get("imap_timeout_sec", 25)))
        user = acc["username"]
        pw = acc.get("password") or os.getenv(acc.get("password_env", ""))
        if not pw:
            print(f"[{name}] ERROR missing env: {acc.get('password_env')}")
            continue

        print(f"[{name}] connect {host}:{port} ({imap_encryption}) as {user}")
        if imap_encryption == "starttls":
            conn = imaplib.IMAP4(host, port, timeout=imap_timeout_sec)
            conn.starttls(ssl_context=ssl.create_default_context())
        else:
            conn = imaplib.IMAP4_SSL(host, port, timeout=imap_timeout_sec, ssl_context=ssl.create_default_context())
        try:
            conn.login(user, pw)
            for folder in sorted(set(acc.get("target_folders", {}).values())):
                status = create_folder(conn, folder)
                print(f"[{name}] {folder}: {status}")
            # Optional: ensure folder list refresh
            conn.list()
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
