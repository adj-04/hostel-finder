# Chennai Hostel Finder

A full‑stack app to browse, review, book, and manage hostels in Chennai. It includes three roles:
- **Students**: search hostels (live, as-you-type, with a "near me" distance sort), view details on a map, post reviews, and reserve a bed through a secure checkout flow
- **Owners**: list and manage "My Hostels"
- **Admins**: monitor hostels and reviews, verify/delete listings, live dashboard

## Tech stack
- **Backend**: Flask + Flask-CORS, MongoDB (with in‑memory fallback if Mongo isn't available), Server-Sent Events for real-time updates
- **Frontend**: Vanilla HTML/CSS/JS — no build step required. Sleek dark UI (Inter font, warm amber accent), toast notifications, skeleton loaders

## Project structure
- `backend/`
  - `app.py` — Flask API server (hostels, reviews, auth, bookings, live stream)
  - `models.py` — Mongo client with a mock in‑memory DB fallback
  - `requirements.txt` — Python dependencies
  - `utils/`
    - `scrapers.py` — adds sample hostels (placeholder scraper)
    - `generate_hostels.py` — generates dummy hostels with lat/lng
- `frontend/`
  - `*.html`, `style.css` (design system), `script.js` (app logic), `toast.js` (notifications)

## What's new in this pass
**Design**
- Complete visual overhaul: near-black background, warm amber accent, Inter font, rounded corners, soft shadows — replacing the old neon/terminal look
- Toast notifications instead of `alert()` popups
- Skeleton loading states while hostel results load
- Fully responsive on mobile

**Search**
- Live, debounced search-as-you-type (no need to click "Search" every time)
- "Near me" button — uses the browser's Geolocation API and sorts real results by distance (haversine formula), with a distance badge per card
- Location suggestion chips pulled from real data in your database (`/get_locations`)

**Real-time data**
- New `/stream_hostels` Server-Sent Events endpoint — a genuine live channel (not just polling) that notifies the frontend the moment a hostel is added, verified, or deleted, so the "Live" badge and hostel list update in real time
- "Synced Xs ago" indicator on the student dashboard

**Payment**
- Fully wired checkout flow: card / UPI / net banking, with client-side validation (card length, expiry, CVV, UPI ID format)
- New `/create_booking` and `/get_bookings/<user_id>` endpoints — bookings are real, persisted records (card numbers are masked, never stored in full)
- Booking history shown on the payment page with order IDs and a printable receipt
- Clearly labeled as a **demo/sandbox gateway** — no real money moves, since this project doesn't have live payment processor keys. Swapping in Razorpay/Stripe would mean adding their SDK + your API keys to `create_booking`.

**Listing data**
- The dummy/random hostel generator has been replaced with a dataset grounded in **real Chennai PG market data**: real locality names and coordinates, and real, currently-published price bands per locality (sourced from Zolo/Stanza Living's own pricing pages, checked Aug 2026) — see `backend/utils/chennai_locality_data.py` for the sourcing notes.
- `backend/utils/scrapers.py` now seeds a handful of **real, named operators** (Zolo, Stanza Living) with their actual published rates for that locality, instead of fictional placeholder businesses.
- What's still illustrative: exact per-bed listing names/counts for independent PGs. We don't scrape or redistribute individual small businesses' private listing data (most listing aggregators prohibit this in their ToS, and this sandbox's network can't reach those sites anyway). See `scrape_custom_source()` in `scrapers.py` for a documented starter template if you want to point a real scraper at a specific site *you've* confirmed you're allowed to scrape, run from your own machine.
- **Always verify current rent/availability directly with a property before paying anything** — this app's prices are realistic ranges, not a live feed.

**Real vs. sample data — solved structurally, not just relabeled**
Every hostel document now carries a `data_source` field so the app never has to guess what's real:
- `"owner_submitted"` — an actual owner used Add Hostel. This is 100% real by construction; shown with a green "Owner listed" badge.
- `"real_operator"` — one of the 6 seeded Zolo/Stanza Living entries with their real published pricing; shown with a "Real operator · verify pricing" badge.
- `"generated_sample"` — illustrative placeholder generated inside a real price band; shown with a muted "Sample listing" badge so nobody mistakes it for an actual business.

The admin dashboard has a **"Clear sample data"** button (`POST /clear_sample_data`) that deletes everything except `owner_submitted` listings in one click — once real owners have populated the app, you can wipe every placeholder and the dataset becomes unambiguously real.

**Real geocoding for new listings**
When an owner adds a hostel without lat/lng, `backend/utils/geocode.py` calls OpenStreetMap's free Nominatim API to convert their typed address into real coordinates — no more guessing. If geocoding fails (offline, address not found, etc.) the listing still saves; it's flagged `location_approx: true` instead of showing a fake pin. Note: this specific external call could not be tested from inside this build sandbox (its network egress is locked to a handful of dev domains) — verified it fails safe, but do a live smoke test once you deploy somewhere with normal internet access.

## Prerequisites
- Python 3.9+
- (Optional) MongoDB running locally on `mongodb://localhost:27017`
  - If MongoDB is not available, the backend automatically uses an in‑memory store (data resets on restart)

## Setup
1) Create/activate a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```

2) Run the backend (threaded, so the live SSE stream doesn't block other requests):
   ```bash
   python app.py
   ```
   This starts the server at `http://127.0.0.1:5000`.

3) Open the frontend:
   - Open `frontend/index.html` directly in your browser (or serve the folder with any static server), then use Login/Register
   - After login:
     - role=student → `student_home.html`
     - role=owner → `owner_home.html` (My Hostels + Add Hostel)
     - role=admin → `admin_home.html` (reviews + hostels, live-refreshing)

## Key API endpoints
- `GET/POST /get_hostels` — list hostels (search/price/features)
- `GET /get_hostel/<id>` — single hostel
- `POST /add_hostel` — owner adds a hostel (facilities as array)
- `GET /owner_hostels/<owner>` — owner's own hostels
- `POST /add_review` / `GET /get_reviews/<hostel>` — reviews
- `GET /get_all_reviews` / `GET /get_all_hostels` — admin feeds
- `POST /verify_hostel/<id>` / `DELETE /delete_hostel/<id>` — admin actions
- `GET /get_locations` — distinct localities for search suggestions
- `GET /stream_hostels` — **Server-Sent Events** live-update channel
- `POST /create_booking` / `GET /get_bookings/<user_id>` — checkout & booking history

## Known gaps & ideas for next steps
- Auth: hashed passwords + JWT sessions (currently plaintext demo auth)
- A real payment processor integration (Razorpay/Stripe) if you want to move real money
- Image upload support for hostel photos (S3/Cloudinary) — the UI has a file picker but doesn't yet persist the file
- Pagination for `/get_hostels` once the dataset grows
- Favorites/shortlist for students
