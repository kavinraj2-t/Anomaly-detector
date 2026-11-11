import os
import random
import re
from datetime import datetime, timedelta
from statistics import mean

from pymongo import MongoClient
from werkzeug.security import generate_password_hash


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "upi_fraud_simulator")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

BANK_HANDLES = ["okbb", "okcc", "oksbi", "okhdfc", "okaxis"]
CITY_COORDS = {
    "bengaluru": {"latitude": 12.9716, "longitude": 77.5946, "city": "Bengaluru"},
    "mumbai": {"latitude": 19.076, "longitude": 72.8777, "city": "Mumbai"},
    "hyderabad": {"latitude": 17.385, "longitude": 78.4867, "city": "Hyderabad"},
    "delhi": {"latitude": 28.6139, "longitude": 77.209, "city": "Delhi"},
    "kolkata": {"latitude": 22.5726, "longitude": 88.3639, "city": "Kolkata"},
    "dubai": {"latitude": 25.2048, "longitude": 55.2708, "city": "Dubai"},
}


def initialize_database():
    db.users.create_index("email", unique=True)
    db.users.create_index("user_id", unique=True)
    db.transactions.create_index("created_at")
    db.behavior_profiles.create_index("user_id", unique=True)
    db.pending_registrations.create_index("email", unique=True)
    db.pending_registrations.create_index("expires_at", expireAfterSeconds=0)
    db.pending_pin_resets.create_index("email", unique=True)
    db.pending_pin_resets.create_index("expires_at", expireAfterSeconds=0)
    db.pending_password_resets.create_index("email", unique=True)
    db.pending_password_resets.create_index("expires_at", expireAfterSeconds=0)
    db.pending_transactions.create_index("transaction_id", unique=True)
    db.pending_transactions.create_index("expires_at", expireAfterSeconds=0)

    if db.users.count_documents({}) == 0:
        seed_sample_data()
    else:
        migrate_legacy_data()


def seed_sample_data():
    now = datetime.utcnow()
    users = [
        {
            "user_id": "krishna@okbb",
            "name": "Krishna Iyer",
            "email": "krishna@example.com",
            "password": generate_password_hash("password123"),
            "upi_pin_hash": generate_password_hash("1234"),
            "balance": 85000.0,
            "primary_device_id": "device-krishna-primary",
            "created_at": now,
        },
        {
            "user_id": "meera@okcc",
            "name": "Meera Shah",
            "email": "meera@example.com",
            "password": generate_password_hash("password123"),
            "upi_pin_hash": generate_password_hash("2345"),
            "balance": 64000.0,
            "primary_device_id": "device-meera-primary",
            "created_at": now,
        },
        {
            "user_id": "arjun@oksbi",
            "name": "Arjun Rao",
            "email": "arjun@example.com",
            "password": generate_password_hash("password123"),
            "upi_pin_hash": generate_password_hash("3456"),
            "balance": 72000.0,
            "primary_device_id": "device-arjun-primary",
            "created_at": now,
        },
    ]
    db.users.insert_many(users)

    seeded_transactions = [
        {
            "sender_id": "krishna@okbb",
            "receiver_id": "meera@okcc",
            "amount": 1200.0,
            "device_id": "device-krishna-primary",
            "device_label": "Krishna Pixel 8",
            "location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "city": "Bengaluru",
            },
            "status": "success",
            "risk_score": 0.08,
            "reasons": ["Trusted device recognized", "Inside known location radius"],
            "decision": "allow",
            "created_at": now - timedelta(days=3, hours=2),
        },
        {
            "sender_id": "krishna@okbb",
            "receiver_id": "arjun@oksbi",
            "amount": 2400.0,
            "device_id": "device-krishna-primary",
            "device_label": "Krishna Pixel 8",
            "location": {
                "latitude": 12.9698,
                "longitude": 77.6021,
                "city": "Bengaluru",
            },
            "status": "success",
            "risk_score": 0.11,
            "reasons": ["Known location cluster", "Expected amount range"],
            "decision": "allow",
            "created_at": now - timedelta(days=2, hours=3),
        },
        {
            "sender_id": "meera@okcc",
            "receiver_id": "krishna@okbb",
            "amount": 1800.0,
            "device_id": "device-meera-primary",
            "device_label": "Meera iPhone 14",
            "location": {
                "latitude": 19.076,
                "longitude": 72.8777,
                "city": "Mumbai",
            },
            "status": "success",
            "risk_score": 0.09,
            "reasons": ["Consistent amount pattern", "Trusted device recognized"],
            "decision": "allow",
            "created_at": now - timedelta(days=2, hours=6),
        },
        {
            "sender_id": "arjun@oksbi",
            "receiver_id": "meera@okcc",
            "amount": 3200.0,
            "device_id": "device-arjun-primary",
            "device_label": "Arjun OnePlus 12",
            "location": {
                "latitude": 17.385,
                "longitude": 78.4867,
                "city": "Hyderabad",
            },
            "status": "success",
            "risk_score": 0.14,
            "reasons": ["Known payee behavior", "Inside trusted zone"],
            "decision": "allow",
            "created_at": now - timedelta(days=1, hours=5),
        },
        {
            "sender_id": "krishna@okbb",
            "receiver_id": "meera@okcc",
            "amount": 900.0,
            "device_id": "device-krishna-primary",
            "device_label": "Krishna Pixel 8",
            "location": {
                "latitude": 12.9762,
                "longitude": 77.6033,
                "city": "Bengaluru",
            },
            "status": "success",
            "risk_score": 0.05,
            "reasons": ["Routine payment"],
            "decision": "allow",
            "created_at": now - timedelta(days=1, hours=1),
        },
    ]
    db.transactions.insert_many(seeded_transactions)

    for transaction in seeded_transactions:
        db.users.update_one(
            {"user_id": transaction["sender_id"]},
            {"$inc": {"balance": -transaction["amount"]}},
        )
        db.users.update_one(
            {"user_id": transaction["receiver_id"]},
            {"$inc": {"balance": transaction["amount"]}},
        )

    for user in users:
        user_id = user["user_id"]
        outgoing = list(
            db.transactions.find({"sender_id": user_id}).sort("created_at", 1)
        )
        if outgoing:
            amounts = [tx["amount"] for tx in outgoing]
            profile = {
                "user_id": user_id,
                "avg_amount": round(mean(amounts), 2),
                "max_amount": max(amounts),
                "usual_hours": sorted(list({tx["created_at"].hour for tx in outgoing})),
                "known_devices": sorted(list({tx["device_id"] for tx in outgoing})),
                "known_locations": [tx["location"] for tx in outgoing[-5:]],
                "last_transaction_at": outgoing[-1]["created_at"],
                "recent_tx_timestamps": [tx["created_at"] for tx in outgoing[-5:]],
                "total_transactions": len(outgoing),
                "last_device_id": outgoing[-1]["device_id"],
            }
        else:
            profile = {
                "user_id": user_id,
                "avg_amount": 0.0,
                "max_amount": 0.0,
                "usual_hours": [],
                "known_devices": [],
                "known_locations": [],
                "last_transaction_at": None,
                "recent_tx_timestamps": [],
                "total_transactions": 0,
                "last_device_id": None,
            }
        db.behavior_profiles.insert_one(profile)


