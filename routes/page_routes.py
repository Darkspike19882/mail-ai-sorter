import json

from flask import Blueprint, jsonify, render_template, request

from config_service import load_config
from services.stats_service import get_detailed_stats, get_stats


page_bp = Blueprint("page_routes", __name__)


@page_bp.route("/")
def index():
    return render_template("dashboard.html", stats=get_stats())


@page_bp.route("/config")
def config_page():
    return render_template("configuration.html", config=load_config())


@page_bp.route("/inbox")
def inbox_page():
    return render_template("inbox.html", config=load_config())


@page_bp.route("/logs")
def logs_page():
    return render_template("logs.html")


@page_bp.route("/stats")
def stats_page():
    return render_template("stats.html", stats=get_detailed_stats())


@page_bp.route("/setup")
def setup_page():
    return render_template("setup.html")


@page_bp.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@page_bp.route("/api/stats/detailed")
def api_stats_detailed():
    return jsonify(get_detailed_stats(request.args.get("days", "30")))


@page_bp.route("/api/ollama-check")
def api_ollama_check():
    import urllib.request

    cfg = load_config()
    ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
    result = {"installed": False, "version": None, "models": [], "url": ollama_url}
    try:
        r = urllib.request.urlopen(ollama_url + "/api/version", timeout=5)
        data = json.loads(r.read().decode())
        result["installed"] = True
        result["version"] = data.get("version", "?")
    except Exception:
        return jsonify(result)
    try:
        r = urllib.request.urlopen(ollama_url + "/api/tags", timeout=5)
        data = json.loads(r.read().decode())
        for m in data.get("models", []):
            result["models"].append(
                {"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 1)}
            )
    except Exception:
        pass
    return jsonify(result)
