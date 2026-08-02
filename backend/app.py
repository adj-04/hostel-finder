from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from models import hostels_collection, users_collection, reviews_collection, bookings_collection
from utils.generate_hostels import generate_hostels
from utils.scrapers import scrape_99acres_chennai_pg
from utils.geocode import geocode_address
from bson.objectid import ObjectId
import traceback
import time
import json
import uuid
import random
import string
import threading
from datetime import datetime, timezone

# Password hashing helpers (optional, but preferred)
try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:  # pragma: no cover - very unlikely in a Flask app
    generate_password_hash = None
    check_password_hash = None

app = Flask(__name__)
CORS(app)

# -------------------- REAL-TIME (SSE) STATE --------------------
# A simple monotonically increasing version counter. Any write endpoint that
# changes hostel/review data bumps this; the /stream_hostels SSE endpoint
# pushes the new version to connected clients so the UI can refresh live
# without the client needing to poll aggressively.
_data_lock = threading.Lock()
_data_version = {"v": 1, "ts": time.time()}

def bump_data_version():
    with _data_lock:
        _data_version["v"] += 1
        _data_version["ts"] = time.time()

# -------------------- DATABASE INIT --------------------
if hostels_collection.count_documents({}) == 0:
    try:
        scrape_99acres_chennai_pg()
    except Exception:
        traceback.print_exc()
    try:
        generate_hostels(50)
    except Exception:
        traceback.print_exc()

# -------------------- SERIALIZATION HELPERS --------------------
def serialize_hostel(h):
    h = dict(h)
    h["_id"] = str(h.get("_id"))
    facs = h.get("facilities")
    if facs is None:
        h["facilities"] = []
    elif isinstance(facs, str):
        h["facilities"] = [f.strip() for f in facs.split(",") if f.strip()]
    elif isinstance(facs, list):
        h["facilities"] = facs
    else:
        h["facilities"] = []
    if "ownerId" in h and not isinstance(h["ownerId"], str):
        h["ownerId"] = str(h["ownerId"])
    return h

def serialize_review(r):
    r = dict(r)
    r["_id"] = str(r.get("_id"))
    return r

# -------------------- ROUTES --------------------
@app.route("/get_all_reviews", methods=["GET"])
def get_all_reviews():
    try:
        reviews = list(reviews_collection.find({}))
        # Hide reviews that have been explicitly soft-deleted
        reviews = [r for r in reviews if r.get("status") != "deleted"]
        return jsonify([serialize_review(r) for r in reviews])
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error fetching reviews"}), 500

@app.route("/get_all_hostels", methods=["GET"])
def get_all_hostels():
    try:
        hostels = list(hostels_collection.find({}))
        return jsonify([serialize_hostel(h) for h in hostels])
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error fetching hostels"}), 500


@app.route("/admin_stats", methods=["GET"])
def admin_stats():
    """Aggregate admin statistics for dashboard widgets."""
    try:
        total_hostels = hostels_collection.count_documents({})
        total_users = users_collection.count_documents({})
        total_reviews = reviews_collection.count_documents({})
        pending_hostels = hostels_collection.count_documents({"verified": False})
        return jsonify({
            "total_hostels": total_hostels,
            "total_users": total_users,
            "total_reviews": total_reviews,
            "pending_hostels": pending_hostels,
        })
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error fetching admin stats"}), 500


@app.route("/get_hostels", methods=["POST", "GET"])
def get_hostels():
    try:
        # Get request data
        if request.method == "POST":
            data = request.get_json(force=True) or {}
        else:
            data = {
                "search": request.args.get("search", ""),
                "price": request.args.get("price", None),
                "features": request.args.getlist("features") or []
            }
        search = (data.get("search") or "").strip()
        price_val = data.get("price")
        max_price = float(price_val) if price_val not in (None, "", "null") else None
        features = data.get("features", []) or []
        if isinstance(features, str):
            features = [f.strip() for f in features.split(",") if f.strip()]

        # Base query
        query = {}
        if max_price is not None:
            query["price"] = {"$lte": max_price}

        # Fetch hostels
        hostels = list(hostels_collection.find(query))

        # Multi-term search (space-separated): each term must match name/location/facilities
        # Normalize/serialize once
        hostels = [serialize_hostel(h) for h in hostels]

        # Multi-term search: all tokens must match somewhere in name/location/facilities
        # Example: "tambaram ac" => hostels in Tambaram that also mention "ac" in type/facilities.
        if search:
            tokens = [t.strip().lower() for t in search.split() if t.strip()]
            if tokens:
                filtered = []
                for hs in hostels:
                    name = (hs.get("name") or "").lower()
                    location = (hs.get("location") or hs.get("address") or "").lower()
                    facs = hs.get("facilities") or []
                    if isinstance(facs, str):
                        facs = [f.strip() for f in facs.split(",") if f.strip()]
                    fac_text = " ".join(facs).lower()
                    haystack = " ".join([name, location, fac_text])
                    if all(tok in haystack for tok in tokens):
                        filtered.append(hs)
                hostels = filtered

        # Filter by features manually (facilities stored as list/string)
        if features:
            feats = [f.lower() for f in features]
            filtered = []
            for hs in hostels:
                h_fac = [f.strip().lower() for f in hs.get("facilities", [])]
                if all(f in h_fac for f in feats):
                    filtered.append(hs)
            hostels = filtered

        return jsonify(hostels)

    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error during /get_hostels"}), 500

