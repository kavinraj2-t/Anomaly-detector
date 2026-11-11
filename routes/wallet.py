from datetime import datetime
from functools import wraps

from bson import ObjectId
from flask import Blueprint, jsonify, request, session

from db import db
from models.transaction_model import get_recent_transactions


wallet_bp = Blueprint("wallet", __name__)


def serialize_document(document):
    if isinstance(document, list):
        return [serialize_document(item) for item in document]
    if not isinstance(document, dict):
        if isinstance(document, ObjectId):
            return str(document)
        if isinstance(document, datetime):
            return document.isoformat()
        return document

    output = {}
    for key, value in document.items():
        output[key] = serialize_document(value)
    return output


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


@wallet_bp.get("/balance")
@login_required
def get_balance():
    user = db.users.find_one({"user_id": session["user_id"]}, {"password": 0, "upi_pin_hash": 0})
    transactions = [serialize_document(tx) for tx in get_recent_transactions(user["user_id"], 8)]
    return jsonify(
        {
            "user": serialize_document(user),
            "balance": round(user["balance"], 2),
            "transactions": transactions,
        }
    )


@wallet_bp.post("/add_money")
@login_required
def add_money():
    payload = request.get_json() or {}
    amount = float(payload.get("amount", 0))
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    db.users.update_one({"user_id": session["user_id"]}, {"$inc": {"balance": amount}})
    user = db.users.find_one({"user_id": session["user_id"]}, {"password": 0, "upi_pin_hash": 0})
    return jsonify(
        {
            "message": "Money added successfully",
            "balance": round(user["balance"], 2),
        }
    )


@wallet_bp.get("/users")
@login_required
def list_users():
    current_user_id = session["user_id"]
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"users": []})

    users = list(
        db.users.find(
            {
                "$and": [
                    {"user_id": {"$ne": current_user_id}},
                    {
                        "$or": [
                            {"user_id": {"$regex": f"^{query}$", "$options": "i"}},
                            {"name": {"$regex": f"^{query}$", "$options": "i"}},
                        ]
                    },
                ]
            },
            {"password": 0, "upi_pin_hash": 0},
        ).limit(5)
    )
    return jsonify({"users": [serialize_document(user) for user in users]})
