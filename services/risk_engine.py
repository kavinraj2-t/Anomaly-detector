from services.anomaly_detector import detect_anomalies


WEIGHTS = {
    "amount_score": 0.4,
    "device_score": 0.2,
    "time_score": 0.2,
    "location_score": 0.15,
    "frequency_score": 0.05,
}


def evaluate_transaction_risk(sender_id, amount, device, location, transaction_time):
    detection = detect_anomalies(sender_id, amount, device, location, transaction_time)
    metrics = detection["metrics"]
    risk_score = sum(metrics[name] * weight for name, weight in WEIGHTS.items())
    risk_score = round(min(risk_score, 1.0), 2)

    if risk_score > 0.8:
        decision = "block"
        status = "blocked"
    elif risk_score >= 0.5:
        decision = "otp"
        status = "otp_required"
    else:
        decision = "allow"
        status = "success"

    reasons = detection["reasons"] or ["Pattern looks normal"]
    return {
        "risk_score": risk_score,
        "decision": decision,
        "status": status,
        "reasons": reasons,
        "metrics": metrics,
    }