@app.route("/get_hostel/<hostel_id>", methods=["GET"])
def get_single_hostel(hostel_id):
    try:
        # Try ObjectId, fall back to string
        query = {"_id": ObjectId(hostel_id)}
        h = hostels_collection.find_one(query)
        if not h:
            h = hostels_collection.find_one({"_id": str(hostel_id)})
        if not h:
            return jsonify({"error": "Not found"}), 404
        return jsonify(serialize_hostel(h))
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Invalid hostel id"}), 400

@app.route("/add_review", methods=["POST"])
def add_review():
    try:
        data = request.get_json(force=True) or {}
        hostel_id = data.get("hostelId")
        text = data.get("text", "")
        rating = int(data.get("rating", 0))
        user = data.get("user", "Anonymous")
        if not hostel_id:
            return jsonify({"success": False, "message": "hostelId required"}), 400
        review = {
            "hostel_id": str(hostel_id),
            "text": text,
            "rating": rating,
            "user": user,
            "status": "pending",
        }
        reviews_collection.insert_one(review)
        return jsonify({"success": True, "message": "Review added successfully!", "user": user})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error adding review"}), 500

@app.route("/get_reviews/<hostel_id>", methods=["GET"])
def get_reviews(hostel_id):
    try:
        reviews = list(reviews_collection.find({"hostel_id": str(hostel_id)}))
        # Only expose approved (or legacy unlabelled) reviews to students
        reviews = [r for r in reviews if r.get("status") in (None, "approved")]
        return jsonify([serialize_review(r) for r in reviews])
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error fetching reviews"}), 500

@app.route("/add_hostel", methods=["POST"])
def add_hostel():
    try:
        data = request.get_json(force=True) or {}
        owner_id = data.get("owner_id") or data.get("ownerId") or data.get("owner_email")
        if not owner_id:
            return jsonify({"success": False, "message": "owner_id required"}), 400
        facilities = data.get("facilities", [])
        if isinstance(facilities, str):
            facilities = [f.strip() for f in facilities.split(",") if f.strip()]

        # Validate and normalize price
        raw_price = data.get("price")
        try:
            price_value = float(raw_price)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid price. Please provide a numeric value."
            }), 400

        # Owners rarely know their lat/lng — geocode the real address they
        # typed via OpenStreetMap's Nominatim instead of guessing. Falls
        # back gracefully (None, None) if geocoding fails or is unreachable,
        # in which case the listing still saves — it just won't show a pin
        # on the map until an admin/owner sets coordinates manually.
        lat = data.get("lat")
        lng = data.get("lng")
        location_approx = False
        if lat in (None, "") or lng in (None, ""):
            address_text = data.get("address", "")
            geo_lat, geo_lng = geocode_address(address_text)
            if geo_lat is not None:
                lat, lng = geo_lat, geo_lng
            else:
                lat, lng = None, None
                location_approx = True

        hostel = {
            "name": data.get("name"),
            "address": data.get("address"),
            "price": price_value,
            "type": data.get("type"),
            "facilities": facilities,
            "ownerId": str(owner_id),
            "owner_email": data.get("owner_email"),
            "verified": False,
            "lat": lat,
            "lng": lng,
            "location_approx": location_approx,
            # Real, owner-submitted listing — never seed/sample data.
            "data_source": "owner_submitted",
        }
        result = hostels_collection.insert_one(hostel)
        bump_data_version()
        return jsonify({"success": True, "message": "Hostel added successfully!", "id": str(result.inserted_id)})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error adding hostel"}), 500

