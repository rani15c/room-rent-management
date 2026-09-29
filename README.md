# StayNest PG and Room Management

A Flask and SQLite application for managing student accommodation, room inventory, owners, leases, and rent payments.

## Features

- Dashboard with occupancy and collected-rent summaries
- Owner and room records
- Student registration
- Lease creation that marks rooms occupied
- Rent payment ledger with month, method, and transaction reference
- SQLite database created automatically on first run

## Setup

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and change `SECRET_KEY` for real use.

4. Start the app:

   ```powershell
   python run.py
   ```

Open `http://127.0.0.1:5000` in your browser.

The database file is stored in the Flask instance folder as `instance/room_rent.db`.

## Online rent payments

The Payments page supports Razorpay Checkout in test mode. Create a Razorpay account, copy the test API keys, and add them to `.env`:

```env
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

Restart Flask. The `Pay online with Razorpay` button will create an order on the server, open Razorpay Checkout, verify the returned signature on the server, and only then mark the payment as `paid`. Without keys, manual payment recording remains available and online checkout stays disabled.
