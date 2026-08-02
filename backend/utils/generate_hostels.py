import random
from models import hostels_collection
from utils.chennai_locality_data import LOCALITIES, FACILITY_TIERS


NAME_TEMPLATES = [
    "{loc} PG Residency",
    "{loc} Student Homes",
    "Comfort Stay {loc}",
    "{loc} Nest PG",
    "Sri Sannidhi PG, {loc}",
    "{loc} Scholars Hostel",
    "New Horizon PG {loc}",
    "{loc} Green Stay",
]


def generate_hostels(count=40):
    """Generate a realistic Chennai hostel/PG dataset.

    Unlike a purely random generator, this grounds every listing in a real
    locality (real lat/lng centroid) and a real, currently-published price
    band for that locality (see utils/chennai_locality_data.py for sourcing
    notes). Listing *names* here are still illustrative/generic — we don't
    fabricate exact street addresses or contact details for unverified real
    small businesses, since that would be misinformation rather than real
    data. For actual branded operators (Zolo, Stanza Living) see
    utils/scrapers.py, which seeds a few real, named entries with their
    published pricing.
    """
    hostels = []
    per_locality = max(1, count // len(LOCALITIES))

    for loc_name, lat, lng, min_price, max_price, tier in LOCALITIES:
        for _ in range(per_locality):
            price = random.randint(min_price, max_price)
            # Higher price within the band skews toward AC/attached extras
            price_ratio = (price - min_price) / max(1, (max_price - min_price))
            room_type = "ac" if price_ratio > 0.4 or tier == "premium" else "non-ac"

            base_facilities = set(FACILITY_TIERS[tier])
            if room_type == "ac":
                base_facilities.add("ac")
                base_facilities.discard("non-ac")
            extra_pool = ["parking", "laundry", "food", "single", "shared"]
            facilities = list(base_facilities | set(random.sample(extra_pool, k=random.randint(0, 2))))

            name = random.choice(NAME_TEMPLATES).format(loc=loc_name)
            # Realistic verification mix: most listings verified, a portion pending
            verified = random.random() < 0.7

            hostel = {
                "name": name,
                "address": f"{loc_name}, Chennai",
                "location": loc_name,
                "price": price,
                "type": room_type,
                "facilities": facilities,
                "owner_email": f"owner{len(hostels)+1}@example.com",
                "verified": verified,
                # small realistic jitter so pins don't all stack on one point
                "lat": lat + random.uniform(-0.01, 0.01),
                "lng": lng + random.uniform(-0.01, 0.01),
                # Illustrative seed data, not a real business — flagged so
                # the UI can show a "Sample listing" badge and so admins can
                # bulk-clear it once real owners start listing.
                "data_source": "generated_sample",
            }
            hostels.append(hostel)

    if hostels:
        hostels_collection.insert_many(hostels)
        print(f"Generated {len(hostels)} hostels grounded in real Chennai locality/price data")

    return hostels
