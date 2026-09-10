"""
Opens Funda in a real Chrome window so you can pass any bot/CAPTCHA check
manually, then saves the resulting session cookies to funda_cookies.json
for scraper.py to reuse.

Run this once before your first scrape, and again whenever Funda starts
rejecting the scraper (cookies expire).
"""

import json
from selenium import webdriver
import time


def save_cookies(driver, filepath):
    cookies = driver.get_cookies()
    with open(filepath, 'w') as file:
        json.dump(cookies, file)
    print(f"Cookies saved to {filepath}")


def extract_funda_cookies():
    url = "https://www.funda.nl"

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    )

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    print("Accept any cookie banner / pass any check in the browser window...")
    time.sleep(10)

    save_cookies(driver, 'funda_cookies.json')
    driver.quit()


if __name__ == "__main__":
    extract_funda_cookies()
