from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models.report import Report
from models.content import Content
from routes.auth_helpers import get_current_user

report_bp = Blueprint("report", __name__, url_prefix="/api/reports")


def staff_only():
    user = get_current_user()
    if user.role not in ("admin", "writer"):
        return None, (jsonify({"error": "Forbidden"}), 403)
    return user, None


@report_bp.route("", methods=["POST"])
@jwt_required()
def file_report():
    current_user, error = staff_only()
    if error:
        return error

    data = request.get_json() or {}
    content_id = data.get("content_id")
    reason = (data.get("reason") or "").strip()
    if not content_id or not reason:
        return jsonify({"error": "content_id and reason are required"}), 400

    Content.query.get_or_404(content_id)
    report = Report(content_id=content_id, reporter_id=current_user.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    return jsonify(report.to_dict()), 201
    


@report_bp.route("", methods=["GET"])
@jwt_required()
def list_reports():
    _, error = staff_only()
    if error:
        return error

    status = request.args.get("status", "pending")
    if status not in ("pending", "resolved", "dismissed"):
        return jsonify({"error": "Invalid report status"}), 400

    reports = Report.query.filter_by(status=status).order_by(Report.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reports]), 200


@report_bp.route("/<int:report_id>/dismiss", methods=["POST"])
@jwt_required()
def dismiss_report(report_id):
    current_user, error = staff_only()
    if error:
        return error

    report = Report.query.get_or_404(report_id)
    report.status = "dismissed"
    report.resolved_by_id = current_user.id
    db.session.commit()
    return jsonify(report.to_dict()), 200


@report_bp.route("/<int:report_id>/resolve", methods=["POST"])
@jwt_required()
def resolve_report(report_id):
    current_user, error = staff_only()
    if error:
        return error

    report = Report.query.get_or_404(report_id)
    report.status = "resolved"
    report.resolved_by_id = current_user.id
    db.session.commit()

    return jsonify({
        "message": "Report resolved successfully",
        "report": report.to_dict(),
    }), 200