@app.route("/owner_hostels/<owner_id>", methods=["GET"])
def owner_hostels(owner_id):
    try:
        hostels = list(hostels_collection.find({"ownerId": str(owner_id)}))
        return jsonify([serialize_hostel(h) for h in hostels])
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error fetching owner hostels"}), 500

@app.route("/verify_hostel/<hostel_id>", methods=["POST"])
def verify_hostel(hostel_id):
    try:
        # Try ObjectId, fallback to string id
        try:
            res = hostels_collection.update_one({"_id": ObjectId(hostel_id)}, {"$set": {"verified": True}})
            modified = getattr(res, 'modified_count', 0)
        except Exception:
            modified = 0
        if not modified:
            res = hostels_collection.update_one({"_id": str(hostel_id)}, {"$set": {"verified": True}})
        bump_data_version()
        return jsonify({"success": True})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error verifying hostel"}), 500

@app.route("/delete_hostel/<hostel_id>", methods=["DELETE"])
def delete_hostel(hostel_id):
    try:
        try:
            hostels_collection.delete_one({"_id": ObjectId(hostel_id)})
        except Exception:
            hostels_collection.delete_one({"_id": str(hostel_id)})
        bump_data_version()
        return jsonify({"success": True})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error deleting hostel"}), 500


@app.route("/approve_review/<review_id>", methods=["POST"])
def approve_review(review_id):
    try:
        modified = 0
        try:
            res = reviews_collection.update_one({"_id": ObjectId(review_id)}, {"$set": {"status": "approved"}})
            modified = getattr(res, "modified_count", 0)
        except Exception:
            modified = 0
        if not modified:
            reviews_collection.update_one({"_id": str(review_id)}, {"$set": {"status": "approved"}})
        return jsonify({"success": True})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error approving review"}), 500


@app.route("/delete_review/<review_id>", methods=["DELETE"])
def delete_review(review_id):
    try:
        # Soft delete: mark as deleted so it no longer appears in lists
        modified = 0
        try:
            res = reviews_collection.update_one({"_id": ObjectId(review_id)}, {"$set": {"status": "deleted"}})
            modified = getattr(res, "modified_count", 0)
        except Exception:
            modified = 0
        if not modified:
            reviews_collection.update_one({"_id": str(review_id)}, {"$set": {"status": "deleted"}})
        return jsonify({"success": True})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error deleting review"}), 500

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email")
        password = data.get("password")
        if not email:
            return jsonify({"error": "Email required"}), 400
        if not password:
            return jsonify({"error": "Password required"}), 400
        if users_collection.find_one({"email": email}):
            return jsonify({"error": "Email already exists"}), 400

        # Prefer hashed passwords when Werkzeug is available
        if generate_password_hash is not None:
            password_hash = generate_password_hash(password)
            user_doc = {
                "name": data.get("name"),
                "email": email,
                "password_hash": password_hash,
                "role": data.get("role", "student"),
            }
        else:
            # Fallback: store plain password (legacy behaviour)
            user_doc = {
                "name": data.get("name"),
                "email": email,
                "password": password,
                "role": data.get("role", "student"),
            }

        result = users_collection.insert_one(user_doc)
        return jsonify({"success": True, "message": "User registered successfully!", "user_id": str(result.inserted_id)})
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error registering user"}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Invalid credentials"}), 400

        # Support both hashed and legacy plain-text passwords for backward compatibility
        is_valid = False
        stored_hash = user.get("password_hash")
        stored_plain = user.get("password")

        if stored_hash and check_password_hash is not None:
            try:
                is_valid = check_password_hash(stored_hash, password)
            except Exception:
                is_valid = False
        elif stored_plain is not None:
            is_valid = stored_plain == password

        if not is_valid:
            return jsonify({"error": "Invalid credentials"}), 400

        return jsonify({
            "success": True,
            "message": "Login successful!",
            "user": {
                "name": user.get("name"),
                "email": user.get("email"),
                "role": user.get("role", "student"),
                "user_id": str(user.get("_id"))
            }
        })
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error during login"}), 500

