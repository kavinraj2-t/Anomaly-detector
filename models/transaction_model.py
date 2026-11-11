from db import db


def create_transaction(transaction_data):
    return db.transactions.insert_one(transaction_data)


def get_recent_transactions(user_id, limit=10):
    return list(
        db.transactions.find(
            {"$or": [{"sender_id": user_id}, {"receiver_id": user_id}]}
        )
        .sort("created_at", -1)
        .limit(limit)
    )


def get_transaction_history(user_id, limit=50):
    return list(
        db.transactions.find(
            {"$or": [{"sender_id": user_id}, {"receiver_id": user_id}]}
        )
        .sort("created_at", -1)
        .limit(limit)
    )
