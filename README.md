# House Hunter

Scrapes [Funda](https://www.funda.nl), [Huurwoningen](https://www.huurwoningen.com)
and [Pararius](https://www.pararius.com) for rental listings matching the
areas/price/size you're looking for, and emails you whenever a new one
shows up. Built for the Dutch rental market.

It keeps a "seen" list per search profile, so you only get emailed about
listings you haven't already been told about.

## How it works

1. Selenium drives a real Chrome window to each site (using saved cookies
   so you don't get blocked as a bot), and scrapes the search results.
2. Listings are filtered down to your configured postcodes and price cap.
3. The result is compared against the last run's saved list. Anything new
   triggers one email (via Mailjet's SMTP relay) listing all new matches.
4. By default it repeats every hour, forever.

## Setup

### 1. Requirements

- Python 3.10+
- Google Chrome installed
- [chromedriver](https://developer.chrome.com/docs/chromedriver) matching
  your Chrome version, on your `PATH` (Selenium 4.48 will usually
  auto-manage this for you, but if you hit driver errors, install it
  manually — on macOS: `brew install --cask chromedriver`)
- A free [Mailjet](https://www.mailjet.com/) account, to send the
  notification emails (their free tier is plenty for this)

### 2. Install

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure email

Mailjet gives you an API key + secret key that double as SMTP
username/password. In Mailjet, also verify a sender email address (under
Senders & Domains) — that's the address you'll use as `SENDER_EMAIL`.

```sh
cp .env.example .env
```

Edit `.env`:

```
SENDER_EMAIL=your_verified_sender@example.com
RECEIVER_EMAIL=you@example.com
MAILJET_API_KEY=...
MAILJET_SECRET_KEY=...
```

Test it:

```sh
python3 test_mailjet.py
```

You should get an email. If not, double check the sender address is
verified in Mailjet and the keys are correct.

### 4. Configure your search

```sh
cp config.example.py config.py
```

Edit `config.py`:

- `SEARCH_PROFILES` — one entry per city/area you want to search. Each
  profile has its own `funda_areas`/`huurwoningen_cities` (what to query
  the sites with), `zipcodes` (what to actually keep — also sets the
  ranking order, first = most preferred), and its own `state_file` so
  profiles don't interfere with each other.
- `PRICE_MIN_EUR` / `PRICE_MAX_EUR`, `FLOOR_AREA_MIN_M2` /
  `FLOOR_AREA_MAX_M2`, `ROOMS_MIN` / `ROOMS_MAX`, `BEDROOMS_MIN` /
  `BEDROOMS_MAX` — passed straight into the site search queries.
- `MAX_PRICE_EUR` — a final safety cap applied after scraping.
- `POLL_INTERVAL_MINUTES` — how often to re-check.
- `HEADLESS` — keep `False` until things are working; a visible browser
  makes it much easier to see what's going wrong.

### 5. Get cookies

Each site needs a valid cookie file so the scraper's requests look like a
normal logged-in browser instead of a bot. Run these once (a Chrome window
will open — accept the cookie banner / pass any check manually):

```sh
python3 get_funda_cookies.py
python3 get_huurwoningen_cookies.py
python3 get_pararius_cookies.py
```

This creates `funda_cookies.json`, `huur_cookies.json` and
`pararius_cookies.json` next to the scripts. Re-run the relevant script if
the scraper starts failing to load a site — cookies expire.

## Usage

Run once and exit (good for testing, or for running from `cron`):

```sh
python3 scraper.py --once
```

Run continuously (checks every `POLL_INTERVAL_MINUTES`, forever):

```sh
python3 scraper.py
```

Or, to have it auto-restart if it ever crashes:

```sh
sh run.sh
```

## Notes / known quirks

- Funda occasionally redesigns their site, which breaks the CSS
  selectors in `parse_listings_funda`. If Funda results silently stop
  showing up, that's the first thing to check — open the site in a
  browser, inspect a listing card, and update the selectors in
  `scraper.py`.
- Huurwoningen shows a generic "no results" page (with nationwide
  suggestions) for areas with zero listings, rather than an empty page.
  The scraper detects and skips this, but it means very quiet areas can
  look like a bug when they're not.
- None of the three sites offer a public API — this works by scraping
  rendered HTML, which is inherently a bit fragile. Keep expectations
  calibrated accordingly.
