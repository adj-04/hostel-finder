"""
Real Chennai PG/hostel locality data.

Coordinates are real locality centroids. Price bands (min/max monthly rent
in INR) are grounded in live pricing pages from major managed-PG operators
(Zolo, Stanza Living) and PG aggregators, checked in August 2026:

  - Anna Nagar:  ~Rs.7,000 - Rs.20,000/month   (Stanza Living, Zolo)
  - Velachery:   ~Rs.7,000 - Rs.19,178/month   (Zolo — sharing Rs.8,858-11,610,
                                                  private Rs.19,178)
  - Guindy:      starts ~Rs.7,000/month         (Zolo)
  - City-wide:   Rs.4,500 - Rs.30,000+/month depending on locality/room type
                 (Zolo "Cost of PG in Chennai" market guide)
  - Cheapest localities called out: Teynampet, Medavakkam, Ambattur, Porur,
    Velachery, Arcot Road, OMR, Avadi, Tambaram, GST Road
  - Safest/premium localities called out: Adyar, Mylapore, Velachery,
    Besant Nagar

Other localities below (T. Nagar, Adyar, Tambaram, Porur, Sholinganallur /
OMR, Medavakkam, Ambattur, Perungudi, Nungambakkam, Mylapore, Besant Nagar)
use price bands interpolated from these published city-wide bands for
similar locality tiers (IT-corridor / premium / budget), since operators
don't publish a fixed number for every single micro-locality.

NOTE ON HONESTY: exact monthly rent for any single real bed changes with
sharing type, AC vs non-AC, and offers running that week — treat the bands
below as realistic ranges, not a live price feed. If you want a live feed,
you'd need a paid data agreement or your own scraper pointed at a specific
operator's site (see utils/scrapers.py for a starter script), run with that
operator's permission / within their terms of service.
"""

# (locality name, lat, lng, min_price, max_price, tier)
# tier: "budget" | "mid" | "premium" — used to bias which facilities get
# attached (premium => AC/attached-bath more likely, budget => fewer extras)
LOCALITIES = [
    ("Anna Nagar",     13.0850, 80.2101,  7000, 20000, "premium"),
    ("Velachery",      12.9759, 80.2200,  7000, 19000, "mid"),
    ("T. Nagar",       13.0418, 80.2341,  7000, 18000, "premium"),
    ("Guindy",         13.0067, 80.2206,  7000, 16000, "mid"),
    ("Adyar",          13.0067, 80.2560,  9000, 22000, "premium"),
    ("Besant Nagar",   13.0000, 80.2667,  9000, 20000, "premium"),
    ("Mylapore",       13.0339, 80.2619,  8000, 18000, "premium"),
    ("Nungambakkam",   13.0569, 80.2425,  6000, 14000, "mid"),
    ("Perungudi",      12.9698, 80.2422,  8000, 18000, "mid"),
    ("Sholinganallur", 12.9010, 80.2279,  6000, 15000, "mid"),
    ("Thoraipakkam",   12.9420, 80.2370,  5500, 14000, "mid"),
    ("Porur",          13.0381, 80.1565,  5000, 10000, "budget"),
    ("Tambaram",       12.9249, 80.1000,  4500,  9000, "budget"),
    ("Medavakkam",     12.9165, 80.1876,  4500,  8500, "budget"),
    ("Ambattur",       13.1143, 80.1548,  4500,  8500, "budget"),
]

FACILITY_TIERS = {
    "budget":  ["wifi", "shared", "non-ac"],
    "mid":     ["wifi", "food", "shared", "laundry"],
    "premium": ["wifi", "ac", "food", "laundry", "parking", "single"],
}
