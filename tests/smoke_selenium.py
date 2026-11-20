"""Selenium smoke test against the canary: open the demo page, submit a ticket, expect a category.

Usage: BASE_URL=http://<ingress> VERSION=<canary version> python tests/smoke_selenium.py
Jenkins runs it after the canary is up. The `canary=always` cookie makes ingress-nginx send
this browser to the canary every time instead of 10% of the time.
"""
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

base = os.environ["BASE_URL"].rstrip("/")
expected = os.environ["VERSION"]

options = webdriver.ChromeOptions()
for arg in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1280,900"):
    options.add_argument(arg)
if os.getenv("CHROME_BIN"):  # set in the Jenkins image (Debian chromium)
    options.binary_location = os.environ["CHROME_BIN"]
service = Service(os.getenv("CHROMEDRIVER")) if os.getenv("CHROMEDRIVER") else Service()
driver = webdriver.Chrome(options=options, service=service)

try:
    driver.get(base + "/")
    driver.add_cookie({"name": "canary", "value": "always"})
    driver.get(base + "/")
    driver.find_element(By.ID, "ticket").send_keys("My order #482913 has not arrived yet and tracking is not updated")
    driver.find_element(By.ID, "submit").click()
    category = WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "category").text.strip())
    version = driver.find_element(By.ID, "version").text
    assert category in {"billing", "technical", "account", "shipping"}, f"unexpected category {category!r}"
    assert expected in version, f"answered by {version}, expected canary {expected}"
    print(f"smoke OK: category={category} version={version}")
finally:
    driver.quit()
