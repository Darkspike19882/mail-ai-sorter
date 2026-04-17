#!/usr/bin/env python3
"""
Inbox decoration, normalization, and smart-priority helpers.
"""

import email.utils
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import memory


def parse_mail_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def to_date_iso(value: Any) -> str:
    parsed = parse_mail_date(value)
    return parsed.isoformat() if parsed else ""


def normalize_mail_item(email_item: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(email_item)
    uid = item.get("uid") or item.get("msg_uid") or ""
    date_value = item.get("date") or item.get("date_iso") or ""
    date_iso = to_date_iso(date_value)
    normalized = {
        "uid": str(uid) if uid is not None else "",
        "msg_uid": str(uid) if uid is not None else "",
        "account": item.get("account", ""),
        "folder": item.get("folder", ""),
        "from": item.get("from") or item.get("from_addr") or "",
        "from_addr": item.get("from_addr") or item.get("from") or "",
        "to": item.get("to", ""),
        "cc": item.get("cc", ""),
        "subject": item.get("subject", ""),
        "date": date_iso or str(date_value or ""),
        "date_iso": date_iso,
        "seen": bool(item.get("seen", True)),
        "flagged": bool(item.get("flagged", False)),
        "message_id": item.get("message_id", ""),
        "in_reply_to": item.get("in_reply_to", ""),
        "references": item.get("references", ""),
    }
    normalized.update(item)
    normalized.update(
        {
            "uid": str(uid) if uid is not None else "",
            "msg_uid": str(uid) if uid is not None else "",
            "from": normalized.get("from") or normalized.get("from_addr") or "",
            "from_addr": normalized.get("from_addr") or normalized.get("from") or "",
            "date": date_iso or str(date_value or ""),
            "date_iso": date_iso,
            "seen": bool(normalized.get("seen", True)),
            "flagged": bool(normalized.get("flagged", False)),
        }
    )
    return normalized


def mail_sort_key(email_item: Dict[str, Any]) -> Tuple[datetime, str, str, str]:
    normalized = normalize_mail_item(email_item)
    parsed_date = parse_mail_date(normalized.get("date_iso") or normalized.get("date"))
    return (
        parsed_date or datetime.min.replace(tzinfo=timezone.utc),
        str(normalized.get("account", "")),
        str(normalized.get("folder", "")),
        str(normalized.get("uid", "")),
    )


def sort_mail_items(email_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(email_items, key=mail_sort_key, reverse=True)


def merge_unified_inbox_results(
    account_results: List[Dict[str, Any]], page: int, per_page: int
) -> Dict[str, Any]:
    all_emails: List[Dict[str, Any]] = []
    failures: List[Dict[str, str]] = []
    total = 0
    for result in account_results:
        all_emails.extend(result.get("emails", []))
        total += int(result.get("total", 0) or 0)
        if result.get("error"):
            failures.append(
                {
                    "account": str(result.get("account", "")),
                    "error": str(result.get("error", "")),
                }
            )

    ordered = sort_mail_items(all_emails)
    start = max(0, page - 1) * per_page
    return {
        "emails": ordered[start : start + per_page],
        "total": total,
        "page": page,
        "per_page": per_page,
        "failures": failures,
        "degraded": bool(failures),
    }


def score_priority(
    summary: Optional[Dict[str, Any]], is_seen: bool, is_flagged: bool
) -> Tuple[int, str]:
    if not summary:
        score = 55 if (not is_seen or is_flagged) else 35
    else:
        importance = str(summary.get("importance", "mittel")).lower()
        action_needed = bool(summary.get("action_needed", False))
        tone = str(summary.get("tone", "")).lower()
        score = 20
        if importance == "hoch":
            score += 45
        elif importance == "mittel":
            score += 20
        if action_needed:
            score += 20
        if any(word in tone for word in ["dring", "urgent", "frist", "krit"]):
            score += 10
        if is_flagged:
            score += 10
        if not is_seen:
            score += 5
        score = max(0, min(100, score))

    if score >= 80:
        bucket = "dringend"
    elif score >= 60:
        bucket = "heute"
    elif score >= 40:
        bucket = "info"
    else:
        bucket = "niedrig"
    return score, bucket


def decorate_email(email_item: Dict[str, Any]) -> Dict[str, Any]:
    decorated = decorate_emails([email_item])
    return decorated[0] if decorated else email_item


def decorate_emails(email_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not email_items:
        return []

    normalized_items = [normalize_mail_item(item) for item in email_items]
    keys = [
        (str(item.get("uid", "")), item.get("account", ""), item.get("folder", ""))
        for item in normalized_items
        if item.get("uid") and item.get("account") and item.get("folder")
    ]
    summaries = memory.get_email_summaries_for_many(keys)
    tags = memory.get_tags_for_many(keys)

    decorated = []
    for item in normalized_items:
        key = (
            str(item.get("uid", "")),
            item.get("account", ""),
            item.get("folder", ""),
        )
        summary = summaries.get(key)
        tag_list = tags.get(key, [])
        score, bucket = score_priority(
            summary, item.get("seen", True), item.get("flagged", False)
        )
        enriched = dict(item)
        enriched["analysis"] = summary
        enriched["tags"] = tag_list
        enriched["priority_score"] = score
        enriched["smart_priority"] = bucket
        decorated.append(enriched)
    return decorated
