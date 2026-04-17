from flask import Blueprint, jsonify, request

import memory
from services import rag_service

rag_bp = Blueprint("rag_routes", __name__)


@rag_bp.route("/api/rag/query", methods=["POST"])
def api_rag_query():
    data = request.json or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"success": False, "error": "Keine Frage"})
    return jsonify(
        rag_service.query(
            query,
            limit=data.get("limit", 10),
            account=data.get("account"),
            folder=data.get("folder"),
            since=data.get("since"),
            before=data.get("before"),
        )
    )


@rag_bp.route("/api/rag/status")
def api_rag_status():
    return jsonify(rag_service.get_status())


@rag_bp.route("/api/rag/history")
def api_rag_history():
    limit = min(int(request.args.get("limit", 20)), 50)
    return jsonify({"success": True, "history": memory.get_rag_history(limit=limit)})


@rag_bp.route("/api/rag/reindex", methods=["POST"])
def api_rag_reindex():
    return jsonify(rag_service.reindex())
