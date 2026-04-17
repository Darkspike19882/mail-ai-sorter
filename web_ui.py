#!/usr/bin/env python3
"""
Mail AI Sorter - Web UI bootstrap.
"""

from flask import Flask, redirect, url_for

from routes import register_blueprints


app = Flask(__name__)
register_blueprints(app)


@app.route("/configuration")
def configuration_redirect():
    return redirect(url_for("page_routes.config_page"))


if __name__ == "__main__":
    print("🌐 Mail AI Sorter Web UI")
    print("=" * 50)
    print("Starte Web-Server auf http://0.0.0.0:5001")
    print("🔗 Tailscale: http://100.97.63.41:5001")
    print("🔗 Lokal: http://localhost:5001")
    print("Drücke STRG+C zum Beenden")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=5001)
