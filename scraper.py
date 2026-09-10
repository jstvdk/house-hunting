"""
House Hunter: scrapes Funda, Huurwoningen and Pararius for rental listings
matching the profiles in config.py, and emails you when new ones appear.

Usage:
    python scraper.py          # run all profiles, then repeat every
                                # POLL_INTERVAL_MINUTES forever
    python scraper.py --once   # run all profiles a single time and exit

See README.md for setup instructions.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import schedule
import json
import os
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

try:
    import config
except ImportError:
    sys.exit(
        "config.py not found. Copy config.example.py to config.py and edit "
        "it first:\n\n    cp config.example.py config.py\n"
    )

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# Email configuration - set these in your shell env or a local .env file (see .env.example)
SENDER_EMAIL = os.environ['SENDER_EMAIL']
RECEIVER_EMAIL = os.environ['RECEIVER_EMAIL']
MAILJET_API_KEY = os.environ['MAILJET_API_KEY']
MAILJET_SECRET_KEY = os.environ['MAILJET_SECRET_KEY']

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
)


def build_funda_url(areas):
    # Funda takes postcodes and city names as search areas and mixes them freely.
    # It silently caps at 100 areas, so keep any one query well under that.
    return (
        'https://www.funda.nl/zoeken/huur?selected_area=['
        + ','.join(f'%22{area}%22' for area in areas)
        + f']&price=%22{config.PRICE_MIN_EUR}-{config.PRICE_MAX_EUR}%22'
        + '&object_type=[%22house%22,%22apartment%22]'
        + f'&publication_date=%22{config.PUBLISHED_WITHIN_DAYS}%22'
        + f'&floor_area=%22{config.FLOOR_AREA_MIN_M2}-{config.FLOOR_AREA_MAX_M2}%22'
        + f'&rooms=%22{config.ROOMS_MIN}-{config.ROOMS_MAX}%22'
        + f'&bedrooms=%22{config.BEDROOMS_MIN}-{config.BEDROOMS_MAX}%22'
    )


def build_huurwoningen_urls(cities):
    # Huurwoningen has no postcode search - "/in/1011/" silently returns nationwide
    # results - so search per city and let the zipcode filter narrow it down.
    return [
        f'https://www.huurwoningen.com/in/{city}/?price={config.PRICE_MIN_EUR - 100}-{config.PRICE_MAX_EUR}'
        f'&living_size={config.FLOOR_AREA_MIN_M2}&since=3'
        for city in cities
    ]


def new_chrome_driver():
    options = Options()
    if config.HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={USER_AGENT}")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(90)  # never hang indefinitely on a dead/stalled browser
    return driver


# Function to parse and return listings from the page
# NOTE: Funda redesigned their search page (Tailwind-based, no more data-test-id
# attributes like "street-name-house-number"/"price-rent"/"object-image-link").
# The only stable hook left is the a[data-testid="listingDetailsAddress"] anchor.
def parse_listings_funda(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')

    address_links = soup.find_all('a', attrs={'data-testid': 'listingDetailsAddress'})
    result = []

    if not address_links:
        print("No listings found. Please check the HTML structure or class name.")
        return result

    # Loop through listings and collect relevant details
    for link_tag in address_links:
        # Extract the postal code and city (used downstream as "Address")
        location_tag = link_tag.find('div', class_='text-neutral-80')
        location = location_tag.get_text(strip=True) if location_tag else "Location not specified"

        # Extract the price (sibling block rendered just before the address anchor)
        price_container = link_tag.parent.find('div', class_='font-semibold') if link_tag.parent else None
        price_tag = price_container.find('div', class_='truncate') if price_container else None
        price = price_tag.get_text(strip=True) if price_tag else "Price not specified"

        # Extract the listing URL
        link = link_tag.get('href')
        if link:
            if not link.startswith('http'):
                link = "https://www.funda.nl" + link
        else:
            link = "URL not specified"

        # Extract the number of bedrooms and surface area from the feature list
        # that follows the address anchor (icon + text per <li>, no stable class name)
        bedrooms = 'Not specified'
        surface_area = 'Not specified'

        features_list = link_tag.find_next_sibling('ul')
        if features_list:
            for detail in features_list.find_all('li'):
                span = detail.find('span')
                text = span.get_text(strip=True) if span else detail.get_text(strip=True)
                if 'm²' in text:
                    surface_area = text
                elif text.isdigit():
                    bedrooms = text

        # Append listing details to result list
        result.append({
            "Address": location,
            "Price": price,
            "Rooms": bedrooms,
            "Surface Area": surface_area,
            "URL": link
        })

    return result

# Funda pagination is now driven by a "search_result=<page>" URL query param -
# there's no more clickable "Volgende" button in the rendered page.
def fetch_all_pages_funda(driver, base_url):
    listings = []
    page = 1
    while True:
        page_url = base_url if page == 1 else f"{base_url}&search_result={page}"
        if page > 1:
            driver.get(page_url)
            time.sleep(5)

        page_listings = parse_listings_funda(driver.page_source)
        if not page_listings:
            print("Reached the last page, no more pages to navigate.")
            break

        listings.extend(page_listings)
        page += 1
        if page > 50:  # safety cap against an accidental infinite loop
            print("Hit pagination safety cap (50 pages).")
            break
    return listings

# Main function to load cookies and fetch listings across multiple pages
def fetch_funda_with_pagination(url):
    driver = new_chrome_driver()

    # Load a generic URL first to load cookies
    driver.get("https://www.funda.nl")
    time.sleep(5)  # Wait for the page to load completely

    # Load cookies from a JSON file
    try:
        with open('funda_cookies.json', 'r') as cookies_file:
            cookies = json.load(cookies_file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        print("Cookies loaded successfully!")
    except Exception as e:
        print("Failed to load cookies:", e)
        driver.quit()
        return []

    # Refresh the page to apply cookies
    driver.get(url)
    time.sleep(5)  # Wait for the page to load completely
    print("Page loaded successfully! Title:", driver.title)

    # Fetch listings from all pages
    listings = fetch_all_pages_funda(driver, url)

    # Close the browser
    driver.quit()
    return listings


# Function to parse and return listings from the page
def parse_listings_huurwoningen(page_source, driver):
    soup = BeautifulSoup(page_source, 'html.parser')

    # Find all listing containers (assuming 'listing-search-item' is the class for listing containers)
    listings = soup.find_all('section', class_='listing-search-item')
    result = []

    if not listings:
        print("No listings found. Please check the HTML structure or class name.")
        return result

    # Loop through listings and collect relevant details
    for idx, listing in enumerate(listings):
        try:
            # Extract the address using Selenium XPath
            address_xpath = f"(//div[contains(@class, 'listing-search-item__sub-title')])[{idx+1}]"
            address_element = driver.find_element(By.XPATH, address_xpath)
            address = address_element.text.strip() if address_element else "Address not specified"
        except Exception:
            # Fallback to BeautifulSoup extraction
            address_tag = listing.find('div', class_='listing-search-item__sub-title')
            address = address_tag.get_text(strip=True) if address_tag else "Address not specified"

        # Extract the price
        price_tag = listing.find('div', class_='listing-search-item__price')
        price = price_tag.get_text(strip=True) if price_tag else "Price not specified"

        # Extract the listing URL
        link_tag = listing.find('a', class_='listing-search-item__link--title')
        if link_tag:
            link = link_tag['href']
            if not link.startswith('http'):
                link = "https://www.huurwoningen.com" + link
        else:
            link = "URL not specified"

        # Extract the number of rooms
        rooms_tag = listing.find('li', class_='illustrated-features__item--number-of-rooms')
        rooms = rooms_tag.get_text(strip=True) if rooms_tag else 'Not specified'

        # Extract the square meters (surface area)
        surface_area_tag = listing.find('li', class_='illustrated-features__item--surface-area')
        surface_area = surface_area_tag.get_text(strip=True) if surface_area_tag else 'Not specified'

        # Append listing details to result list
        result.append({
            "Address": address,
            "Price": price,
            "Rooms": rooms,
            "Surface Area": surface_area,
            "URL": link
        })

    return result

# Function to handle pagination by clicking the "Volgende" button
def fetch_all_pages_huurwoningen(driver):
    listings = []
    page = 0
    while True:
        # When a town has no listings at all, Huurwoningen serves a
        # "no search results" page filled with nationwide suggestions instead. Crawling
        # those just wastes minutes on listings the zipcode filter throws away.
        page_source = driver.page_source
        if 'no-search-results' in page_source:
            print("No listings for this area - skipping the suggested alternatives.")
            break

        # Parse the current page
        listings.extend(parse_listings_huurwoningen(page_source, driver))

        page += 1
        if page > 50:  # safety cap against an accidental infinite loop
            print("Hit pagination safety cap (50 pages).")
            break

        # Find the "Next" button using the arrow
        next_buttons = driver.find_elements(By.XPATH, '//li[@class="pagination__item pagination__item--next"]/a')

        # If the "Next" button is not found, break the loop (last page reached)
        if not next_buttons:
            print("Reached the last page, no more pages to navigate.")
            break

        try:
            # Scroll into view and click the button
            next_button = next_buttons[0]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", next_button)
            time.sleep(2)  # Pause to mimic human interaction

            # Click the "Next" button
            next_button.click()
            print("Next button clicked, moving to the next page...")
            time.sleep(5)  # Delay for page to load

        except Exception as e:
            print("An error occurred while clicking the 'Next' button:", e)
            break
    return listings

# Main function to load cookies and fetch listings across multiple pages
def fetch_huurwoningen_with_pagination(urls):
    # One search per city (no postcode search available), all in a single browser session.
    driver = new_chrome_driver()

    # Load a generic URL first to load cookies
    driver.get("https://www.huurwoningen.com")
    driver.implicitly_wait(6)  # Wait for the page to load

    try:
        # Wait for the button to be present and clickable
        essential_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
        )

        # Scroll into view to make sure it is visible
        driver.execute_script("arguments[0].scrollIntoView(true);", essential_button)

        # Attempt to click the button
        essential_button.click()
        print("Clicked on 'Alleen essentiële cookies' button.")
    except Exception as e:
        # Fallback to clicking using JavaScript in case standard click fails
        try:
            print("Standard click failed, trying JavaScript click.")
            essential_button = driver.find_element(By.ID, "onetrust-reject-all-handler")
            driver.execute_script("arguments[0].click();", essential_button)
            print("Clicked on 'Alleen essentiële cookies' button using JavaScript.")
        except Exception as js_e:
            print("Alleen essentiële cookies button not found or clickable after JavaScript attempt:", js_e)

    # Load cookies from a JSON file
    try:
        with open('huur_cookies.json', 'r') as cookies_file:
            cookies = json.load(cookies_file)
            for cookie in cookies:
                # Adjust the cookie format for Selenium
                cookie_dict = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie['path'],
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False)
                }
                if 'expirationDate' in cookie:
                    cookie_dict['expiry'] = int(cookie['expirationDate'])
                driver.add_cookie(cookie_dict)
        print("Cookies loaded successfully!")
    except Exception as e:
        print("Failed to load cookies:", e)
        driver.quit()
        return []

    # Search each city in turn, reusing the same session
    listings = []
    for url in urls:
        driver.get(url)
        driver.implicitly_wait(5)
        print("Page loaded successfully! Title:", driver.title)
        listings.extend(fetch_all_pages_huurwoningen(driver))

    # Close the browser
    driver.quit()
    return listings


# Function to parse and return listings from the page
def parse_listings_pararius(page_source, driver):
    soup = BeautifulSoup(page_source, 'html.parser')

    # Find all listing containers
    listings = soup.find_all('section', class_='listing-search-item')
    result = []

    if not listings:
        print("No listings found. Please check the HTML structure or class name.")
        return result

    # Loop through listings and collect relevant details
    for idx, listing in enumerate(listings):
        try:
            # Extract the address using Selenium XPath
            address_xpath = f"(//div[contains(@class, 'listing-search-item__sub-title')])[{idx+1}]"
            address_element = driver.find_element(By.XPATH, address_xpath)
            address = address_element.text.strip() if address_element else "Address not specified"
        except Exception:
            # Fallback to BeautifulSoup extraction
            address_tag = listing.find('div', class_='listing-search-item__sub-title')
            address = address_tag.get_text(strip=True) if address_tag else "Address not specified"

        # Extract the price
        price_tag = listing.find('div', class_='listing-search-item__price')
        price = price_tag.get_text(strip=True) if price_tag else "Price not specified"

        # Extract the listing URL
        link_tag = listing.find('a', class_='listing-search-item__link--title')
        if link_tag:
            link = link_tag['href']
            if not link.startswith('http'):
                link = "https://www.pararius.com" + link
        else:
            link = "URL not specified"

        # Extract the number of rooms
        rooms_tag = listing.find('li', class_='illustrated-features__item--number-of-rooms')
        rooms = rooms_tag.get_text(strip=True) if rooms_tag else 'Not specified'

        # Extract the square meters (surface area)
        surface_area_tag = listing.find('li', class_='illustrated-features__item--surface-area')
        surface_area = surface_area_tag.get_text(strip=True) if surface_area_tag else 'Not specified'

        # Append listing details to result list
        result.append({
            "Address": address,
            "Price": price,
            "Rooms": rooms,
            "Surface Area": surface_area,
            "URL": link
        })

    return result

# Function to handle pagination by clicking the "Volgende" button
def fetch_all_pages_pararius(driver):
    listings = []
    while True:
        # Parse the current page
        page_source = driver.page_source
        listings.extend(parse_listings_pararius(page_source, driver))

        # Find the "Next" button using the arrow
        next_buttons = driver.find_elements(By.XPATH, '//li[@class="pagination__item pagination__item--next"]/a')

        # If the "Next" button is not found, break the loop (last page reached)
        if not next_buttons:
            print("Reached the last page, no more pages to navigate.")
            break

        try:
            # Scroll into view and click the button
            next_button = next_buttons[0]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", next_button)
            time.sleep(2)  # Pause to mimic human interaction

            # Click the "Next" button
            next_button.click()
            print("Next button clicked, moving to the next page...")
            time.sleep(5)  # Delay for page to load

        except Exception as e:
            print("An error occurred while clicking the 'Next' button:", e)
            break
    return listings

# Main function to load cookies and fetch listings across multiple pages
def fetch_pararius_with_pagination(url):
    driver = new_chrome_driver()

    # Load a generic URL first to load cookies
    driver.get("https://www.pararius.com")
    time.sleep(5)  # Wait for the page to load completely

    # Load cookies from a JSON file
    try:
        with open('pararius_cookies.json', 'r') as cookies_file:
            cookies = json.load(cookies_file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        print("Cookies loaded successfully!")
    except Exception as e:
        print("Failed to load cookies:", e)
        driver.quit()
        return []

    # Refresh the page to apply cookies
    driver.get(url)
    time.sleep(5)  # Wait for the page to load completely
    print("Page loaded successfully! Title:", driver.title)

    # Fetch listings from all pages
    listings = fetch_all_pages_pararius(driver)

    # Close the browser
    driver.quit()
    return listings


def job(profile):
    start_time = time.time()
    print(f"=== Searching: {profile['name']} ===")

    zipcodes = profile['zipcodes']
    valid_zipcodes = set(zipcodes)

    master_list = fetch_funda_with_pagination(build_funda_url(profile['funda_areas']))
    master_list += fetch_huurwoningen_with_pagination(
        build_huurwoningen_urls(profile['huurwoningen_cities'])
    )
    if profile['pararius_url']:
        master_list += fetch_pararius_with_pagination(profile['pararius_url'])

    # Process master list
    cleaned_list = []
    for listing in master_list:
        # Extract numeric values from price, rooms, and surface area
        price = re.sub(r'[^\d]', '', listing['Price'])
        rooms = re.sub(r'[^\d]', '', listing['Rooms'])
        surface_area = re.sub(r'[^\d]', '', listing['Surface Area'])

        # Extract zip code from address
        address = listing['Address']
        zip_code = address[:4] if address[:4].isdigit() else ""

        # Only include listings with valid zip codes
        if zip_code in valid_zipcodes and price.isdigit() and int(price) <= config.MAX_PRICE_EUR:
            cleaned_list.append({
                "Zip Code": zip_code,
                "Address": address,
                "Price": int(price),
                "Rooms": int(rooms) if rooms.isdigit() else 0,
                "Surface Area": int(surface_area) if surface_area.isdigit() else 0,
                "URL": listing['URL']
            })

    # Check if cleaned_list is empty
    if not cleaned_list:
        print("No valid listings found.")
        return

    # Sort the cleaned list according to the specified criteria
    sorted_list = sorted(cleaned_list, key=lambda x: (
        -x['Rooms'],
        zipcodes.index(x['Zip Code']),
        x['Price'],
        -x['Surface Area']
    ))

    # Load the previous sorted list from file
    os.makedirs(os.path.dirname(profile['state_file']) or '.', exist_ok=True)
    try:
        with open(profile['state_file'], 'r') as file:
            previous_sorted_list = json.load(file)
    except FileNotFoundError:
        previous_sorted_list = []

    # Compare new sorted list to the previous sorted list
    new_entries = [entry for entry in sorted_list if entry not in previous_sorted_list]

    # If there are new entries, update the sorted list file and send an email
    if new_entries:
        print(f"{len(new_entries)} new listing(s), sending email")
        # Update the stored sorted list
        with open(profile['state_file'], 'w') as file:
            json.dump(sorted_list, file, indent=4)

        # Send email notification
        subject = f"New Rental Listings Available - {profile['name']}"
        body = "The following new rental listings have been found:\n\n"
        for entry in new_entries:
            body += f"Address: {entry['Address']}\nPrice: {entry['Price']}\nRooms: {entry['Rooms']}\nSurface Area: {entry['Surface Area']}\nURL: {entry['URL']}\n{'-' * 40}\n"

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            # Establish a secure session with Mailjet's SMTP server
            with smtplib.SMTP('in-v3.mailjet.com', 587) as server:
                server.starttls()  # Secure the connection using TLS
                server.login(MAILJET_API_KEY, MAILJET_SECRET_KEY)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")
    else:
        print("No new listings since last run.")

    # Print the total time taken
    end_time = time.time()
    print(f"Time taken to run the program: {end_time - start_time:.2f} seconds")


def run_all_profiles():
    for profile in config.SEARCH_PROFILES:
        job(profile)


if __name__ == '__main__':
    run_all_profiles()

    if '--once' not in sys.argv:
        schedule.every(config.POLL_INTERVAL_MINUTES).minutes.do(
            lambda: (print("restarting job now"), run_all_profiles())
        )
        while True:
            schedule.run_pending()
            time.sleep(1)