def normalize_location(location):
    if isinstance(location, dict):
        return location
    if isinstance(location, str):
        return CITY_COORDS.get(location.strip().lower(), {"latitude": 0.0, "longitude": 0.0, "city": location})
    return {"latitude": 0.0, "longitude": 0.0}


def normalize_device_id(raw_device, user_id):
    if not raw_device:
        return f"device-{re.sub(r'[^a-z0-9]', '', user_id.lower()) or 'user'}-legacy"
    safe_value = re.sub(r"[^a-z0-9]+", "-", str(raw_device).lower()).strip("-")
    return f"device-{safe_value or 'legacy'}"


def migrate_legacy_data():
    for user in db.users.find({"upi_pin_hash": {"$exists": False}}):
        updates = {
            "upi_pin_hash": generate_password_hash("1234"),
            "primary_device_id": user.get("primary_device_id") or normalize_device_id(user.get("user_id"), user.get("user_id", "user")),
        }
        db.users.update_one({"_id": user["_id"]}, {"$set": updates})

    for transaction in db.transactions.find({"device_id": {"$exists": False}}):
        device_label = transaction.get("device") or "Legacy device"
        device_id = normalize_device_id(device_label, transaction.get("sender_id", "user"))
        location = normalize_location(transaction.get("location"))
        db.transactions.update_one(
            {"_id": transaction["_id"]},
            {
                "$set": {
                    "device_id": device_id,
                    "device_label": transaction.get("device_label") or device_label,
                    "location": location,
                },
                "$unset": {"device": ""},
            },
        )

    for profile in db.behavior_profiles.find({}):
        known_locations = [normalize_location(location) for location in profile.get("known_locations", [])]
        known_devices = [
            normalize_device_id(device, profile.get("user_id", "user"))
            for device in profile.get("known_devices", [])
        ]
        updates = {
            "known_locations": known_locations,
            "known_devices": sorted(list(set(known_devices))),
            "last_device_id": profile.get("last_device_id") or (known_devices[-1] if known_devices else None),
        }
        db.behavior_profiles.update_one({"_id": profile["_id"]}, {"$set": updates})


def generate_upi_id(email, preferred_handle=None):
    local_part = (email.split("@")[0] if email else "user").lower()
    local_part = re.sub(r"[^a-z0-9]", "", local_part)
    if not local_part:
        local_part = "user"

    handle = preferred_handle if preferred_handle in BANK_HANDLES else random.choice(BANK_HANDLES)
    base = f"{local_part}@{handle}"
    candidate = base
    suffix = 1

    while db.users.find_one({"user_id": candidate}):
        suffix += 1
        candidate = f"{local_part}{suffix}@{handle}"

    return candidate
