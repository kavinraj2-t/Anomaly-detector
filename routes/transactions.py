import random
from datetime import datetime, timedelta

from bson import ObjectId
from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from db import db
from models.transaction_model import get_transaction_history
from routes.wallet import login_required, serialize_document
from services.behavior_engine import update_behavior_profile
from services.mail_service import send_transaction_otp
from services.risk_engine import evaluate_transaction_risk


transactions_bp = Blueprint("transactions", __name__)


def build_transaction_record(sender_id, receiver_id, amount, device_id, device_label, location, evaluation, status=None, otp_verified=False):
    return {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount,
        "device_id": device_id,
        "device_label": device_label,
        "location": location,
        "status": status or ("success" if evaluation["decision"] == "allow" else ("otp_required" if evaluation["decision"] == "otp" else "blocked")),
        "risk_score": evaluation["risk_score"],
        "reasons": evaluation["reasons"],
        "decision": evaluation["decision"],
        "otp_verified": otp_verified,
        "created_at": datetime.utcnow(),
    }


@transactions_bp.post("/send_money")
@login_required
def send_money():
    payload = request.get_json() or {}
    sender_id = session["user_id"]
    recipient_identifier = (payload.get("recipient") or "").strip().lower()
    amount = float(payload.get("amount", 0))
    device_id = (payload.get("device_id") or "").strip()
    upi_pin = str(payload.get("upi_pin") or "").strip()
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    if not recipient_identifier or amount <= 0 or not device_id or not upi_pin:
        return jsonify({"error": "Recipient, amount, device ID, and UPI PIN are required"}), 400
    if latitude is None or longitude is None:
        return jsonify({"error": "Location permission is required to process the payment"}), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid geolocation coordinates"}), 400

    sender = db.users.find_one({"user_id": sender_id})
    receiver = db.users.find_one(
        {
            "$or": [
                {"user_id": recipient_identifier},
                {"name": {"$regex": f"^{recipient_identifier}$", "$options": "i"}},
            ]
        }
    )

    if not receiver:
        return jsonify({"error": "Recipient not found"}), 404
    if receiver["user_id"] == sender_id:
        return jsonify({"error": "You cannot pay yourself"}), 400
    if sender["balance"] < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    if not check_password_hash(sender["upi_pin_hash"], upi_pin):
        return jsonify({"error": "Invalid UPI PIN"}), 401

    location = {"latitude": latitude, "longitude": longitude}
    evaluation = evaluate_transaction_risk(
        sender_id=sender_id,
        amount=amount,
        device=device_id,
        location=location,
        transaction_time=datetime.utcnow(),
    )

    transaction = build_transaction_record(
        sender_id=sender_id,
        receiver_id=receiver["user_id"],
        amount=amount,
        device_id=device_id,
        device_label=payload.get("device_label") or "Browser device",
        location=location,
        evaluation=evaluation,
    )

    if evaluation["decision"] == "allow":
        db.users.update_one({"user_id": sender_id}, {"$inc": {"balance": -amount}})
        db.users.update_one({"user_id": receiver["user_id"]}, {"$inc": {"balance": amount}})
        update_behavior_profile(sender_id, transaction)
        insert_result = db.transactions.insert_one(transaction)
        transaction["_id"] = insert_result.inserted_id
    elif evaluation["decision"] == "otp":
        insert_result = db.transactions.insert_one(transaction)
        transaction["_id"] = insert_result.inserted_id
        otp_code = f"{random.randint(0, 999999):06d}"
        db.pending_transactions.update_one(
            {"transaction_id": str(insert_result.inserted_id)},
            {
                "$set": {
                    "transaction_id": str(insert_result.inserted_id),
                    "sender_id": sender_id,
                    "receiver_id": receiver["user_id"],
                    "amount": amount,
                    "device_id": device_id,
                    "device_label": payload.get("device_label") or "Browser device",
                    "location": location,
                    "otp_code": otp_code,
                    "expires_at": datetime.utcnow() + timedelta(minutes=10),
                    "created_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        mail_result = send_transaction_otp(
            recipient_email=sender["email"],
            recipient_name=sender["name"],
            otp_code=otp_code,
            amount=amount,
            receiver_id=receiver["user_id"],
        )
        if not mail_result["sent"]:
            db.transactions.update_one(
                {"_id": insert_result.inserted_id},
                {"$set": {"status": "otp_delivery_failed", "mail_error": mail_result["message"]}},
            )
            return jsonify({"error": mail_result["message"]}), 500
    else:
        insert_result = db.transactions.insert_one(transaction)
        transaction["_id"] = insert_result.inserted_id

    updated_sender = db.users.find_one({"user_id": sender_id}, {"password": 0, "upi_pin_hash": 0})
    response = {
        "transaction": serialize_document(transaction),
        "balance": round(updated_sender["balance"], 2),
        "recipient": {
            "user_id": receiver["user_id"],
            "name": receiver["name"],
        },
    }
    if evaluation["decision"] == "otp":
        response["otp_required"] = True
        response["transaction_id"] = str(transaction["_id"])
    return jsonify(response)


@transactions_bp.post("/confirm_transaction_otp")
@login_required
def confirm_transaction_otp():
    payload = request.get_json() or {}
    transaction_id = (payload.get("transaction_id") or "").strip()
    otp_code = (payload.get("otp") or "").strip()
    sender_id = session["user_id"]

    if not transaction_id or not otp_code:
        return jsonify({"error": "Transaction ID and OTP are required"}), 400

    pending = db.pending_transactions.find_one({"transaction_id": transaction_id})
    if not pending:
        return jsonify({"error": "OTP session expired. Start the payment again."}), 404
    if pending["sender_id"] != sender_id:
        return jsonify({"error": "This OTP does not belong to the logged-in user"}), 403
    if pending["expires_at"] < datetime.utcnow():
        db.pending_transactions.delete_one({"transaction_id": transaction_id})
        db.transactions.update_one({"_id": ObjectId(transaction_id)}, {"$set": {"status": "otp_expired"}})
        return jsonify({"error": "OTP expired. Start the payment again."}), 400
    if pending["otp_code"] != otp_code:
        return jsonify({"error": "Invalid OTP"}), 400

    sender = db.users.find_one({"user_id": sender_id})
    receiver = db.users.find_one({"user_id": pending["receiver_id"]})
    if not sender or not receiver:
        return jsonify({"error": "Sender or receiver no longer exists"}), 404
    if sender["balance"] < pending["amount"]:
        return jsonify({"error": "Insufficient balance at confirmation time"}), 400

    db.users.update_one({"user_id": sender_id}, {"$inc": {"balance": -pending["amount"]}})
    db.users.update_one({"user_id": receiver["user_id"]}, {"$inc": {"balance": pending["amount"]}})

    confirmed_transaction = db.transactions.find_one({"_id": ObjectId(transaction_id)})
    if not confirmed_transaction:
        return jsonify({"error": "Transaction record not found"}), 404

    db.transactions.update_one(
        {"_id": ObjectId(transaction_id)},
        {"$set": {"status": "success", "otp_verified": True, "verified_at": datetime.utcnow()}},
    )
    confirmed_transaction["status"] = "success"
    confirmed_transaction["otp_verified"] = True
    update_behavior_profile(sender_id, confirmed_transaction)
    db.pending_transactions.delete_one({"transaction_id": transaction_id})

    updated_sender = db.users.find_one({"user_id": sender_id}, {"password": 0, "upi_pin_hash": 0})
    return jsonify(
        {
            "message": "OTP verified and payment completed",
            "transaction": serialize_document(confirmed_transaction),
            "balance": round(updated_sender["balance"], 2),
        }
    )


@transactions_bp.get("/behavior")
@login_required
def behavior_snapshot():
    profile = db.behavior_profiles.find_one({"user_id": session["user_id"]})
    if not profile:
        return jsonify({"profile": None})
    return jsonify({"profile": serialize_document(profile)})


@transactions_bp.get("/transactions")
@login_required
def list_transactions():
    user_id = session["user_id"]
    transactions = get_transaction_history(user_id, 50)
    return jsonify({"transactions": serialize_document(transactions)})
