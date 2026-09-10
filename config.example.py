"""
Search configuration for House Hunter.

Copy this file to config.py and edit it to match what you're looking for:

    cp config.example.py config.py

config.py is gitignored, so your personal search settings (areas, price
range, email address, ...) never get committed or shared.
"""

# --- Where to search -----------------------------------------------------
#
# House Hunter searches one city at a time. To search somewhere else,
# just edit the values below.

CITY = "Amsterdam"  # used in the email subject line

# Postcodes and/or city names for Funda to search (mixed freely, capped at
# ~100 entries by Funda itself). Dutch postcodes are 4 digits (a "PC4"),
# which lets you target specific neighbourhoods instead of a whole city -
# look up PC4 codes for the areas you want (e.g. via postcodetool.nl), or
# just use a city name like ["amsterdam"].
#
# Order also sets the preference order used to rank listings (earlier
# entries are ranked higher) - only used if you list multiple postcodes.
FUNDA_AREAS = (
    [str(z) for z in range(1011, 1019)]    # Centrum
    + [str(z) for z in range(1071, 1079)]  # Zuid + De Pijp
    + [str(z) for z in range(1051, 1059)]  # West incl. Bos en Lommer / De Baarsjes
    + [str(z) for z in range(1091, 1100)]  # Oost
    + ['1031', '1032', '1033']             # Noord: Overhoeks/Buiksloterweg, Buiksloterham, NDSM
)

# City slug as it appears in the huurwoningen.com URL, e.g. "amsterdam".
HUURWONINGEN_CITY = "amsterdam"

# City slug as it appears in the pararius.com URL, e.g. "amsterdam".
# Set to None to skip Pararius entirely.
PARARIUS_CITY = "amsterdam"

# Only listings whose postcode falls in this set are kept. Usually the
# same list as FUNDA_AREAS, but kept separate in case you search Funda by
# city name while still wanting to filter results down to specific
# postcodes.
ZIPCODES = FUNDA_AREAS

# Where "already seen" listings are stored, so you only get emailed about
# genuinely new ones.
STATE_FILE = "state/sorted_listings.json"

# --- Filters ---------------------------------------------------------------

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

# How often (in minutes) the continuous loop re-runs the search.
POLL_INTERVAL_MINUTES = 60

# Run Chrome without a visible window. Keep this False until you've
# confirmed your cookies and the page selectors still work - headless
# mode makes failures much harder to debug.
HEADLESS = False
