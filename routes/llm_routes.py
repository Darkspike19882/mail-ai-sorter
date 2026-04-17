from flask import Blueprint, jsonify, request

from config_service import get_account
from services import imap_service, llm_service

llm_bp = Blueprint("llm_routes", __name__)


def _json_error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


@llm_bp.route("/api/llm/summarize", methods=["POST"])
def api_llm_summarize():
    data = request.json or {}
    result = llm_service.summarize_email(
        subject=data.get("subject", ""),
        from_addr=data.get("from_addr", ""),
        body=data.get("body", ""),
        category=data.get("category", "privat"),
        uid=data.get("uid", ""),
        account=data.get("account", ""),
        folder=data.get("folder", ""),
    )
    if result:
        return jsonify({"success": True, **result})
    return _json_error("LLM nicht erreichbar", 503)


@llm_bp.route("/api/llm/analyze-email", methods=["POST"])
def api_llm_analyze_email():
    data = request.json or {}
    result = llm_service.analyze_email(
        subject=data.get("subject", ""),
        from_addr=data.get("from_addr", ""),
        body=data.get("body", ""),
        category=data.get("category", "auto"),
        uid=data.get("uid", ""),
        account=data.get("account", ""),
        folder=data.get("folder", ""),
    )
    if not result:
        return _json_error("LLM nicht erreichbar", 503)
    return jsonify({"success": True, **result})


@llm_bp.route("/api/llm/quick-reply", methods=["POST"])
def api_llm_quick_reply():
    data = request.json or {}
    thread_items = data.get("thread_context") or []
    thread_context = None
    if thread_items:
        parts = []
        for item in thread_items[-3:]:
            parts.append(
                f"  Von: {item.get('from', '?')} | Betreff: {item.get('subject', '?')}\n  {item.get('body', '')[:500]}"
            )
        thread_context = "\n".join(parts)
    result = llm_service.draft_reply(
        subject=data.get("subject", ""),
        from_addr=data.get("from_addr", ""),
        body=data.get("body", ""),
        tone=data.get("tone", "freundlich"),
        language=data.get("language", "de"),
        thread_context=thread_context,
    )
    if not result:
        return _json_error("LLM nicht erreichbar", 503)
    return jsonify({"success": True, **result})


@llm_bp.route("/api/llm/adapt-template", methods=["POST"])
def api_llm_adapt_template():
    data = request.json or {}
    template_body = data.get("template_body", "")
    if not template_body:
        return _json_error("Vorlagen-Text fehlt", 400)
    thread_items = data.get("thread_context") or []
    thread_context = None
    if thread_items:
        parts = []
        for item in thread_items[-3:]:
            parts.append(
                f"  Von: {item.get('from', '?')} | Betreff: {item.get('subject', '?')}\n  {item.get('body', '')[:500]}"
            )
        thread_context = "\n".join(parts)
    result = llm_service.adapt_template(
        template_body=template_body,
        subject=data.get("subject", ""),
        from_addr=data.get("from_addr", ""),
        body=data.get("body", ""),
        tone=data.get("tone", "freundlich"),
        language=data.get("language", "de"),
        thread_context=thread_context,
    )
    if result is None:
        return _json_error("LLM nicht erreichbar", 503)
    return jsonify({"success": True, "reply": result})


@llm_bp.route("/api/llm/digest")
def api_llm_digest():
    try:
        return jsonify(llm_service.build_digest())
    except Exception as e:
        return _json_error(str(e), 500)


@llm_bp.route("/api/llm/chat", methods=["POST"])
def api_llm_chat():
    data = request.json or {}
    session_id = data.get("session_id", "default")
    message = data.get("message", "")
    if not message:
        return _json_error("Keine Nachricht", 400)
    reply = llm_service.chat_with_assistant(session_id, message)
    if reply:
        return jsonify({"success": True, "reply": reply})
    return _json_error("LLM nicht erreichbar", 503)


@llm_bp.route("/api/llm/email-summary/<account_name>/<folder>/<uid>")
def api_llm_email_summary(account_name, folder, uid):
    acc = get_account(account_name)
    if not acc:
        return _json_error("Account nicht gefunden", 404)
    try:
        detail = imap_service.get_email_detail(acc, folder, uid)
        result = llm_service.summarize_email(
            subject=detail.get("subject", ""),
            from_addr=detail.get("from", ""),
            body=(detail.get("body_text") or detail.get("body_html") or "")[:3000],
            category="auto",
            uid=uid,
            account=account_name,
            folder=folder,
        )
        if result:
            return jsonify({"success": True, **result})
        return _json_error("LLM nicht erreichbar", 503)
    except Exception as e:
        return _json_error(str(e), 502)
