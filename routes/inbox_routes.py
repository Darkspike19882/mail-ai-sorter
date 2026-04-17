import base64
import concurrent.futures
from pathlib import Path

from flask import Blueprint, jsonify, request

import memory
from config_service import get_account, inject_account_secret, load_config
from services import imap_service, inbox_service


inbox_bp = Blueprint("inbox_routes", __name__)
INDEX_DB = Path(__file__).resolve().parent.parent / "mail_index.db"


def _json_error(message: str, status: int = 400, **extra):
    return jsonify({"success": False, "error": message, **extra}), status


def _safe_int(val, default=1):
    try:
        return max(1, int(val))
    except (ValueError, TypeError):
        return default


def _fetch_account_inbox(acc, per_page, page):
    try:
        emails, total = imap_service.list_folder_emails(
            acc, "INBOX", 1, per_page * page
        )
        return {
            "account": acc.get("name", ""),
            "emails": inbox_service.decorate_emails(emails),
            "total": total,
            "error": None,
        }
    except Exception as exc:
        return {
            "account": acc.get("name", ""),
            "emails": [],
            "total": 0,
            "error": str(exc),
        }


@inbox_bp.route("/api/tags")
def api_tags():
    return jsonify(memory.get_all_tags())


@inbox_bp.route("/api/tags", methods=["POST"])
def api_save_tag():
    data = request.json or {}
    msg_uid = data.get("msg_uid")
    account = data.get("account")
    folder = data.get("folder")
    tag = data.get("tag")
    if not all([msg_uid, account, folder, tag]):
        return jsonify({"success": False, "error": "Fehlende Daten"}), 400
    memory.add_tag(msg_uid, account, folder, tag)
    return jsonify({"success": True})


@inbox_bp.route("/api/tags/<msg_uid>/<account_name>/<folder>", methods=["DELETE"])
def api_delete_tag(msg_uid, account_name, folder):
    tag = request.args.get("tag")
    if not tag:
        return jsonify({"success": False, "error": "Tag fehlt"}), 400
    memory.remove_tag(msg_uid, account_name, folder, tag)
    return jsonify({"success": True})


@inbox_bp.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    category = request.args.get("category", "")
    account = request.args.get("account", "")
    folder = request.args.get("folder", "")
    since = request.args.get("since", "")
    before = request.args.get("before", "")
    try:
        import sqlite3

        conn = sqlite3.connect(str(INDEX_DB))
        if query:
            sql = """
                SELECT e.id, e.msg_uid, e.account, e.folder, e.from_addr, e.subject,
                       e.date_iso, e.category, e.keywords,
                       snippet(emails_fts, 3, '[', ']', '...', 12) AS match_snippet
                FROM emails_fts
                JOIN emails e ON e.id = emails_fts.rowid
                WHERE emails_fts MATCH ?
            """
            params = [query]
        else:
            sql = """
                SELECT id, msg_uid, account, folder, from_addr, subject,
                       date_iso, category, keywords, snippet AS match_snippet
                FROM emails
                WHERE 1=1
            """
            params = []

        if category:
            sql += " AND e.category = ?" if query else " AND category = ?"
            params.append(category)
        if account:
            sql += " AND e.account = ?" if query else " AND account = ?"
            params.append(account)
        if folder:
            sql += " AND e.folder = ?" if query else " AND folder = ?"
            params.append(folder)
        if since:
            sql += " AND e.date_iso >= ?" if query else " AND date_iso >= ?"
            params.append(since)
        if before:
            sql += " AND e.date_iso < ?" if query else " AND date_iso < ?"
            params.append(before)

        sql += " ORDER BY e.date_iso DESC" if query else " ORDER BY date_iso DESC"
        sql += " LIMIT 50"

        cursor = conn.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        columns = [
            "id",
            "msg_uid",
            "account",
            "folder",
            "from_addr",
            "subject",
            "date_iso",
            "category",
            "keywords",
            "match_snippet",
        ]
        emails = inbox_service.decorate_emails(
            [
                inbox_service.normalize_mail_item(dict(zip(columns, row)))
                for row in results
            ]
        )
        conn.close()
        return jsonify(
            {
                "emails": emails,
                "total": len(emails),
                "page": 1,
                "per_page": len(emails),
                "failures": [],
            }
        )
    except Exception as e:
        return jsonify(
            {
                "error": str(e),
                "emails": [],
                "total": 0,
                "page": 1,
                "per_page": 0,
                "failures": [],
            }
        )


