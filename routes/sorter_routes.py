from flask import Blueprint, jsonify, request

from services import sorter_service

sorter_bp = Blueprint("sorter_routes", __name__)


@sorter_bp.route("/api/sorter/status")
def api_sorter_status():
    return jsonify(sorter_service.get_status())


@sorter_bp.route("/api/sorter/start", methods=["POST"])
def api_sorter_start():
    return jsonify(sorter_service.start_daemon())


@sorter_bp.route("/api/sorter/pause", methods=["POST"])
def api_sorter_pause():
    return jsonify(sorter_service.pause_daemon())


@sorter_bp.route("/api/sorter/resume", methods=["POST"])
def api_sorter_resume():
    return jsonify(sorter_service.resume_daemon())


@sorter_bp.route("/api/sorter/stop", methods=["POST"])
def api_sorter_stop():
    return jsonify(sorter_service.stop_daemon())


@sorter_bp.route("/api/sorter/quiet-hours", methods=["POST"])
def api_sorter_quiet_hours():
    return jsonify(sorter_service.update_quiet_hours(request.json or {}))


@sorter_bp.route("/api/run", methods=["POST"])
def api_run():
    data = request.json or {}
    return jsonify(
        sorter_service.run_sorter_once(
            dry_run=data.get("dry_run", False),
            max_mails=data.get("max_mails", 10),
        )
    )


@sorter_bp.route("/api/logs")
def api_logs():
    return jsonify(sorter_service.get_logs())


@sorter_bp.route("/api/logs/clear", methods=["POST"])
def api_logs_clear():
    return jsonify(sorter_service.clear_logs())
