from flask import Flask, send_from_directory, jsonify
import os

from extensions import db, migrate, jwt, cors
from config import Config

from routes.auth_route import auth_bp
from routes.user_route import user_bp
from routes.admin_route import admin_bp
from routes.category_route import category_bp
from routes.comment_route import comment_bp
from routes.content_route import content_bp
from routes.notification_route import notification_bp
from routes.profile import profile_bp
from routes.reaction_route import reaction_bp
from routes.report_route import report_bp
from routes.subscription_route import subscription_bp
from routes.wishlist_route import wishlist_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5173"
                ],
                "methods": [
                    "GET",
                    "POST",
                    "PUT",
                    "PATCH",
                    "DELETE",
                    "OPTIONS"
                ],
                "allow_headers": [
                    "Content-Type",
                    "Authorization"
                ],
                "supports_credentials": True
            }
        }
    )



    @app.route("/")
    def home():
        return jsonify({
            "message": "Moringa School Daily Dev API is running",
            "status": "success"
        }), 200

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(
            os.path.join(app.root_path, "uploads"),
            filename
        )

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(reaction_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(wishlist_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)