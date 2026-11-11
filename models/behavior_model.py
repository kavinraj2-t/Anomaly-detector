from db import db


def get_behavior_profile(user_id):
    return db.behavior_profiles.find_one({"user_id": user_id})


def upsert_behavior_profile(user_id, profile):
    db.behavior_profiles.update_one(
        {"user_id": user_id},
        {"$set": profile},
        upsert=True,
    )
