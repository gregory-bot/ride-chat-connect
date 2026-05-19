# WaziRide

**WhatsApp and SMS Ride-Booking Infrastructure for Africa**

WaziRide is a production-grade Python backend that enables ride booking entirely over WhatsApp and SMS — no mobile app required. It is designed for markets where app abandonment, limited device storage, and high data costs create a structural barrier between users and ride-hailing services.

---

## The Problem

Across Africa, WhatsApp penetration exceeds 97% of smartphone users, yet fewer than 35% have a ride-hailing app installed at any given time. The primary reason is not price — it is the friction of apps themselves.

- Ride-hailing apps occupy 150–300 MB of storage. On low-end and mid-range devices, they compete with the camera, M-Pesa, and WhatsApp. Users delete them.
- Loading a ride app over 2G or EDGE connections is unreliable. A WhatsApp message uses roughly 0.02 KES in data; an app session uses 50–100 times that.
- First-time app installation requires account creation, permissions, and onboarding. Every step is a drop-off point.

The digital ride economy was built for users with flagship smartphones and affordable data. A large portion of the market — rural users, older users, tourists, and low-storage device owners — is effectively excluded.

---

## The Solution

WaziRide moves the booking interface to where the users already are: WhatsApp and SMS.

A user sends a message to a WaziRide number. The system handles pickup location (shared pin or typed address), destination, fare estimation, driver matching, trip updates, and payment confirmation — all through a structured conversation. No app. No install. No account setup beyond a phone number.

This is not a consumer product. WaziRide is an infrastructure layer — a WhatsApp and SMS channel that any ride-hailing operator (Uber, Bolt, Little Cab, or an independent fleet) can connect to their existing dispatch API.

---

## Conversation Flow

```
User:  hi                   ->  "Welcome to WaziRide. Where should we pick you up?"
User:  Westlands, Nairobi   ->  "Pickup confirmed. Where are you going?"
User:  JKIA, Nairobi        ->  "From Westlands to JKIA. Approx. 14 km, 30 min. Fare: KES 1,250. Reply YES to confirm or NO to cancel."
User:  YES                  ->  "Trip confirmed. Driver: John M. — KDB 123X, Toyota Axio White. Rating: 4.9. Arriving in approx. 4 minutes."
User:  STATUS               ->  Current trip details and ETA
User:  DONE                 ->  Trip completed. Receipt sent.
User:  CANCEL               ->  Trip cancelled.
User:  SOS                  ->  Emergency alert with trip details.
User:  HELP                 ->  Command reference.
```

Pickup location also accepts:
- A WhatsApp shared location pin (Twilio forwards `Latitude` and `Longitude`)
- Raw coordinates in text: `-1.2921,36.8219`

---

## Architecture

```
User Device (WhatsApp / SMS)
        |
        v
WhatsApp Business API (Meta) or Africa's Talking / Twilio SMS
        |
        v
WaziRide Backend (FastAPI)
  - Conversation state machine
  - Geocoding (Google Maps API or deterministic offline mock)
  - Fare estimation (haversine distance + pricing formula)
  - Driver matching (mock fleet; replace with partner API)
        |
        v
Ride Operator API  (Uber, Bolt, Little, or custom fleet)
        |
        v
Driver assigned -> Trip updates -> Payment confirmation -> Receipt
        |
        v
All responses returned to user via WhatsApp or SMS
```

---

## Repository Layout

```
app/
  main.py                   FastAPI application entry point
  config.py                 Environment-based settings
  db.py                     Async SQLAlchemy engine and Base
  models/entities.py        User, Session, Driver, Trip models
  bot/engine.py             Channel-agnostic conversation state machine
  routers/
    whatsapp.py             Twilio WhatsApp + Twilio SMS webhooks (TwiML)
    africastalking.py       Africa's Talking SMS webhook + delivery reports
    admin.py                Simulator and admin endpoints
  services/
    geocoder.py             Google Maps geocoding or offline mock + haversine
    pricing.py              Fare calculation
    drivers.py              Driver matching and seeded mock data
    sms_at.py               Outbound SMS via Africa's Talking
    sms_twilio.py           Outbound WhatsApp and SMS via Twilio
tests/
  test_bot_flow.py          End-to-end booking flow integration test
```

---

## Quick Start (Local, No External Services)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

The geocoder runs in offline mock mode when no `GOOGLE_MAPS_API_KEY` is set, so the full booking flow works without any external API keys.

---

## Testing the Bot Without Twilio

The `/admin/simulate` endpoint runs messages through the same state machine the real webhooks use. No Twilio account or paid SMS required.

