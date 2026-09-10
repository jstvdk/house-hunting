"""
Opens Huurwoningen in a real Chrome window so you can accept the cookie
banner manually, then saves the resulting session cookies to
huur_cookies.json for scraper.py to reuse.

Run this once before your first scrape, and again whenever Huurwoningen
stops returning results for the scraper (cookies expire).
"""

from selenium import webdriver
import json
import time

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)

driver.get("https://www.huurwoningen.com")

print("Please accept the cookies manually if prompted...")
time.sleep(15)  # Wait for cookies to be accepted (adjust if necessary)

cookies = driver.get_cookies()
with open("huur_cookies.json", "w") as file:
    json.dump(cookies, file)
    print("Cookies saved to huur_cookies.json")

driver.quit()
