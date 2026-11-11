import random
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import BANK_HANDLES, db, generate_upi_id
from models.behavior_model import upsert_behavior_profile
from models.user_model import create_user, get_user_by_email
from routes.wallet import serialize_document
from services.mail_service import (
    send_password_reset_otp,
    send_registration_otp,
    send_upi_pin_reset_otp,
)


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/request-registration-otp")
def request_registration_otp():
    payload = request.get_json() or {}
    required_fields = ["name", "email", "password", "upi_pin", "device_id"]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    upi_pin = str(payload.get("upi_pin", "")).strip()
    if not upi_pin.isdigit() or len(upi_pin) not in (4, 6):
        return jsonify({"error": "UPI PIN must be 4 or 6 digits"}), 400

    email = payload["email"].strip().lower()
    if get_user_by_email(email):
        return jsonify({"error": "User already exists"}), 409

    otp_code = f"{random.randint(0, 999999):06d}"
    preferred_handle = (payload.get("bank_handle") or "").strip().lower()
    generated_upi_id = generate_upi_id(email, preferred_handle)

    db.pending_registrations.update_one(
        {"email": email},
        {
            "$set": {
                "name": payload["name"].strip(),
                "email": email,
                "password": generate_password_hash(payload["password"]),
                "upi_pin_hash": generate_password_hash(upi_pin),
                "balance": float(payload.get("balance", 50000.0)),
                "generated_upi_id": generated_upi_id,
                "bank_handle": preferred_handle if preferred_handle in BANK_HANDLES else generated_upi_id.split("@")[1],
                "device_id": payload["device_id"].strip(),
                "otp_code": otp_code,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    mail_result = send_registration_otp(
        recipient_email=email,
        recipient_name=payload["name"].strip(),
        otp_code=otp_code,
        generated_upi_id=generated_upi_id,
    )
    if not mail_result["sent"]:
        return jsonify({"error": mail_result["message"]}), 500

    return jsonify(
        {
            "message": "OTP sent to your email",
            "email": email,
            "bank_handles": BANK_HANDLES,
        }
    )


@auth_bp.post("/verify-registration-otp")
def verify_registration_otp():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    otp_code = (payload.get("otp") or "").strip()

    if not email or not otp_code:
        return jsonify({"error": "Email and OTP are required"}), 400

    pending = db.pending_registrations.find_one({"email": email})
    if not pending:
        return jsonify({"error": "Registration session expired. Request a new OTP."}), 404
    if pending["expires_at"] < datetime.utcnow():
        db.pending_registrations.delete_one({"email": email})
        return jsonify({"error": "OTP expired. Request a new OTP."}), 400
    if pending["otp_code"] != otp_code:
        return jsonify({"error": "Invalid OTP"}), 400

    user = {
        "user_id": pending["generated_upi_id"],
        "name": pending["name"],
        "email": pending["email"],
        "password": pending["password"],
        "upi_pin_hash": pending["upi_pin_hash"],
        "balance": pending.get("balance", 50000.0),
        "primary_device_id": pending.get("device_id"),
        "created_at": datetime.utcnow(),
    }
    create_user(user)
    upsert_behavior_profile(
        user["user_id"],
        {
            "user_id": user["user_id"],
            "avg_amount": 0.0,
            "max_amount": 0.0,
            "usual_hours": [],
            "known_devices": [pending.get("device_id")] if pending.get("device_id") else [],
            "known_locations": [],
            "last_transaction_at": None,
            "recent_tx_timestamps": [],
            "total_transactions": 0,
            "last_device_id": pending.get("device_id"),
        },
    )
    db.pending_registrations.delete_one({"email": email})

    session["user_id"] = user["user_id"]
    return (
        jsonify(
            {
                "message": "Registration successful",
                "user": {
                    "user_id": user["user_id"],
                    "name": user["name"],
                    "email": user["email"],
                    "balance": user["balance"],
                    "primary_device_id": user.get("primary_device_id"),
                },
            }
        ),
        201,
    )


@auth_bp.post("/request-upi-pin-reset-otp")
def request_upi_pin_reset_otp():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    session_user_id = session.get("user_id")
    if not session_user_id:
        return jsonify({"error": "Authentication required"}), 401

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user["user_id"] != session_user_id:
        return jsonify({"error": "You can only reset the logged-in user's UPI PIN"}), 403

    otp_code = f"{random.randint(0, 999999):06d}"
    db.pending_pin_resets.update_one(
        {"email": email},
        {
            "$set": {
                "email": email,
                "user_id": user["user_id"],
                "otp_code": otp_code,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    mail_result = send_upi_pin_reset_otp(
        recipient_email=email,
        recipient_name=user["name"],
        otp_code=otp_code,
        user_id=user["user_id"],
    )
    if not mail_result["sent"]:
        return jsonify({"error": mail_result["message"]}), 500

    return jsonify({"message": "UPI PIN reset OTP sent", "email": email})


@auth_bp.post("/verify-upi-pin-reset-otp")
def verify_upi_pin_reset_otp():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    otp_code = (payload.get("otp") or "").strip()
    new_upi_pin = str(payload.get("new_upi_pin") or "").strip()

    if not email or not otp_code or not new_upi_pin:
        return jsonify({"error": "Email, OTP, and new UPI PIN are required"}), 400
    if not new_upi_pin.isdigit() or len(new_upi_pin) not in (4, 6):
        return jsonify({"error": "UPI PIN must be 4 or 6 digits"}), 400

    session_user_id = session.get("user_id")
    if not session_user_id:
        return jsonify({"error": "Authentication required"}), 401

    pending = db.pending_pin_resets.find_one({"email": email})
    if not pending:
        return jsonify({"error": "Reset session expired. Request a new OTP."}), 404
    if pending["expires_at"] < datetime.utcnow():
        db.pending_pin_resets.delete_one({"email": email})
        return jsonify({"error": "OTP expired. Request a new OTP."}), 400
    if pending["otp_code"] != otp_code:
        return jsonify({"error": "Invalid OTP"}), 400
    if pending["user_id"] != session_user_id:
        return jsonify({"error": "Reset session does not match the logged-in user"}), 403

    result = db.users.update_one(
        {"email": email},
        {"$set": {"upi_pin_hash": generate_password_hash(new_upi_pin)}},
    )
    db.pending_pin_resets.delete_one({"email": email})
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": "UPI PIN reset successful"})


@auth_bp.post("/request-password-reset-otp")
def request_password_reset_otp():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    otp_code = f"{random.randint(0, 999999):06d}"
    db.pending_password_resets.update_one(
        {"email": email},
        {
            "$set": {
                "email": email,
                "user_id": user["user_id"],
                "otp_code": otp_code,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    mail_result = send_password_reset_otp(
        recipient_email=email,
        recipient_name=user["name"],
        otp_code=otp_code,
        user_id=user["user_id"],
    )
    if not mail_result["sent"]:
        return jsonify({"error": mail_result["message"]}), 500

    return jsonify({"message": "Password reset OTP sent", "email": email})


@auth_bp.post("/verify-password-reset-otp")
def verify_password_reset_otp():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    otp_code = (payload.get("otp") or "").strip()
    new_password = payload.get("new_password") or ""

    if not email or not otp_code or not new_password:
        return jsonify({"error": "Email, OTP, and new password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    pending = db.pending_password_resets.find_one({"email": email})
    if not pending:
        return jsonify({"error": "Reset session expired. Request a new OTP."}), 404
    if pending["expires_at"] < datetime.utcnow():
        db.pending_password_resets.delete_one({"email": email})
        return jsonify({"error": "OTP expired. Request a new OTP."}), 400
    if pending["otp_code"] != otp_code:
        return jsonify({"error": "Invalid OTP"}), 400

    result = db.users.update_one(
        {"email": email},
        {"$set": {"password": generate_password_hash(new_password)}},
    )
    db.pending_password_resets.delete_one({"email": email})
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": "Password reset successful"})


@auth_bp.get("/bank-handles")
def bank_handles():
    return jsonify({"bank_handles": BANK_HANDLES})


@auth_bp.post("/login")
def login():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user["user_id"]
    return jsonify(
        {
            "message": "Login successful",
            "user": {
                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"],
                "balance": user["balance"],
                "primary_device_id": user.get("primary_device_id"),
            },
        }
    )


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False}), 401

    user = db.users.find_one({"user_id": user_id}, {"password": 0, "upi_pin_hash": 0})
    return jsonify({"authenticated": True, "user": serialize_document(user)})


@auth_bp.delete("/delete_account")
def delete_account():
    payload = request.get_json() or {}
    session_user_id = session.get("user_id")
    if not session_user_id:
        return jsonify({"error": "Authentication required"}), 401

    user_id = (payload.get("user_id") or "").strip().lower()
    password = payload.get("password") or ""
    upi_pin = str(payload.get("upi_pin") or "").strip()

    if not user_id or not password or not upi_pin:
        return jsonify({"error": "user_id, password, and UPI PIN are required"}), 400
    if user_id != session_user_id:
        return jsonify({"error": "You can only delete your own account"}), 403

    user = db.users.find_one({"user_id": session_user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid password"}), 401
    if not check_password_hash(user["upi_pin_hash"], upi_pin):
        return jsonify({"error": "Invalid UPI PIN"}), 401

    db.transactions.delete_many({"$or": [{"sender_id": session_user_id}, {"receiver_id": session_user_id}]})
    db.behavior_profiles.delete_one({"user_id": session_user_id})
    db.pending_registrations.delete_many({"email": user["email"]})
    db.users.delete_one({"user_id": session_user_id})
    session.clear()
    return jsonify({"message": "Account deleted permanently"})