@inbox_bp.route("/api/folders")
def api_folders():
    account_name = request.args.get("account", "")
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404, folders=[])
    try:
        return jsonify(imap_service.list_folders(acc))
    except Exception as e:
        return _json_error(str(e), 502, folders=[])


@inbox_bp.route("/api/inbox")
def api_inbox():
    account_name = request.args.get("account", "")
    folder = request.args.get("folder", "INBOX")
    page = _safe_int(request.args.get("page", 1))
    per_page = _safe_int(request.args.get("per_page", 50), 50)
    acc = get_account(account_name)
    if not acc:
        return _json_error(
            "Account nicht gefunden", 404, emails=[], total=0, failures=[]
        )
    try:
        emails, total = imap_service.list_folder_emails(acc, folder, page, per_page)
        emails = inbox_service.decorate_emails(emails)
        return jsonify(
            {
                "emails": emails,
                "total": total,
                "page": page,
                "per_page": per_page,
                "failures": [],
            }
        )
    except Exception as e:
        return _json_error(str(e), 502, emails=[], total=0, failures=[])


@inbox_bp.route("/api/unified-inbox")
def api_unified_inbox():
    page = _safe_int(request.args.get("page", 1))
    per_page = _safe_int(request.args.get("per_page", 50), 50)
    cfg = load_config()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                _fetch_account_inbox, inject_account_secret(acc), per_page, page
            ): acc
            for acc in cfg.get("accounts", [])
        }
        account_results = []
        for future in concurrent.futures.as_completed(futures):
            account_results.append(future.result())
    return jsonify(
        inbox_service.merge_unified_inbox_results(account_results, page, per_page)
    )


@inbox_bp.route("/api/email/<account_name>/<folder>/<uid>")
def api_email_detail(account_name, folder, uid):
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404)
    try:
        result = imap_service.get_email_detail(acc, folder, uid)
        result["tags"] = memory.get_tags(uid, account_name, folder)
        result["analysis"] = memory.get_email_summary(uid, account_name, folder)
        result["attachments"] = [
            {
                "filename": a["filename"],
                "size": a["size"],
                "content_type": a["content_type"],
            }
            for a in result.get("attachments", [])
        ]
        return jsonify(result)
    except Exception as e:
        return _json_error(str(e), 404 if "nicht gefunden" in str(e).lower() else 502)


@inbox_bp.route("/api/email/<account_name>/<folder>/<uid>/attachment/<int:att_index>")
def api_email_attachment(account_name, folder, uid, att_index):
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404)
    try:
        att = imap_service.get_attachment(acc, folder, uid, att_index)
        from flask import Response

        return Response(
            att["data"],
            mimetype=att["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{att["filename"]}"'
            },
        )
    except Exception as e:
        return _json_error(str(e), 404 if "nicht gefunden" in str(e).lower() else 502)


@inbox_bp.route(
    "/api/email/<account_name>/<folder>/<uid>/unsubscribe", methods=["POST"]
)
def api_email_unsubscribe(account_name, folder, uid):
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404)
    try:
        detail = imap_service.get_email_detail(acc, folder, uid)
        options = detail.get("unsubscribe_options", [])
        http_option = next(
            (opt for opt in options if opt.lower().startswith(("http://", "https://"))),
            None,
        )
        mailto_option = next(
            (opt for opt in options if opt.lower().startswith("mailto:")), None
        )
        if http_option:
            return jsonify({"success": True, "method": "http", "url": http_option})
        if mailto_option:
            return jsonify({"success": True, "method": "mailto", "url": mailto_option})
        return jsonify(
            {"success": False, "error": "Keine Unsubscribe-Option gefunden"}
        ), 400
    except Exception as e:
        return _json_error(str(e), 502)


