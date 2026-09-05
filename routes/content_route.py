
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from routes.auth_route import current_user
from werkzeug.utils import secure_filename
import os
import uuid

from extensions import db
from models.content import Content
from models.comment import Comment

from services import content_service
from services.recommendation_service import get_recommended_content

from routes.auth_helpers import get_current_user


content_bp = Blueprint(
    "content",
    __name__,
    url_prefix="/api/content"
)

# GET ALL CONTENT

@content_bp.route("", methods=["GET"])
def list_content():
    category_id = request.args.get(
        "category_id",
        type=int
    )

    items = content_service.get_feed(
        category_id=category_id
    )

    return jsonify(items), 200

# GET RECOMMENDED CONTENT

@content_bp.route("/recommended", methods=["GET"])
@jwt_required()
def recommended():
    current_user = get_current_user()

    items = get_recommended_content(
        current_user
    )

    return jsonify(items), 200


# GET PENDING CONTENT

@content_bp.route("/pending", methods=["GET"])
@jwt_required()
def pending_review():
    current_user = get_current_user()

    if current_user.role not in ("admin", "writer"):
        return jsonify({
            "error": "Forbidden"
        }), 403

    items = content_service.get_pending()

    return jsonify(items), 200


# GET ONE CONTENT ITEM

@content_bp.route("/<int:content_id>", methods=["GET"])
def get_content(content_id):
    item = Content.query.get_or_404(
        content_id
    )

    return jsonify(
        content_service.get_content_with_counts(item)
    ), 200


# CREATE CONTENT

@content_bp.route("", methods=["POST"])
@jwt_required()
def create_content():
    current_user = get_current_user()

    if request.content_type and request.content_type.startswith("multipart/form-data"):
        data = {
            "title": request.form.get("title", "").strip(),
            "type": request.form.get("type", "").strip().lower(),
            "category_id": request.form.get("category_id", type=int),
            "body_or_url": request.form.get("body_or_url", "").strip(),
        }
        media_file = request.files.get("media_file")

        if data["type"] in ("video", "audio") and media_file and media_file.filename:
            upload_dir = os.path.join(current_app.root_path, "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            original_name = secure_filename(media_file.filename)
            extension = os.path.splitext(original_name)[1].lower()

            allowed_extensions = {
                "video": {".mp4", ".webm", ".mov", ".m4v", ".avi"},
                "audio": {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"},
            }

            if extension not in allowed_extensions.get(data["type"], set()):
                return jsonify({"error": f"Unsupported {data['type']} file type"}), 400

            filename = f"{uuid.uuid4().hex}{extension}"
            filepath = os.path.join(upload_dir, filename)
            media_file.save(filepath)

            data["body_or_url"] = f"/uploads/{filename}"

        elif data["type"] in ("video", "audio") and not data["body_or_url"]:
            return jsonify({"error": "Upload a media file or provide a media URL"}), 400

    else:
        data = request.get_json(silent=True) or {}

    error = content_service.validate_content_payload(data)
    if error:
        return jsonify({"error": error}), 400

    item = content_service.create_content(data, current_user)

    return jsonify(item.to_dict()), 201


# UPDATE CONTENT

@content_bp.route(
    "/<int:content_id>",
    methods=["PATCH"]
)
@jwt_required()
def update_content(content_id):
    current_user = get_current_user()

    item = Content.query.get_or_404(
        content_id
    )

    # Only the author or an admin can update
    if (
        item.author_id != current_user.id
        and current_user.role != "admin"
    ):
        return jsonify({
            "error": "Forbidden"
        }), 403

    data = request.get_json() or {}

    item = content_service.update_content(
        item,
        data
    )

    return jsonify(
        item.to_dict()
    ), 200


# APPROVE CONTENT

@content_bp.route(
    "/<int:content_id>/approve",
    methods=["POST"]
)
@jwt_required()
def approve(content_id):
    current_user = get_current_user()

    if current_user.role not in ("admin", "writer"):
        return jsonify({
            "error": "Forbidden"
        }), 403

    item = Content.query.get_or_404(
        content_id
    )

    item = content_service.approve_content(
        item
    )

    return jsonify(
        item.to_dict()
    ), 200

# DELETE CONTENT

@content_bp.route(
    "/<int:content_id>",
    methods=["DELETE"]
)
@jwt_required()
def delete_content(content_id):
    current_user = get_current_user()

    if current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    item = Content.query.get_or_404(content_id)

    try:
        # Delete dependent records first so PostgreSQL foreign keys
        from models.reaction import Reaction
        from models.wishlist import Wishlist
        from models.report import Report

        Reaction.query.filter_by(content_id=content_id).delete(
            synchronize_session=False
        )
        Wishlist.query.filter_by(content_id=content_id).delete(
            synchronize_session=False
        )
        Report.query.filter_by(content_id=content_id).delete(
            synchronize_session=False
        )

        # Delete all comments belonging to the content, including replies.
        comments = Comment.query.filter_by(content_id=content_id).all()

        def delete_comment_tree(comment):
            for reply in list(comment.replies):
                delete_comment_tree(reply)
            db.session.delete(comment)

        top_level = [
            comment for comment in comments
            if comment.parent_comment_id is None
        ]

        for comment in top_level:
            delete_comment_tree(comment)

    
        deleted_ids = {comment.id for comment in comments}
        for comment in comments:
            if comment.id not in deleted_ids:
                db.session.delete(comment)

        db.session.delete(item)
        db.session.commit()

        # Remove uploaded media file after the database transaction succeeds.
        media_url = item.body_or_url
        if media_url and media_url.startswith("/uploads/"):
            filepath = os.path.join(
                current_app.root_path,
                media_url.lstrip("/")
            )
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
            except OSError:
                pass

        return jsonify({
            "message": "Content and related records deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("DELETE CONTENT ERROR")
        return jsonify({
            "error": "Failed to delete content",
            "details": str(e)
        }), 500
