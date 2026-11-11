from statistics import mean

from db import db


def get_or_create_profile(user_id):
    profile = db.behavior_profiles.find_one({"user_id": user_id})
    if profile:
        return profile

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
    return profile


def append_unique_location(existing_locations, new_location, limit=10):
    locations = list(existing_locations or [])
    if not new_location:
        return locations[-limit:]

    is_duplicate = False
    for location in locations:
        if (
            round(location.get("latitude", 0), 3) == round(new_location.get("latitude", 0), 3)
            and round(location.get("longitude", 0), 3) == round(new_location.get("longitude", 0), 3)
        ):
            is_duplicate = True
            break

    if not is_duplicate:
        locations.append(new_location)
    return locations[-limit:]


def update_behavior_profile(user_id, transaction):
    profile = get_or_create_profile(user_id)
    previous_total = profile.get("total_transactions", 0)
    previous_avg = profile.get("avg_amount", 0.0)
    amount = transaction["amount"]

    if previous_total == 0:
        new_avg = amount
    else:
        new_avg = ((previous_avg * previous_total) + amount) / (previous_total + 1)

    hours = sorted(list(set(profile.get("usual_hours", []) + [transaction["created_at"].hour])))
    devices = sorted(list(set(profile.get("known_devices", []) + [transaction["device_id"]])))
    locations = append_unique_location(profile.get("known_locations", []), transaction["location"])
    timestamps = list(profile.get("recent_tx_timestamps", []))
    timestamps.append(transaction["created_at"])
    timestamps = timestamps[-10:]

    updated = {
        "avg_amount": round(new_avg, 2),
        "max_amount": max(profile.get("max_amount", 0.0), amount),
        "usual_hours": hours,
        "known_devices": devices,
        "known_locations": locations,
        "last_transaction_at": transaction["created_at"],
        "recent_tx_timestamps": timestamps,
        "total_transactions": previous_total + 1,
        "median_hint": round(mean([new_avg, amount]), 2),
        "last_device_id": transaction["device_id"],
    }
    db.behavior_profiles.update_one({"user_id": user_id}, {"$set": updated}, upsert=True)
    return db.behavior_profiles.find_one({"user_id": user_id})
