import json

from flask import Blueprint, jsonify, request

from config_service import load_config, save_config
from pathlib import Path


config_bp = Blueprint("config_routes", __name__)
SORTER_DIR = Path(__file__).resolve().parent.parent


@config_bp.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        new_config = request.json
        if save_config(new_config):
            return jsonify({"success": True})
        return jsonify(
            {"success": False, "error": "Konnte Konfiguration nicht speichern"}
        )
    return jsonify(load_config())


@config_bp.route("/api/rule-templates")
def api_rule_templates():
    try:
        templates_file = SORTER_DIR / "rule_templates.json"
        with open(templates_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)})
