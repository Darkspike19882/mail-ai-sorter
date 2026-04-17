from flask import Blueprint, jsonify, request

import memory

memory_bp = Blueprint("memory_routes", __name__)


@memory_bp.route("/api/memory")
def api_memory():
    return jsonify(memory.get_db_size())


@memory_bp.route("/api/memory/sessions")
def api_memory_sessions():
    return jsonify(memory.list_sessions())


@memory_bp.route("/api/memory/facts")
def api_memory_facts():
    cat = request.args.get("category")
    return jsonify(memory.get_facts(category=cat))


@memory_bp.route("/api/memory/facts", methods=["POST"])
def api_memory_save_fact():
    data = request.json or {}
    fact = data.get("fact", "")
    if not fact:
        return jsonify({"success": False, "error": "Kein Fakt"})
    memory.save_fact(fact, data.get("category", "general"), data.get("confidence", 0.5))
    return jsonify({"success": True})


@memory_bp.route("/api/memory/summaries")
def api_memory_summaries():
    days = int(request.args.get("days", 1))
    limit = int(request.args.get("limit", 50))
    cat = request.args.get("category")
    return jsonify(memory.get_recent_summaries(days=days, limit=limit, category=cat))


@memory_bp.route("/api/memory/rag-history")
def api_memory_rag_history():
    limit = int(request.args.get("limit", 20))
    return jsonify(memory.get_rag_history(limit))


@memory_bp.route("/api/memory/cleanup", methods=["POST"])
def api_memory_cleanup():
    data = request.json or {}
    days = int(data.get("days", 90))
    return jsonify(memory.cleanup_old_data(days))
