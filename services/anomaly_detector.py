from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from services.behavior_engine import get_or_create_profile


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def location_distance(location_a, location_b):
    if not location_a or not location_b:
        return None
    if "latitude" not in location_a or "longitude" not in location_a:
        return None
    if "latitude" not in location_b or "longitude" not in location_b:
        return None
    return haversine_km(
        location_a["latitude"],
        location_a["longitude"],
        location_b["latitude"],
        location_b["longitude"],
    )


def detect_anomalies(sender_id, amount, device_id, location, transaction_time):
    profile = get_or_create_profile(sender_id)
    reasons = []
    metrics = {
        "amount_score": 0.0,
        "device_score": 0.0,
        "time_score": 0.0,
        "location_score": 0.0,
        "frequency_score": 0.0,
    }

    avg_amount = profile.get("avg_amount", 0.0)
    max_amount = profile.get("max_amount", 0.0)
    if avg_amount > 0:
        multiple = amount / avg_amount
        if multiple >= 5:
            metrics["amount_score"] = 1.0
            reasons.append(f"Amount {multiple:.1f}x higher than usual")
        elif multiple >= 3:
            metrics["amount_score"] = 0.7
            reasons.append(f"Amount {multiple:.1f}x above your average")
        elif multiple >= 1.75:
            metrics["amount_score"] = 0.35
            reasons.append("Amount noticeably above your average pattern")
    elif amount >= 10000:
        metrics["amount_score"] = 0.6
        reasons.append("Large first-time outgoing payment")

    if max_amount and amount > (max_amount * 1.5):
        metrics["amount_score"] = max(metrics["amount_score"], 0.85)
        reasons.append("Amount exceeds your historical maximum by a wide margin")

    known_devices = profile.get("known_devices", [])
    if known_devices and device_id not in known_devices:
        metrics["device_score"] = 1.0
        reasons.append("New or unrecognized device detected")
    elif not known_devices:
        metrics["device_score"] = 0.2
        reasons.append("No trusted device history yet")

    known_locations = profile.get("known_locations", [])
    if known_locations:
        distances = []
        for known_location in known_locations:
            distance = location_distance(location, known_location)
            if distance is not None:
                distances.append(distance)
        if distances:
            nearest_distance = min(distances)
            if nearest_distance >= 1000:
                metrics["location_score"] = 1.0
                reasons.append(f"Transaction is {nearest_distance:.0f} km away from usual locations")
            elif nearest_distance >= 250:
                metrics["location_score"] = 0.75
                reasons.append(f"Transaction is {nearest_distance:.0f} km away from your normal zone")
            elif nearest_distance >= 40:
                metrics["location_score"] = 0.4
                reasons.append("Transaction is outside your usual local area")
        else:
            metrics["location_score"] = 0.4
            reasons.append("Location could not be matched against trusted zones")
    else:
        metrics["location_score"] = 0.15
        reasons.append("Location baseline still forming")

    usual_hours = profile.get("usual_hours", [])
    current_hour = transaction_time.hour
    if usual_hours:
        nearest_gap = min(abs(current_hour - hour) for hour in usual_hours)
        if nearest_gap >= 8:
            metrics["time_score"] = 1.0
            reasons.append("Unusual transaction time")
        elif nearest_gap >= 4:
            metrics["time_score"] = 0.55
            reasons.append("Transaction time is outside your common hours")
    else:
        metrics["time_score"] = 0.1

    recent_timestamps = profile.get("recent_tx_timestamps", [])
    recent_count = sum(
        1 for timestamp in recent_timestamps if transaction_time - timestamp <= timedelta(minutes=15)
    )
    if recent_count >= 3:
        metrics["frequency_score"] = 1.0
        reasons.append("High payment frequency detected")
    elif recent_count >= 2:
        metrics["frequency_score"] = 0.6
        reasons.append("Rapid repeat payments detected")

    return {"profile": profile, "metrics": metrics, "reasons": reasons}
