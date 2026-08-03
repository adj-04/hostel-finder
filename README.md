# Chennai Hostel Finder

A full-stack app for browsing, reviewing, and managing hostels in Chennai. There are three roles:

- **Students**-search hostels (live search, "near me" distance sort), view them on a map, post reviews, and book a bed through a checkout flow
- **Owners**-list and manage their own hostels
- **Admins**-review submissions, verify or delete listings, moderate reviews

## Tech stack

- **Backend**: Flask + Flask-CORS, a small JSON-file-backed data store (no external database needed), Server-Sent Events for live updates
- **Frontend**: plain HTML/CSS/JS, no build step, Leaflet for maps

## Project structure

- `backend/`
  - `app.py`-Flask API (hostels, reviews, auth, bookings, live stream)
  - `models.py` / `store.py`-the data layer: JSON files on disk instead of MongoDB
  - `auth.py`-signed-token auth for login and admin-only routes
  - `requirements.txt`-Python dependencies
  - `utils/`
    - `scrapers.py`-seeds a handful of real, named PG operators with real published rates
    - `generate_hostels.py`-generates additional sample listings within real price bands
    - `geocode.py`-turns an owner-typed address into real coordinates via OpenStreetMap's Nominatim
- `frontend/`
  - `*.html`, `style.css`, `script.js`, `toast.js`

## Data model

Every hostel record has a `data_source` field so the app always knows what's real:

- `owner_submitted`-added by a real owner through the app. Shown with an "Owner listed" badge.
- `real_operator`-one of the seeded Zolo/Stanza Living entries with their real published pricing. Shown as "Real operator-verify pricing."
- `generated_sample`-a placeholder listing generated inside a realistic price band. Shown as "Sample listing" so it's never mistaken for a real one.

The admin dashboard has a "Clear sample data" action that removes everything except `owner_submitted` listings, once there are enough real ones to not need the placeholders.

Prices reflect realistic ranges for the area, not a live feed-always confirm current rent and availability with the property directly before paying anything.

## Prerequisites

- Python 3.9+

That's it-no database server to install or run. Data is stored as JSON files under `backend/data/`, created automatically the first time the app runs.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```

2. (Recommended) Set a real secret key, used to sign login tokens:
   ```bash
   # macOS/Linux
   export SECRET_KEY="something-long-and-random"
   # Windows PowerShell
   $env:SECRET_KEY = "something-long-and-random"
   ```
   If you skip this, a hardcoded development key is used, which is fine for local testing but must not be used if you ever deploy this publicly.

3. Run the backend:
   ```bash
   python app.py
   ```
   This starts the server at `http://127.0.0.1:5000`.

4. Open the frontend:
   - Open `frontend/index.html` in your browser (or serve the folder with any static file server), then Login/Register
   - After login you're redirected by role:
     - student → `student_home.html`
     - owner → `owner_home.html` (My Hostels + Add Hostel)
     - admin → `admin_home.html`

## Auth

`/login` returns a signed token along with the user's info. The frontend stores it and sends it back as `Authorization: Bearer <token>` on requests that need it. Admin-only endpoints (`get_all_hostels`, `get_all_reviews`, `admin_stats`, `verify_hostel`, `delete_hostel`, `approve_review`, `delete_review`, `clear_sample_data`) check that token server-side and reject anything without a valid admin token-visiting `admin_home.html` directly, or editing `localStorage` to claim an admin role, no longer grants any access, since the check happens on the server, not the page.

Tokens expire after 12 hours. `/whoami` lets a page confirm a stored token is still valid before it renders.

## Key API endpoints

- `GET/POST /get_hostels`-list hostels (search/price/features)
- `GET /get_hostel/<id>`-single hostel
- `POST /add_hostel`-owner adds a hostel
- `GET /owner_hostels/<owner>`-an owner's own hostels
- `POST /add_review` / `GET /get_reviews/<hostel>`-reviews
- `POST /login` / `POST /register`-auth
- `GET /whoami`-check whether the current token is valid, and for which role
- `GET /get_all_reviews` / `GET /get_all_hostels` / `GET /admin_stats`-admin-only feeds
- `POST /verify_hostel/<id>` / `DELETE /delete_hostel/<id>`-admin-only actions
- `POST /approve_review/<id>` / `DELETE /delete_review/<id>`-admin-only actions
- `GET /get_locations`-distinct localities for search suggestions
- `GET /stream_hostels`-Server-Sent Events channel for live updates
- `POST /create_booking` / `GET /get_bookings/<user_id>`-checkout and booking history

## Known gaps and ideas for next steps

- Owner-only routes (`add_hostel`, `owner_hostels/<owner>`) still trust whatever `owner_id` the client sends, rather than checking it against the logged-in user's token-worth locking down the same way the admin routes now are
- Passwords are hashed on register/login, but there's no rate limiting on login attempts
- A real payment processor integration (Razorpay/Stripe) if this needs to move real money-right now bookings are recorded but no money actually moves
- Image upload support for hostel photos (S3/Cloudinary)-the UI has a file picker but doesn't persist the file yet
- Pagination for `/get_hostels` once the dataset grows
- Favorites/shortlist for students
