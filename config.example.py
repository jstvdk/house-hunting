"""
Search configuration for House Hunter.

Copy this file to config.py and edit it to match what you're looking for:

    cp config.example.py config.py

config.py is gitignored, so your personal search settings (areas, price
range, email address, ...) never get committed or shared.
"""

# --- Search profiles ---------------------------------------------------
#
# A "profile" is one independent search: its own areas, its own site
# queries, and its own state file (so results from different profiles
# never get mixed together or re-trigger emails for each other).
#
# funda_areas / zipcodes: Dutch postcodes are 4 digits (a "PC4"), and
# Funda lets you search by PC4 or by city name in the same query. Look up
# PC4 codes for the areas you want (e.g. via postcodetool.nl) or just use
# city names.
#
# Order within a profile's zipcodes is also the preference order used to
# rank listings (earlier entries are ranked higher).
AMSTERDAM_ZIPCODES = (
    [str(z) for z in range(1011, 1019)]    # Centrum
    + [str(z) for z in range(1071, 1079)]  # Zuid + De Pijp
    + [str(z) for z in range(1051, 1059)]  # West incl. Bos en Lommer / De Baarsjes
    + [str(z) for z in range(1091, 1100)]  # Oost
    + ['1031', '1032', '1033']             # Noord: Overhoeks/Buiksloterweg, Buiksloterham, NDSM
)

SEARCH_PROFILES = [
    {
        "name": "Amsterdam",
        # Postcodes and/or city names for Funda to search (mixed freely,
        # capped at ~100 entries by Funda itself).
        "funda_areas": AMSTERDAM_ZIPCODES,
        # City slugs as they appear in the huurwoningen.com URL.
        "huurwoningen_cities": ("amsterdam",),
        # Pararius has no postcode search, only one URL per profile.
        # Set to None to skip Pararius for this profile.
        "pararius_url": "https://www.pararius.com/apartments/amsterdam/apartment/900-2000/25m2/since-3",
        # Only listings whose postcode falls in this set are kept.
        "zipcodes": AMSTERDAM_ZIPCODES,
        # Where this profile's "already seen" listings are stored, so an
        # email only goes out for genuinely new listings.
        "state_file": "state/sorted_amsterdam.json",
    },
    # Add more profiles here, e.g. a second city or a "any of these towns"
    # search:
    # {
    #     "name": "Haarlem",
    #     "funda_areas": ("haarlem",),
    #     "huurwoningen_cities": ("haarlem",),
    #     "pararius_url": None,
    #     "zipcodes": [str(z) for z in range(2011, 2038)],
    #     "state_file": "state/sorted_haarlem.json",
    # },
]

# --- Filters (applied to every profile) --------------------------------

PRICE_MIN_EUR = 1000
PRICE_MAX_EUR = 2000
FLOOR_AREA_MIN_M2 = 40
FLOOR_AREA_MAX_M2 = 100
ROOMS_MIN = 0
ROOMS_MAX = 3
BEDROOMS_MIN = 0
BEDROOMS_MAX = 3

# Final safety cap applied after scraping, in case a site's own price
# filter lets something slightly over PRICE_MAX_EUR through.
MAX_PRICE_EUR = 2600

# Only look at listings published within the last N days (Funda's own
# "publication_date" filter).
PUBLISHED_WITHIN_DAYS = 5

# --- Run behaviour -------------------------------------------------------

# How often (in minutes) the continuous loop re-runs all profiles.
POLL_INTERVAL_MINUTES = 60

# Run Chrome without a visible window. Keep this False until you've
# confirmed your cookies and the page selectors still work - headless
# mode makes failures much harder to debug.
HEADLESS = False