```bash
# Start a conversation
curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'Content-Type: application/json' \
  -d '{"phone": "+254700111222", "body": "hi"}'

# Set pickup location
curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'Content-Type: application/json' \
  -d '{"phone": "+254700111222", "body": "Westlands, Nairobi"}'

# Set destination
curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'Content-Type: application/json' \
  -d '{"phone": "+254700111222", "body": "JKIA, Nairobi"}'

# Confirm booking
curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'Content-Type: application/json' \
  -d '{"phone": "+254700111222", "body": "YES"}'
```

---

## Admin Endpoints

| Method | Endpoint              | Description                                      |
|--------|-----------------------|--------------------------------------------------|
| POST   | `/admin/simulate`     | Simulate a user message through the state machine |
| GET    | `/admin/trips`        | List all trips with status                       |
| GET    | `/admin/users`        | List registered users and session state          |
| GET    | `/admin/drivers`      | List seeded mock drivers                         |

---

## Webhook Endpoints

| Method | Endpoint                              | Provider              |
|--------|---------------------------------------|-----------------------|
| POST   | `/webhooks/twilio/whatsapp`           | Twilio WhatsApp       |
| POST   | `/webhooks/twilio/sms`                | Twilio SMS            |
| POST   | `/webhooks/africastalking/sms`        | Africa's Talking SMS  |
| POST   | `/webhooks/africastalking/delivery`   | AT delivery reports   |

---

## Connecting Twilio WhatsApp

1. Create a Twilio account and activate the WhatsApp Sandbox (free for development).
2. Deploy this server to a public HTTPS URL — Render, Railway, Fly.io, or `ngrok http 8000` for local testing.
3. In the Twilio Console, under WhatsApp Sandbox settings, set the incoming message webhook to:
   ```
   POST https://YOUR_DOMAIN/webhooks/twilio/whatsapp
   ```
4. Set the following variables in `.env`:
   ```
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```
5. From your phone, send `join <sandbox-code>` to the Twilio sandbox number, then send `hi`.

For Twilio SMS, point the SMS number's incoming webhook to `POST /webhooks/twilio/sms` and set `TWILIO_SMS_FROM`.

---

## Connecting Africa's Talking SMS

1. Create an Africa's Talking account. Obtain a sandbox username and API key, or configure a live shortcode.
2. In the AT dashboard under SMS > Callback URLs, set:
   - **Incoming Messages**: `POST https://YOUR_DOMAIN/webhooks/africastalking/sms`
   - **Delivery Reports**: `POST https://YOUR_DOMAIN/webhooks/africastalking/delivery`
3. Set the following variables in `.env`:
   ```
   AT_USERNAME=sandbox
   AT_API_KEY=...
   AT_SMS_SHORTCODE=
   ```

Africa's Talking uses asynchronous replies: the webhook acknowledges the inbound message immediately, and the bot reply is dispatched as a separate outbound SMS via the AT API.

---

## Environment Variables

```env
# Database (default: SQLite, zero setup)
DATABASE_URL=sqlite+aiosqlite:///./waziride.db

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_SMS_FROM=

# Africa's Talking
AT_USERNAME=sandbox
AT_API_KEY=
AT_SMS_SHORTCODE=

# Google Maps (optional — offline mock used if not set)
GOOGLE_MAPS_API_KEY=
```

---

## Deployment

### Render / Railway / Fly.io

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set environment variables from `.env.example`.
- For persistent storage, set `DATABASE_URL` to a PostgreSQL connection string
  and add `asyncpg` to `requirements.txt`.

### Docker

```bash
docker build -t waziride .
docker run -p 8000:8000 --env-file .env waziride
```

---

## Running Tests

```bash
pytest tests/test_bot_flow.py -v
```

The integration test covers the full booking sequence — greeting, pickup, destination, fare confirmation, driver assignment, and trip completion — using the in-process simulator with the SQLite database.

---

## Roadmap

- **Payments**: Integrate M-Pesa Daraja STK Push via a `services/payments.py` module and an `awaiting_payment` state in the bot engine.
- **Live fleet**: Replace `services/drivers.py` with a real partner API (Uber, Bolt, or Little Cab).
- **Production database**: Migrate `DATABASE_URL` to PostgreSQL.
- **Security**: Add Twilio webhook signature validation on all inbound routes.
- **Rate limiting**: Add per-phone-number rate limiting using `slowapi`.
- **Trip tracking**: Periodic WhatsApp status updates with map links during active trips.

---

## Market Context

The WhatsApp-first booking model is largely unoccupied. Uber ran limited pilots in India and Egypt but did not scale the product. No major African ride-hailing operator has a functioning WhatsApp booking channel. The infrastructure exists — WhatsApp Business Platform, M-Pesa WhatsApp Pay, and shared location — but no one has assembled it into a reliable booking layer.

WaziRide is designed as that layer: a licensable, operator-agnostic booking channel that any fleet can adopt without replacing their existing dispatch system.

---

## License

MIT