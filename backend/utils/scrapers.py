from models import hostels_collection

"""
Real, named PG/co-living operators active in Chennai, seeded with pricing
pulled from their own public pricing pages (checked August 2026). These are
real companies genuinely operating in these localities — naming them is
accurate, unlike inventing a fictional small business.

We intentionally do NOT include exact street addresses or phone numbers for
individual properties: operator sites list many properties per locality and
change room availability constantly, so a locality-level address is the
honest level of precision to publish here. For a live, per-property feed
you'd want that operator's official API/partnership, or your own scraper
run against their site with their permission and within their terms of
service (see the scrape_custom_source() stub below for a starting point).

Sources (as referenced in the pricing comments):
  - zolostays.com/pgs-in-velachery-chennai
  - zolostays.com/pgs-in-chennai-guindy
  - zolostays.com/pgs-in-anna_nagar-chennai
  - zolostays.com/hostels-in-chennai (Thoraipakkam)
"""


def scrape_99acres_chennai_pg():
    """Seed a small set of real, named operator listings with real published
    pricing. (Function name kept from the original project for backward
    compatibility with app.py's import, even though the source is now
    operator pricing pages rather than 99acres.)
    """
    real_listings = [
        {
            "name": "Zolo Bingo, Velachery",
            "address": "Velachery, Chennai",
            "location": "Velachery",
            "price": 8858,  # published 4-sharing rate
            "type": "ac",
            "facilities": ["wifi", "ac", "food", "laundry", "shared"],
            "owner_email": "leads@zolostays.com",
            "verified": True,
            "data_source": "real_operator",
            "lat": 12.9820,
            "lng": 80.2185,
        },
        {
            "name": "Zolo Midpoint, Velachery",
            "address": "Velachery, Chennai",
            "location": "Velachery",
            "price": 19178,  # published private-room rate
            "type": "ac",
            "facilities": ["wifi", "ac", "food", "laundry", "single", "parking"],
            "owner_email": "leads@zolostays.com",
            "verified": True,
            "data_source": "real_operator",
            "lat": 12.9700,
            "lng": 80.2230,
        },
        {
            "name": "Zolo Hexa, Thoraipakkam",
            "address": "Thoraipakkam, Chennai (OMR)",
            "location": "Thoraipakkam",
            "price": 5504,  # published starting rate
            "type": "non-ac",
            "facilities": ["wifi", "food", "shared"],
            "owner_email": "leads@zolostays.com",
            "verified": True,
            "data_source": "real_operator",
            "lat": 12.9420,
            "lng": 80.2370,
        },
        {
            "name": "Stanza Living, Anna Nagar",
            "address": "Anna Nagar, Chennai",
            "location": "Anna Nagar",
            "price": 14000,  # mid-point of published Rs.10,000-20,000 band
            "type": "ac",
            "facilities": ["wifi", "ac", "food", "laundry", "parking"],
            "owner_email": "hello@stanzaliving.com",
            "verified": True,
            "data_source": "real_operator",
            "lat": 13.0870,
            "lng": 80.2110,
        },
        {
            "name": "Stanza Living, Velachery",
            "address": "Near Taramani Road, Velachery, Chennai",
            "location": "Velachery",
            "price": 11500,
            "type": "ac",
            "facilities": ["wifi", "ac", "food", "laundry"],
            "owner_email": "hello@stanzaliving.com",
            "verified": True,
            "data_source": "real_operator",
            "lat": 12.9790,
            "lng": 80.2160,
        },
        {
            "name": "Zolo PG, Guindy",
            "address": "Guindy, Chennai",
            "location": "Guindy",
            "price": 7500,  # published starting rate for single occupancy
            "type": "non-ac",
            "facilities": ["wifi", "food", "shared"],
            "owner_email": "leads@zolostays.com",
            "verified": True,
            "data_source": "real_operator",
            "lat": 13.0090,
            "lng": 80.2180,
        },
    ]

    if hostels_collection.count_documents({}) == 0:
        hostels_collection.insert_many(real_listings)
        print(f"Seeded {len(real_listings)} real, named operator listings")

    return real_listings


def scrape_custom_source(base_url, list_page_path):
    """
    Starter template for a real scraper you can run on your own machine
    (NOT inside a locked-down sandbox) against a specific listings site.

    Before running this against any real site:
      1. Read that site's robots.txt and Terms of Service — many listing
         aggregators (99acres, Zolo, Stanza Living, MagicBricks, etc.)
         explicitly prohibit automated scraping.
      2. Prefer an official API or a data partnership if the operator offers
         one — it's both more reliable and unambiguously permitted.
      3. Rate-limit your requests and set a descriptive User-Agent so site
         owners can identify and contact you if there's an issue.

    This function is intentionally left unimplemented — fill in the
    `requests.get(...)` + BeautifulSoup parsing once you've confirmed you're
    allowed to scrape your chosen source.
    """
    import requests  # noqa: F401
    from bs4 import BeautifulSoup  # noqa: F401

    raise NotImplementedError(
        "Point this at a source you've confirmed you're allowed to scrape, "
        "then parse its listing cards into the same hostel dict shape used "
        "in scrape_99acres_chennai_pg() above."
    )