@app.route("/clear_sample_data", methods=["POST"])
def clear_sample_data():
    """Admin action: delete every listing that wasn't actually submitted by
    a real owner through the app (i.e. everything with data_source !=
    'owner_submitted' — both the generated sample listings and the seeded
    real-operator entries). Use this once you have enough genuine owner
    listings and want the dataset to be unambiguously 100% real.

    This has no auth check, same as the other admin_* endpoints in this
    demo — add real admin authentication before deploying this publicly.
    """
    try:
        all_docs = list(hostels_collection.find({}))
        to_delete = [
            h for h in all_docs
            if h.get("data_source", "owner_submitted") != "owner_submitted"
        ]
        deleted = 0
        for h in to_delete:
            try:
                hostels_collection.delete_one({"_id": ObjectId(h["_id"])})
            except Exception:
                hostels_collection.delete_one({"_id": str(h["_id"])})
            deleted += 1
        bump_data_version()
        return jsonify({"success": True, "deleted": deleted})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error clearing sample data"}), 500


@app.route("/get_locations", methods=["GET"])
def get_locations():
    """Return the distinct areas/localities currently in the dataset, used to
    power the location suggestion chips on the search bar."""
    try:
        hostels = list(hostels_collection.find({}))
        seen = {}
        for h in hostels:
            loc = (h.get("location") or "").strip()
            if not loc:
                # fall back to the first comma-separated part of the address
                addr = (h.get("address") or "").strip()
                loc = addr.split(",")[0].strip() if addr else ""
            if loc:
                key = loc.lower()
                seen[key] = seen.get(key, 0) + 1
        # Most common localities first
        ranked = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)
        locations = [k.title() for k, _ in ranked][:12]
        return jsonify(locations)
    except Exception:
        traceback.print_exc()
        return jsonify([])


@app.route("/stream_hostels")
def stream_hostels():
    """Server-Sent Events endpoint. Pushes the current data version every
    ~3s (and immediately whenever a write endpoint bumps it) so connected
    dashboards can refresh their listings in real time without hammering
    the REST endpoints with tight polling."""
    def gen():
        last_sent = None
        # initial hello so the client can confirm the connection is live
        yield f"event: hello\ndata: {json.dumps({'ts': time.time()})}\n\n"
        for _ in range(1200):  # ~1 hour per connection at 3s interval
            with _data_lock:
                v = _data_version["v"]
                ts = _data_version["ts"]
            if v != last_sent:
                yield f"event: update\ndata: {json.dumps({'version': v, 'ts': ts})}\n\n"
                last_sent = v
            else:
                yield f"event: heartbeat\ndata: {json.dumps({'ts': time.time()})}\n\n"
            time.sleep(3)
    return Response(gen(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


def _gen_order_id():
    return "HF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


@app.route("/create_booking", methods=["POST"])
def create_booking():
    """Persist a booking/payment record. This project does not move real
    money — card/UPI/bank details are validated for shape only and never
    stored in full (card numbers are masked) — but the booking itself is a
    real record the student and hostel owner can both see."""
    try:
        data = request.get_json(force=True) or {}
        hostel_id = data.get("hostel_id")
        user_id = data.get("user_id")
        if not hostel_id or not user_id:
            return jsonify({"success": False, "message": "hostel_id and user_id are required"}), 400

        try:
            amount = float(data.get("amount", 0))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Invalid amount"}), 400

        method = data.get("method", "card")
        detail = ""
        if method == "card":
            num = (data.get("card_last4") or "").strip()
            detail = f"Card ending {num}" if num else "Card"
        elif method == "upi":
            detail = data.get("upi_id", "UPI")
        elif method == "netbanking":
            detail = data.get("bank", "Net Banking")

        booking = {
            "hostel_id": str(hostel_id),
            "hostel_name": data.get("hostel_name", ""),
            "user_id": str(user_id),
            "user_name": data.get("user_name", ""),
            "amount": amount,
            "method": method,
            "detail": detail,
            "status": "paid",
            "order_id": _gen_order_id(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = bookings_collection.insert_one(booking)
        booking["_id"] = str(result.inserted_id)
        bump_data_version()
        return jsonify({"success": True, "booking": booking})
    except Exception:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error creating booking"}), 500


@app.route("/get_bookings/<user_id>", methods=["GET"])
def get_bookings(user_id):
    try:
        bookings = list(bookings_collection.find({"user_id": str(user_id)}))
        for b in bookings:
            b["_id"] = str(b.get("_id"))
        bookings.sort(key=lambda b: b.get("created_at", ""), reverse=True)
        return jsonify(bookings)
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error fetching bookings"}), 500


# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
