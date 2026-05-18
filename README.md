# WaziRide — WhatsApp & SMS Ride-Booking Backend

A production-shaped Python backend that lets people book rides over **WhatsApp**
(via Twilio) and **SMS** (via Twilio or Africa's Talking). No mobile app required.

This repo contains:

- FastAPI HTTP server
- Webhook endpoints for Twilio WhatsApp, Twilio SMS, and Africa's Talking SMS
- A conversation state machine that handles the full booking flow
- Geocoding (Google Maps if key set, otherwise a deterministic mock so it runs offline)
- Distance + fare estimation
- Driver matching (seeded mock drivers — swap with a real fleet API later)
- SQLite by default (zero setup); switch to Postgres via `DATABASE_URL`
- Admin/simulator endpoints so you can test the whole flow without paying for SMS

## Quick start (local, no external services)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs

### Test the bot without Twilio

Use the simulator endpoint — it talks to the same state machine the real webhooks use:

```bash
curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'content-type: application/json' \
  -d '{"phone":"+254700111222","body":"hi"}'

curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'content-type: application/json' \
  -d '{"phone":"+254700111222","body":"Westlands, Nairobi"}'

curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'content-type: application/json' \
  -d '{"phone":"+254700111222","body":"JKIA, Nairobi"}'

curl -s -X POST http://127.0.0.1:8000/admin/simulate \
  -H 'content-type: application/json' \
  -d '{"phone":"+254700111222","body":"YES"}'
```

## Conversation flow

```
User: hi                 -> "Welcome. Where to pick up?"
User: Westlands          -> "Pickup set. Where to?"
User: JKIA               -> "From .. To .. ~14km ~30min, Fare KES 1,250. YES/NO?"
User: YES                -> "Trip #1 confirmed. Driver John (KDB 123X) ⭐ 4.9 ..."
User: STATUS             -> current trip details
User: DONE               -> trip completed
User: CANCEL / SOS / HELP at any time
```

Pickup also accepts:
- A WhatsApp shared **location pin** (Twilio sends `Latitude` + `Longitude`)
- Raw `lat,lng` text like `-1.2921,36.8219`

## Connecting Twilio WhatsApp

1. Create a Twilio account, activate the WhatsApp **Sandbox** (free for dev).
2. Deploy this server somewhere with a public HTTPS URL
   (Render, Railway, Fly.io, or `ngrok http 8000` for local testing).
3. In the Twilio console → WhatsApp Sandbox settings, set
   **"WHEN A MESSAGE COMES IN"** to:
   ```
   POST https://YOUR_DOMAIN/webhooks/twilio/whatsapp
   ```
4. Fill in `.env`:
   ```
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```
5. From your phone, send `join <sandbox-code>` to the Twilio number, then `hi`.

For SMS via Twilio, point the SMS number's webhook at
`POST /webhooks/twilio/sms` and set `TWILIO_SMS_FROM`.

## Connecting Africa's Talking SMS

1. Create an AT account, get a sandbox username + API key (or a live shortcode).
2. In AT dashboard → SMS → Callback URLs:
   - **Incoming Messages**: `POST https://YOUR_DOMAIN/webhooks/africastalking/sms`
   - **Delivery Reports**:  `POST https://YOUR_DOMAIN/webhooks/africastalking/delivery`
3. Fill in `.env`:
   ```
   AT_USERNAME=sandbox        # or your live username
   AT_API_KEY=...
   AT_SMS_SHORTCODE=          # optional, your alphanumeric/short code
   ```

AT uses asynchronous replies (the webhook acks, and we send the bot reply
as a separate outbound SMS via the AT API), which is already wired up.

## Deploy

### Render / Railway / Fly.io
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set env vars from `.env.example`.
- For persistent data, set `DATABASE_URL` to a Postgres URL
  (e.g. `postgresql+asyncpg://user:pass@host/db`) and add `asyncpg` to requirements.

### Docker
```bash
docker build -t waziride .
docker run -p 8000:8000 --env-file .env waziride
```

## Repo layout

```
app/
  main.py                 FastAPI entry
  config.py               env-based settings
  db.py                   async SQLAlchemy engine + Base
  models/entities.py      User, Session, Driver, Trip
  bot/engine.py           conversation state machine (channel-agnostic)
  routers/
    whatsapp.py           Twilio WhatsApp + Twilio SMS webhooks (TwiML)
    africastalking.py     AT SMS webhook + delivery reports
    admin.py              /admin/simulate, /admin/trips, /admin/users, /admin/drivers
  services/
    geocoder.py           Google Maps or deterministic mock + haversine
    pricing.py            fare formula
    drivers.py            driver matching + seed data
    sms_at.py             outbound SMS via Africa's Talking
    sms_twilio.py         outbound WhatsApp/SMS via Twilio
tests/test_bot_flow.py    end-to-end booking flow test
```

## Next steps (when you're ready)

- Replace `services/drivers.py` with a real fleet/partner API (Uber, Bolt, Little).
- Add M-Pesa Daraja STK Push in a `services/payments.py` module and a new
  `awaiting_payment` state in `bot/engine.py`.
- Move `DATABASE_URL` to Postgres for production.
- Add Twilio signature validation on incoming webhooks for security.
- Add rate limiting (e.g. `slowapi`) per phone number.
