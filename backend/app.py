import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "template"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "static"),
    )
    app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-secret")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    from .routes import api
    app.register_blueprint(api)

    # Serve index.html for all page routes (SPA-like pattern with server templates)
    @app.route("/")
    @app.route("/login")
    @app.route("/register")
    @app.route("/properties-page")
    @app.route("/property/<path:pid>")
    @app.route("/dashboard")
    @app.route("/admin")
    def serve_index(**kwargs):
        return send_from_directory(app.template_folder, "index.html")

    # Seed on first request
    @app.before_request
    def _seed_once():
        if not getattr(app, "_seeded", False):
            app._seeded = True
            try:
                from .db import seed_properties
                seed_properties()
            except Exception as e:
                print(f"[seed] Skipped seeding: {e}")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)