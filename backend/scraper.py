"""Legacy scraper entry point.

This module is kept as a thin wrapper so that existing docs/commands
that call `python backend/scraper.py` continue to work. All real logic
lives in `backend/utils/scrapers.py` which integrates with the same
MongoDB/in-memory setup used by the main app.
"""

from utils.scrapers import scrape_99acres_chennai_pg


if __name__ == "__main__":
    scrape_99acres_chennai_pg()
