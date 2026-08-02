"""
Data layer for the app. Backed by store.JSONCollection — plain JSON files
on disk under backend/data/. No external database (MongoDB or otherwise)
needs to be installed or running.
"""

from store import JSONCollection

hostels_collection = JSONCollection("hostels")
users_collection = JSONCollection("users")
reviews_collection = JSONCollection("reviews")
bookings_collection = JSONCollection("bookings")
