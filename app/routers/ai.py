from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(tags=["ai"])


class SummarizeRequest(BaseModel):
    subject: str
    from_addr: str = ""
    body: str
    category: str = "privat"
    uid: str = ""
    account: str = ""
    folder: str = ""


@router.post("/api/llm/summarize")
async def api_llm_summarize(body: SummarizeRequest):
    from services.llm_service import summarize_email
    result = summarize_email(body.subject, body.from_addr, body.body, body.category, body.uid, body.account, body.folder)
    if not result:
        return {"success": False, "error": "LLM nicht erreichbar"}
    return {"success": True, **result}


class AnalyzeRequest(BaseModel):
    subject: str
    from_addr: str
    body: str
    category: str = "auto"
    uid: str = ""
    account: str = ""
    folder: str = ""


@router.post("/api/llm/analyze-email")
async def api_llm_analyze_email(body: AnalyzeRequest):
    from services.llm_service import analyze_email
    result = analyze_email(body.subject, body.from_addr, body.body, body.category, body.uid, body.account, body.folder)
    if not result:
        return {"success": False, "error": "LLM nicht erreichbar"}
    return {"success": True, **result}


class QuickReplyRequest(BaseModel):
    subject: str
    from_addr: str
    body: str
    tone: str = "freundlich"
    language: str = "de"
    thread_context: Optional[str] = None


@router.post("/api/llm/quick-reply")
async def api_llm_quick_reply(body: QuickReplyRequest):
    from services.llm_service import draft_reply
    result = draft_reply(body.subject, body.from_addr, body.body, body.tone, body.language, body.thread_context)
    if not result:
        return {"success": False, "error": "LLM nicht erreichbar"}
    return {"success": True, "draft": result}


class AdaptTemplateRequest(BaseModel):
    template_body: str
    subject: str
    from_addr: str
    body: str
    tone: str = "freundlich"
    language: str = "de"
    thread_context: Optional[str] = None


@router.post("/api/llm/adapt-template")
async def api_llm_adapt_template(body: AdaptTemplateRequest):
    from services.llm_service import adapt_template
    result = adapt_template(body.template_body, body.subject, body.from_addr, body.body, body.tone, body.language, body.thread_context)
    if not result:
        return {"success": False, "error": "LLM nicht erreichbar"}
    return {"success": True, "draft": result}


class DigestRequest(BaseModel):
    days: int = 1
    limit: int = 30


@router.post("/api/llm/digest")
async def api_llm_digest(body: DigestRequest):
    from services.llm_service import build_digest
    return build_digest(body.days, body.limit)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/api/llm/chat")
async def api_llm_chat(body: ChatRequest):
    from services.llm_service import chat_with_assistant
    reply = chat_with_assistant(body.session_id, body.message)
    if not reply:
        return {"success": False, "error": "LLM nicht erreichbar"}
    return {"success": True, "reply": reply}


@router.get("/api/llm/email-summary/{account_name}/{folder}/{uid}")
async def api_llm_email_summary(account_name: str, folder: str, uid: str):
    import memory
    summaries = memory.get_email_summaries(uid, account_name, folder)
    return {"success": True, "summaries": summaries}


class BatchSummaryItem(BaseModel):
    uid: str
    account: str = ""
    folder: str = ""
    subject: str = ""
    body: str = ""


class BatchSummaryRequest(BaseModel):
    mails: List[BatchSummaryItem] = []


@router.post("/api/ai/batch-summary")
async def api_llm_batch_summary(body: BatchSummaryRequest):
    from services.llm_service import summarize_email
    summaries = {}
    for mail in body.mails[:20]:
        try:
            result = summarize_email(mail.subject, "", mail.body[:500], "auto", mail.uid, mail.account, mail.folder)
            if result and result.get("summary"):
                summaries[mail.uid] = result["summary"]
        except Exception:
            summaries[mail.uid] = ""
    return {"success": True, "summaries": summaries}
