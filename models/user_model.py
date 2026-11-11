from db import db


def create_user(user_data):
    return db.users.insert_one(user_data)


def get_user_by_email(email):
    return db.users.find_one({"email": email})


def get_user_by_user_id(user_id):
    return db.users.find_one({"user_id": user_id})


def get_user_public_profile(user_id):
    return db.users.find_one(
        {"user_id": user_id},
        {"password": 0},
    )
