from flask import Blueprint, jsonify, request

from services import rag_service

rag_bp = Blueprint("rag_routes", __name__)


@rag_bp.route("/api/rag/query", methods=["POST"])
def api_rag_query():
    data = request.json or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"success": False, "error": "Keine Frage"})
    return jsonify(rag_service.query(query, limit=data.get("limit", 10)))


@rag_bp.route("/api/rag/status")
def api_rag_status():
    return jsonify(rag_service.get_status())


@rag_bp.route("/api/rag/reindex", methods=["POST"])
def api_rag_reindex():
    return jsonify(rag_service.reindex())
