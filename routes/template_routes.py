from flask import Blueprint, jsonify, request

import memory

template_bp = Blueprint("template_routes", __name__)


@template_bp.route("/api/templates")
def api_templates():
    category = request.args.get("category", "")
    templates = memory.get_templates(category=category or None)
    return jsonify({"success": True, "templates": templates})


@template_bp.route("/api/templates", methods=["POST"])
def api_create_template():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    body = (data.get("body") or "").strip()
    if not name or not body:
        return jsonify({"success": False, "error": "Name und Inhalt erforderlich"}), 400
    template = memory.create_template(name, body, data.get("category", "Allgemein"))
    return jsonify({"success": True, **template}), 201


@template_bp.route("/api/templates/<int:template_id>", methods=["PUT"])
def api_update_template(template_id):
    data = request.json or {}
    template = memory.update_template(template_id, **data)
    if not template:
        return jsonify({"success": False, "error": "Vorlage nicht gefunden"}), 404
    return jsonify({"success": True, **template})


@template_bp.route("/api/templates/<int:template_id>", methods=["DELETE"])
def api_delete_template(template_id):
    if memory.delete_template(template_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Vorlage nicht gefunden"}), 404
