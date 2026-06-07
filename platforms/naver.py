"""
Naver Shopping scraper.

This one actually works without Selenium since Naver's search returns
parseable HTML even with basic requests headers. Took a while to figure
out the right headers to not get blocked.

Coupang is a different story - see coupang.py.
"""

import time
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://shopping.naver.com/",
}

BASE_URL = "https://search.shopping.naver.com/search/all"


@dataclass
class NaverProduct:
    title: str
    price: Optional[int]           # KRW, None if not available
    review_count: int
    rating: Optional[float]
    seller: str
    category: str
    link: str
    image_url: str = ""
    is_ad: bool = False            # flag sponsored listings


def search(keyword: str, sort: str = "review", max_pages: int = 3, delay: float = 1.5) -> list[NaverProduct]:
    """
    Search Naver Shopping for a keyword and return product listings.

    Args:
        keyword:   Search term (Korean or English)
        sort:      'review' | 'price_asc' | 'price_desc' | 'rank'
        max_pages: How many result pages to fetch (each has ~40 products)
        delay:     Seconds to wait between requests

    Returns:
        List of NaverProduct objects
    """
    sort_map = {
        "review":     "review",
        "price_asc":  "price_asc",
        "price_desc": "price_dsc",
        "rank":       "rel",
    }
    naver_sort = sort_map.get(sort, "review")
    results: list[NaverProduct] = []

    for page in range(1, max_pages + 1):
        params = {
            "query": keyword,
            "sort":  naver_sort,
            "pagingIndex": page,
            "pagingSize":  40,
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Naver request failed on page {page}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("li.product_item__MDtDF")  # class name as of early 2025

        if not items:
            # Naver sometimes changes class names - log a warning so I can fix it
            logger.warning(
                "No items found - Naver may have changed their HTML structure. "
                "Check and update the CSS selector."
            )
            break

        for item in items:
            product = _parse_item(item)
            if product:
                results.append(product)

        logger.info(f"Page {page}: collected {len(items)} items (total: {len(results)})")
        time.sleep(delay)

    return results


def _parse_item(item) -> Optional[NaverProduct]:
    """Parse a single product <li> element."""
    try:
        title_el = item.select_one(".product_title__Mmn7R a")
        title = title_el.get_text(strip=True) if title_el else ""
        link  = title_el["href"] if title_el else ""

        price_el = item.select_one(".price_num__S2p_v")
        price_text = price_el.get_text(strip=True).replace(",", "").replace("원", "") if price_el else ""
        price = int(price_text) if price_text.isdigit() else None

        review_el = item.select_one(".product_grade__Frprs em")
        review_count = int(review_el.get_text(strip=True).replace(",", "")) if review_el else 0

        rating_el = item.select_one(".product_grade__Frprs strong")
        rating_text = rating_el.get_text(strip=True) if rating_el else ""
        rating = float(rating_text) if rating_text else None

        seller_el = item.select_one(".product_mall_title__pO4Kh")
        seller = seller_el.get_text(strip=True) if seller_el else "unknown"

        category_el = item.select_one(".product_category__NCV2F")
        category = category_el.get_text(strip=True) if category_el else ""

        img_el = item.select_one("img.product_img__xHaWQ")
        image_url = img_el.get("src", "") if img_el else ""

        is_ad = bool(item.select_one(".product_ad_label__MQCRm"))

        return NaverProduct(
            title=title,
            price=price,
            review_count=review_count,
            rating=rating,
            seller=seller,
            category=category,
            link=link,
            image_url=image_url,
            is_ad=is_ad,
        )
    except Exception as e:
        logger.debug(f"Failed to parse item: {e}")
        return None