@inbox_bp.route("/api/email/<account_name>/<folder>/<uid>/flag", methods=["POST"])
def api_email_flag(account_name, folder, uid):
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404)
    action = (request.json or {}).get("action", "flag")
    try:
        imap_service.set_flag(acc, folder, uid, action)
        return jsonify({"success": True})
    except Exception as e:
        return _json_error(str(e), 502)


@inbox_bp.route("/api/email/bulk", methods=["POST"])
def api_email_bulk():
    data = request.json or {}
    items = data.get("items", [])
    action = data.get("action", "").strip().lower()
    target_folder = data.get("target_folder", "").strip()
    tag = data.get("tag", "").strip()
    if not items or not action:
        return _json_error("Aktion oder Emails fehlen", 400)
    grouped = {}
    for item in items:
        account_name = item.get("account", "")
        folder = item.get("folder", "")
        uid = str(item.get("uid", "")).strip()
        if not all([account_name, folder, uid]):
            continue
        grouped.setdefault((account_name, folder), []).append(uid)
    results = {"updated": 0, "errors": []}
    for (account_name, folder), uids in grouped.items():
        acc = get_account(account_name)
        if not acc:
            results["errors"].append(f"Account nicht gefunden: {account_name}")
            continue
        try:
            if action == "tag":
                if not tag:
                    raise ValueError("Tag fehlt")
                for uid in uids:
                    memory.add_tag(uid, account_name, folder, tag)
            elif action == "untag":
                if not tag:
                    raise ValueError("Tag fehlt")
                for uid in uids:
                    memory.remove_tag(uid, account_name, folder, tag)
            else:
                imap_service.bulk_update(acc, folder, uids, action, target_folder)
            results["updated"] += len(uids)
        except Exception as e:
            results["errors"].append(f"{account_name}/{folder}: {e}")
    return jsonify({"success": len(results["errors"]) == 0, **results})


@inbox_bp.route("/api/send", methods=["POST"])
def api_send():
    data = request.json or {}
    account_name = data.get("account", "")
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404)
    if not data.get("to"):
        return _json_error("Empfänger fehlt", 400)
    try:
        from smtp_client import send_email

        attachments_raw = []
        for att in data.get("attachments", []):
            attachments_raw.append(
                {
                    "filename": att.get("filename", "attachment"),
                    "data": base64.b64decode(att.get("data_b64", "")),
                }
            )
        result = send_email(
            account=acc,
            to=data.get("to", []),
            cc=data.get("cc", []),
            bcc=data.get("bcc", []),
            subject=data.get("subject", "(Kein Betreff)"),
            body_text=data.get("body_text", ""),
            body_html=data.get("body_html"),
            reply_to=data.get("reply_to"),
            in_reply_to=data.get("in_reply_to"),
            references=data.get("references"),
            attachments=attachments_raw if attachments_raw else None,
        )
        return jsonify(result), (200 if result.get("success") else 502)
    except Exception as e:
        return _json_error(str(e), 502)


@inbox_bp.route("/api/smtp-test", methods=["POST"])
def api_smtp_test():
    data = request.json or {}
    account_name = data.get("account", "")
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404)
    from smtp_client import test_smtp_connection

    result = test_smtp_connection(acc)
    return jsonify(result), (200 if result.get("success") else 502)


@inbox_bp.route("/api/smtp-presets")
def api_smtp_presets():
    from smtp_client import SMTP_PRESETS

    return jsonify({"presets": list(SMTP_PRESETS.keys())})
