"""
Coupang scraper.

Coupang blocks requests pretty aggressively - even with realistic headers
I kept getting 403s or empty responses. Switched to Selenium.

That works, but it's slow and I've had it get rate-limited after ~50 pages
in a session. For now, keeping max_pages low and adding randomized delays.

TODO: Look into whether Coupang has an affiliate/partner API that would be
      cleaner to use. Might be worth applying for.
"""

import time
import random
import logging
from dataclasses import dataclass
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

BASE_URL = "https://www.coupang.com/np/search"


@dataclass
class CoupangProduct:
    title: str
    price: Optional[int]
    review_count: int
    rating: Optional[float]
    is_rocket: bool          # Rocket Delivery (로켓배송)
    is_rocket_fresh: bool    # Rocket Fresh (로켓프레시)
    link: str
    image_url: str = ""


def _make_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    # This helped avoid some bot detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def search(keyword: str, max_pages: int = 2, headless: bool = True) -> list[CoupangProduct]:
    """
    Search Coupang for a keyword using Selenium.

    Slower than the Naver scraper but necessary given Coupang's bot detection.
    """
    results: list[CoupangProduct] = []
    driver = _make_driver(headless=headless)

    try:
        for page in range(1, max_pages + 1):
            url = f"{BASE_URL}?q={keyword}&page={page}"
            driver.get(url)

            # Random delay - feels more human
            time.sleep(random.uniform(2.0, 4.0))

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.search-product"))
                )
            except TimeoutException:
                logger.warning(f"Coupang: page {page} timed out waiting for products.")
                break

            items = driver.find_elements(By.CSS_SELECTOR, "li.search-product")
            logger.info(f"Coupang page {page}: found {len(items)} items")

            for item in items:
                product = _parse_item(item)
                if product:
                    results.append(product)

            time.sleep(random.uniform(1.5, 3.0))

    except Exception as e:
        logger.error(f"Coupang scrape failed: {e}")
    finally:
        driver.quit()

    return results


def _parse_item(item) -> Optional[CoupangProduct]:
    """Parse a single search result item element."""
    try:
        title_el = item.find_element(By.CSS_SELECTOR, ".name")
        title = title_el.text.strip()

        link_el = item.find_element(By.CSS_SELECTOR, "a.search-product-link")
        href = link_el.get_attribute("href") or ""

        price = None
        try:
            price_el = item.find_element(By.CSS_SELECTOR, ".price-value")
            price = int(price_el.text.replace(",", ""))
        except (NoSuchElementException, ValueError):
            pass

        review_count = 0
        try:
            review_el = item.find_element(By.CSS_SELECTOR, ".rating-total-count")
            text = review_el.text.strip("()").replace(",", "")
            review_count = int(text) if text.isdigit() else 0
        except NoSuchElementException:
            pass

        rating = None
        try:
            rating_el = item.find_element(By.CSS_SELECTOR, ".rating")
            rating = float(rating_el.get_attribute("aria-label").split("점")[0].split()[-1])
        except (NoSuchElementException, ValueError, AttributeError):
            pass

        is_rocket = bool(item.find_elements(By.CSS_SELECTOR, ".badge.rocket"))
        is_rocket_fresh = bool(item.find_elements(By.CSS_SELECTOR, ".badge.rocket-fresh"))

        img_url = ""
        try:
            img_el = item.find_element(By.CSS_SELECTOR, "img.search-product-wrap-img")
            img_url = img_el.get_attribute("src") or ""
        except NoSuchElementException:
            pass

        return CoupangProduct(
            title=title,
            price=price,
            review_count=review_count,
            rating=rating,
            is_rocket=is_rocket,
            is_rocket_fresh=is_rocket_fresh,
            link=href,
            image_url=img_url,
        )
    except Exception as e:
        logger.debug(f"Failed to parse Coupang item: {e}")
        return None
