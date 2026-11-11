# UPI Fraud Shield Simulator

A full-stack UPI-style payment simulation with Flask, MongoDB, email OTP onboarding, hashed UPI PINs, browser geolocation, device recognition, behavioral fraud detection, and secure account deletion.

## Features

- User registration and login with hashed passwords
- Email OTP onboarding with auto-generated UPI IDs
- Hashed UPI PIN creation during registration
- Wallet balance and add-money simulation
- Payment processing with UPI PIN verification before fraud evaluation
- Automatic browser geolocation capture using latitude and longitude
- Stable browser-generated device IDs stored and recognized by the backend
- Behavioral anomaly detection on amount, device, time, location distance, and frequency
- Explainable fraud outcomes: `Allow`, `OTP Required`, or `Blocked`
- Secure account deletion with password and UPI PIN confirmation
- Hidden seeded data with 3 users, balances, trusted devices, trusted locations, and behavior profiles

## Project Structure

```text
mongodb/
|- app.py
|- db.py
|- requirements.txt
|- README.md
|- models/
|  |- __init__.py
|  |- behavior_model.py
|  |- transaction_model.py
|  `- user_model.py
|- routes/
|  |- __init__.py
|  |- auth.py
|  |- transactions.py
|  `- wallet.py
|- services/
|  |- __init__.py
|  |- anomaly_detector.py
|  |- behavior_engine.py
|  |- mail_service.py
|  `- risk_engine.py
|- static/
|  |- app.js
|  `- styles.css
`- templates/
   `- index.html
```

## Realistic UPI Flow

### Registration

1. User enters name, email, password, UPI PIN, and bank handle.
2. Frontend attaches a generated browser `device_id`.
3. Backend emails an OTP.
4. After OTP verification, backend creates a UPI ID like `abc@okbb`.
5. Password and UPI PIN are stored as hashes.

### Payment

1. User enters recipient, amount, and UPI PIN.
2. Frontend requests browser geolocation permission.
3. Frontend sends `amount`, `device_id`, `device_label`, `latitude`, `longitude`, and `upi_pin`.
4. Backend validates UPI PIN.
5. Backend evaluates fraud risk and returns decision, risk score, and reasons.

### Account deletion

1. User opens the delete-account confirmation modal.
2. User confirms password and UPI PIN.
3. Backend deletes the user record, related transactions, and behavior profile.

## Fraud Detection Logic

Each outgoing payment is checked against a stored behavior profile:

- `avg_amount`: average outgoing transfer amount
- `max_amount`: historical maximum transfer
- `usual_hours`: common transaction hours
- `known_devices`: trusted device IDs
- `known_locations`: trusted latitude and longitude clusters
- `recent_tx_timestamps`: recent outgoing timestamps

### Risk weights

- Amount anomaly: `0.40`
- Device anomaly: `0.20`
- Time anomaly: `0.20`
- Location anomaly: `0.15`
- Frequency anomaly: `0.05`

### Decision rules

- Risk `> 0.80` -> `Blocked`
- Risk `0.50 to 0.80` -> `OTP Required`
- Risk `< 0.50` -> `Allowed`

## Local setup

### 1. Start MongoDB

MongoDB should be available at:

```text
mongodb://localhost:27017/
```

Optional overrides:

```powershell
$env:MONGO_URI="mongodb://localhost:27017/"
$env:MONGO_DB_NAME="upi_fraud_simulator"
```

### 2. Configure SMTP

```powershell
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="kajjnj05@gmail.com"
$env:SMTP_PASSWORD="mhbmslztdeudmwbh"
$env:SMTP_SENDER="kajjnj05@gmail.com"
```

### 3. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Run the app

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## API endpoints

### Auth

- `POST /api/auth/request-registration-otp`
- `POST /api/auth/verify-registration-otp`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/auth/bank-handles`
- `DELETE /api/auth/delete_account`

### Wallet

- `GET /api/balance`
- `POST /api/add_money`
- `GET /api/users`

### Transactions

- `POST /api/send_money`
- `GET /api/behavior`

## Seeded test data

The initial database bootstrap creates 3 hidden users with:

- Predefined wallet balances
- Hashed passwords
- Hashed UPI PINs
- Trusted device IDs
- Trusted geolocation clusters
- Existing transaction history
- Behavior profiles

These seeded accounts are not shown in the UI.

## Notes

- This project is fully simulated and does not connect to any real bank or UPI network.
- The transaction decision can still return `OTP Required` as a risk-based step-up action.
- Browser geolocation permission is required to submit a payment.
