#!/usr/bin/env python3
"""
Inbox decoration and smart-priority helpers.
"""

from typing import Any, Dict, List, Optional, Tuple

import memory


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

    keys = [
        (str(item.get("uid", "")), item.get("account", ""), item.get("folder", ""))
        for item in email_items
        if item.get("uid") and item.get("account") and item.get("folder")
    ]
    summaries = memory.get_email_summaries_for_many(keys)
    tags = memory.get_tags_for_many(keys)

    decorated = []
    for item in email_items:
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
