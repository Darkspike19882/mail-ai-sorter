import base64
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List

import memory
from config_service import get_account
from services import imap_service

router = APIRouter(tags=["email"])


class SendEmailRequest(BaseModel):
    account: str
    to: List[str] = []
    cc: List[str] = []
    bcc: List[str] = []
    subject: str = "(Kein Betreff)"
    body_text: str = ""
    body_html: Optional[str] = None
    reply_to: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    attachments: list = []


class FlagRequest(BaseModel):
    action: str = "flag"


class BulkActionRequest(BaseModel):
    items: list = []
    action: str = ""
    tag: str = ""
    target_folder: str = ""


@router.get("/api/email/{account_name}/{folder}/{uid}")
async def api_email_detail(account_name: str, folder: str, uid: str):
    acc = get_account(account_name)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden"}
    try:
        from config_service import inject_account_secret
        acc = inject_account_secret(acc)
        result = imap_service.get_email_detail(acc, folder, uid)
        result["tags"] = memory.get_tags(uid, account_name, folder)
        result["analysis"] = memory.get_email_summary(uid, account_name, folder)
        result["attachments"] = [
            {"filename": a["filename"], "size": a["size"], "content_type": a["content_type"]}
            for a in result.get("attachments", [])
        ]
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/email/{account_name}/{folder}/{uid}/attachment/{att_index}")
async def api_email_attachment(account_name: str, folder: str, uid: str, att_index: int):
    acc = get_account(account_name)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden"}
    try:
        from config_service import inject_account_secret
        acc = inject_account_secret(acc)
        att = imap_service.get_attachment(acc, folder, uid, att_index)
        return Response(
            content=att["data"],
            media_type=att["content_type"],
            headers={"Content-Disposition": f'attachment; filename="{att["filename"]}"'},
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/email/{account_name}/{folder}/{uid}/unsubscribe")
async def api_email_unsubscribe(account_name: str, folder: str, uid: str):
    acc = get_account(account_name)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden"}
    try:
        from config_service import inject_account_secret
        acc = inject_account_secret(acc)
        detail = imap_service.get_email_detail(acc, folder, uid)
        options = detail.get("unsubscribe_options", [])
        http_option = next((opt for opt in options if opt.lower().startswith(("http://", "https://"))), None)
        mailto_option = next((opt for opt in options if opt.lower().startswith("mailto:")), None)
        if http_option:
            return {"success": True, "method": "http", "url": http_option}
        if mailto_option:
            return {"success": True, "method": "mailto", "url": mailto_option}
        return {"success": False, "error": "Keine Unsubscribe-Option gefunden"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/email/{account_name}/{folder}/{uid}/flag")
async def api_email_flag(account_name: str, folder: str, uid: str, body: FlagRequest = None):
    acc = get_account(account_name)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden"}
    action = body.action if body else "flag"
    try:
        from config_service import inject_account_secret
        acc = inject_account_secret(acc)
        imap_service.set_flag(acc, folder, uid, action)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/email/bulk")
async def api_email_bulk(body: BulkActionRequest):
    items = body.items
    action = body.action.strip().lower()
    target_folder = body.target_folder.strip()
    tag = body.tag.strip()
    if not items or not action:
        return {"success": False, "error": "Aktion oder Emails fehlen"}
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
            from config_service import inject_account_secret
            acc = inject_account_secret(acc)
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
    return {"success": len(results["errors"]) == 0, **results}


@router.post("/api/send")
async def api_send(body: SendEmailRequest):
    acc = get_account(body.account)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden"}
    if not body.to:
        return {"success": False, "error": "Empfänger fehlt"}
    try:
        from smtp_client import send_email

        attachments_raw = []
        for att in body.attachments:
            attachments_raw.append({
                "filename": att.get("filename", "attachment"),
                "data": base64.b64decode(att.get("data_b64", "")),
            })

        result = send_email(
            account=acc,
            to=body.to,
            cc=body.cc,
            bcc=body.bcc,
            subject=body.subject,
            body_text=body.body_text,
            body_html=body.body_html,
            reply_to=body.reply_to,
            in_reply_to=body.in_reply_to,
            references=body.references,
            attachments=attachments_raw if attachments_raw else None,
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/email/send")
async def api_email_send(body: SendEmailRequest):
    return await api_send(body)


@router.post("/api/email/smtp-test")
async def api_smtp_test(body: dict = None):
    account_name = (body or {}).get("account", "")
    acc = get_account(account_name)
    if not acc:
        return {"success": False, "error": "Account nicht gefunden"}
    from smtp_client import test_smtp_connection
    result = test_smtp_connection(acc)
    return result


@router.get("/api/email/smtp-presets")
async def api_smtp_presets():
    from smtp_client import SMTP_PRESETS
    return {"success": True, "presets": list(SMTP_PRESETS.keys())}
