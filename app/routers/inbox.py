import concurrent.futures
from pathlib import Path

from fastapi import APIRouter

import memory
from config_service import get_account, inject_account_secret, load_config
from services import imap_service, inbox_service

router = APIRouter(tags=["inbox"])
INDEX_DB = Path(__file__).resolve().parent.parent.parent / "mail_index.db"


def _fetch_account_inbox(acc, per_page, page):
    try:
        emails, total = imap_service.list_folder_emails(acc, "INBOX", 1, per_page * page)
        return {"account": acc.get("name", ""), "emails": inbox_service.decorate_emails(emails), "total": total, "error": None}
    except Exception as exc:
        return {"account": acc.get("name", ""), "emails": [], "total": 0, "error": str(exc)}


@router.get("/api/tags")
async def api_tags():
    return memory.get_all_tags()


@router.post("/api/tags")
async def api_save_tag(body: dict = None):
    data = body or {}
    msg_uid = data.get("msg_uid")
    account = data.get("account")
    folder = data.get("folder")
    tag = data.get("tag")
    if not all([msg_uid, account, folder, tag]):
        return {"success": False, "error": "Fehlende Daten"}
    memory.add_tag(msg_uid, account, folder, tag)
    return {"success": True}


@router.delete("/api/tags/{msg_uid}/{account_name}/{folder}")
async def api_delete_tag(msg_uid: str, account_name: str, folder: str, tag: str = ""):
    if not tag:
        return {"success": False, "error": "Tag fehlt"}
    memory.remove_tag(msg_uid, account_name, folder, tag)
    return {"success": True}


@router.get("/api/folders")
async def api_folders(account: str = ""):
    acc = get_account(account)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden", "folders": []}
    try:
        acc = inject_account_secret(acc)
        return imap_service.list_folders(acc)
    except Exception as e:
        return {"success": False, "error": str(e), "folders": []}


@router.get("/api/inbox")
async def api_inbox(account: str = "", folder: str = "INBOX", page: int = 1, per_page: int = 50):
    acc = get_account(account)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden", "emails": [], "total": 0, "failures": []}
    try:
        acc = inject_account_secret(acc)
        emails, total = imap_service.list_folder_emails(acc, folder, page, per_page)
        emails = inbox_service.decorate_emails(emails)
        return {"emails": emails, "total": total, "page": page, "per_page": per_page, "failures": []}
    except Exception as e:
        return {"success": False, "error": str(e), "emails": [], "total": 0, "failures": []}


@router.get("/api/unified-inbox")
async def api_unified_inbox(page: int = 1, per_page: int = 50):
    cfg = load_config()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_fetch_account_inbox, inject_account_secret(acc), per_page, page): acc for acc in cfg.get("accounts", [])}
        account_results = []
        for future in concurrent.futures.as_completed(futures):
            account_results.append(future.result())
    return inbox_service.merge_unified_inbox_results(account_results, page, per_page)


@router.get("/api/search")
async def api_search(q: str = "", category: str = "", account: str = "", folder: str = "", since: str = "", before: str = ""):
    try:
        import sqlite3
        conn = sqlite3.connect(str(INDEX_DB))
        if q:
            sql = """SELECT e.id, e.msg_uid, e.account, e.folder, e.from_addr, e.subject, e.date_iso, e.category, e.keywords, snippet(emails_fts, 3, '[', ']', '...', 12) AS match_snippet FROM emails_fts JOIN emails e ON e.id = emails_fts.rowid WHERE emails_fts MATCH ?"""
            params = [q]
        else:
            sql = """SELECT id, msg_uid, account, folder, from_addr, subject, date_iso, category, keywords, snippet AS match_snippet FROM emails WHERE 1=1"""
            params = []
        if category:
            sql += " AND e.category = ?" if q else " AND category = ?"
            params.append(category)
        if account:
            sql += " AND e.account = ?" if q else " AND account = ?"
            params.append(account)
        if folder:
            sql += " AND e.folder = ?" if q else " AND folder = ?"
            params.append(folder)
        sql += " ORDER BY e.date_iso DESC" if q else " ORDER BY date_iso DESC"
        sql += " LIMIT 50"
        cursor = conn.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        columns = ["id", "msg_uid", "account", "folder", "from_addr", "subject", "date_iso", "category", "keywords", "match_snippet"]
        emails = inbox_service.decorate_emails([inbox_service.normalize_mail_item(dict(zip(columns, row))) for row in results])
        conn.close()
        return {"emails": emails, "total": len(emails), "page": 1, "per_page": len(emails), "failures": []}
    except Exception as e:
        return {"error": str(e), "emails": [], "total": 0, "page": 1, "per_page": 0, "failures": []}
