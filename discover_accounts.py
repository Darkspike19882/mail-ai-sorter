#!/usr/bin/env python3
import argparse
import json
import plistlib
import urllib.parse
from pathlib import Path


def guess_imap_host(email_addr: str) -> str:
    domain = email_addr.split("@")[-1].lower()
    if domain in {"gmail.com", "googlemail.com"}:
        return "imap.gmail.com"
    if domain in {"gmx.de", "gmx.net", "gmx.com"}:
        return "imap.gmx.net"
    if domain in {"web.de"}:
        return "imap.web.de"
    if domain in {"icloud.com", "me.com", "mac.com"}:
        return "imap.mail.me.com"
    if domain == "outlook.com" or domain.endswith("outlook.com") or domain in {"hotmail.com", "live.com"}:
        return "outlook.office365.com"
    return f"imap.{domain}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts-map", default=str(Path.home() / "Library/Mail/V10/MailData/Signatures/AccountsMap.plist"))
    ap.add_argument("--config-template", default="config.example.json")
    ap.add_argument("--output", default="config.json")
    args = ap.parse_args()

    with open(args.config_template, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    with open(args.accounts_map, "rb") as f:
        amap = plistlib.load(f)

    accounts = []
    for _, item in amap.items():
        account_url = item.get("AccountURL", "")
        parsed = urllib.parse.urlparse(account_url)
        username = urllib.parse.unquote(parsed.netloc)
        if not username or "@" not in username:
            continue

        local_part, domain = username.split("@", 1)
        env_name = (
            "MAIL_"
            + local_part.upper().replace(".", "_")
            + "_"
            + domain.upper().replace(".", "_")
            + "_PASS"
        )
        accounts.append(
            {
                "name": username,
                "imap_host": guess_imap_host(username),
                "imap_port": 993,
                "username": username,
                "password_env": env_name,
                "source_folder": "INBOX",
                "target_folders": {
                    "paperless": "Paperless",
                    "apple": "Apple",
                    "finanzen": "Finanzen",
                    "vertraege": "Vertraege",
                    "einkauf": "Einkauf",
                    "reisen": "Reisen",
                    "arbeit": "Arbeit",
                    "behoerden": "Behoerden",
                    "newsletter": "Newsletter",
                    "privat": "Privat"
                },
                "rules": [
                    {
                        "if_from_contains": ["email.apple.com", "apple.com"],
                        "move_to": "apple"
                    },
                    {
                        "if_subject_contains": ["Rechnung", "Beleg", "Invoice", "Receipt", "Lastschrift", "SEPA", "Kontoauszug"],
                        "move_to": "paperless"
                    }
                ]
            }
        )

    cfg["accounts"] = accounts

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.output} with {len(accounts)} account(s).")
    for a in accounts:
        print(f"- {a['username']} -> env {a['password_env']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
