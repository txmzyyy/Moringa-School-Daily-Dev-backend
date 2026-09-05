from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required
)

from services.auth_service import register_user, authenticate_user
from models.user import User
from extensions import db


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# SIGN UP

@auth_bp.post("/signup")
def signup():
    data = request.get_json() or {}

    # Required fields
    required_fields = [
        "first_name",
        "last_name",
        "email",
        "password"
    ]

    missing_fields = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return jsonify({
            "message": "Missing required fields",
            "fields": missing_fields
        }), 400

    try:
        user = register_user(
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            email=data["email"].strip().lower(),
            password=data["password"],
            role=data.get("role", "user")
        )

        token = create_access_token(
            identity=str(user.id)
        )

        return jsonify({
            "message": "User registered successfully",

            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": user.role
            },

            "token": token
        }), 201

    except ValueError as error:
        return jsonify({
            "message": str(error)
        }), 409

    except Exception as error:
        db.session.rollback()

        print("SIGNUP ERROR:", error)

        return jsonify({
            "message": "An error occurred while creating the account"
        }), 500


# LOGIN

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "message": "Email and password are required"
        }), 400

    user = authenticate_user(
        email.strip().lower(),
        password
    )

    if not user:
        return jsonify({
            "message": "Invalid email or password"
        }), 401

    access_token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "message": "Login successful",

        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role
        },

        "token": access_token
    }), 200


# CURRENT USER

@auth_bp.get("/me")
@jwt_required()
def current_user():
    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "message": "User not found"
        }), 404

    return jsonify({
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
    }), 200


# UPDATE PROFILE

@auth_bp.patch("/me")
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "message": "User not found"
        }), 404

    data = request.get_json() or {}

    if "first_name" in data:
        user.first_name = data["first_name"].strip()

    if "last_name" in data:
        user.last_name = data["last_name"].strip()

    if "email" in data:
        user.email = data["email"].strip().lower()

    try:
        db.session.commit()

        return jsonify({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }), 200

    except Exception as error:
        db.session.rollback()

        print("UPDATE PROFILE ERROR:", error)

        return jsonify({
            "message": "Failed to update profile"
        }), 500