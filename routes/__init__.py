from .config_routes import config_bp
from .health_routes import health_bp, init_app as init_health_routes
from .inbox_routes import inbox_bp
from .llm_routes import llm_bp
from .memory_routes import memory_bp
from .page_routes import page_bp
from .rag_routes import rag_bp
from .sorter_routes import sorter_bp
from .telegram_routes import telegram_bp
from .template_routes import template_bp


def register_blueprints(app):
    init_health_routes(app)
    app.register_blueprint(config_bp)
    app.register_blueprint(page_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(inbox_bp)
    app.register_blueprint(llm_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(sorter_bp)
    app.register_blueprint(telegram_bp)
    app.register_blueprint(template_bp)
