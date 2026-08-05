"""
Web Scraper for Health Insurance Data
Extracts content from public domain US government health insurance websites.

Legal basis:
- All US federal government content is public domain (17 U.S.C. § 105)
- Healthcare.gov, Medicare.gov, CMS.gov are federal government websites
- No private/commercial company sites are scraped
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from pathlib import Path


# Rate limiting: be respectful to servers
REQUEST_DELAY = 2  # seconds between requests

# Navigation/footer patterns to remove
NAV_PATTERNS = [
    'skip to main content', 'skip navigation', 'menu', 'footer',
    'cookie', 'privacy policy', 'terms of use', 'sitemap',
    'follow us', 'social media', 'newsletter', 'subscribe',
    'back to top', 'breadcrumb', 'search', 'login', 'sign in'
]

# Elements to remove
REMOVE_TAGS = ['script', 'style', 'nav', 'footer', 'header', 'aside',
               'iframe', 'noscript', 'svg', 'form', 'button']

REMOVE_CLASSES = ['nav', 'navigation', 'menu', 'footer', 'header',
                  'sidebar', 'breadcrumb', 'social', 'cookie',
                  'banner', 'advertisement', 'ad-', 'share']


class HealthInsuranceScraper:
    """Scrapes health insurance content from US government public domain sources."""

    def __init__(self, output_dir: str = "knowledge_base/data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HealthInsuranceKB-Scraper/1.0 (Academic Research Project)'
        })
        self.scraped_data: List[Dict] = []

    def check_robots_txt(self, base_url: str) -> bool:
        """Check if scraping is allowed by robots.txt."""
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            resp = self.session.get(robots_url, timeout=10)
            if resp.status_code == 200:
                content = resp.text.lower()
                if 'disallow: /' in content and 'allow:' not in content:
                    print(f"⚠ robots.txt may restrict scraping at {base_url}")
                    return False
            return True
        except Exception as e:
            print(f"⚠ Could not check robots.txt for {base_url}: {e}")
            return True

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return parsed BeautifulSoup object."""
        try:
            print(f"📥 Fetching: {url}")
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return BeautifulSoup(resp.text, 'lxml')
        except requests.RequestException as e:
            print(f"❌ Failed to fetch {url}: {e}")
            return None

    def clean_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Remove navigation, headers, footers, scripts, and irrelevant elements."""
        for tag_name in REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        for class_pattern in REMOVE_CLASSES:
            for element in soup.find_all(class_=re.compile(class_pattern, re.I)):
                element.decompose()
            for element in soup.find_all(id=re.compile(class_pattern, re.I)):
                element.decompose()

        return soup

    def extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract clean text from parsed HTML."""
        soup = self.clean_soup(soup)

        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find(id=re.compile('content|main', re.I)) or
            soup.find(class_=re.compile('content|main|article', re.I)) or
            soup.find('body')
        )

        if not main_content:
            return ""

        lines = []
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'td', 'th', 'dt', 'dd']):
            text = element.get_text(strip=True)
            if not text or len(text) < 3:
                continue

            if any(pattern in text.lower() for pattern in NAV_PATTERNS):
                continue

            if element.name in ['h1', 'h2', 'h3', 'h4']:
                prefix = '#' * int(element.name[1])
                lines.append(f"\n{prefix} {text}\n")
            elif element.name == 'li':
                lines.append(f"• {text}")
            else:
                lines.append(text)

        content = '\n'.join(lines)
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()

    def scrape_healthcare_gov(self) -> List[Dict]:
        """Scrape Healthcare.gov public pages (US federal government, public domain)."""
        records = []
        pages = {
            "glossary": {
                "url": "https://www.healthcare.gov/glossary/",
                "category": "glossary",
                "title_prefix": "Health Insurance Glossary"
            },
            "plan_categories": {
                "url": "https://www.healthcare.gov/choose-a-plan/plan-categories/",
                "category": "product_plans",
                "title_prefix": "Plan Categories"
            },
            "how_marketplace_works": {
                "url": "https://www.healthcare.gov/how-does-the-marketplace-work/",
                "category": "enrollment",
                "title_prefix": "How the Marketplace Works"
            },
            "coverage": {
                "url": "https://www.healthcare.gov/coverage/",
                "category": "coverage",
                "title_prefix": "Health Coverage Options"
            },
            "preventive_care": {
                "url": "https://www.healthcare.gov/coverage/preventive-care-benefits/",
                "category": "preventive_care",
                "title_prefix": "Preventive Care Benefits"
            },
            "costs": {
                "url": "https://www.healthcare.gov/lower-costs/",
                "category": "costs_pricing",
                "title_prefix": "Lowering Health Insurance Costs"
            },
            "getting_coverage": {
                "url": "https://www.healthcare.gov/get-coverage/",
                "category": "enrollment",
                "title_prefix": "Getting Health Coverage"
            },
            "quick_guide": {
                "url": "https://www.healthcare.gov/quick-guide/",
                "category": "faq",
                "title_prefix": "Quick Guide to the Marketplace"
            },
        }

        self.check_robots_txt("https://www.healthcare.gov")

        for page_id, page_info in pages.items():
            soup = self.fetch_page(page_info["url"])
            if soup:
                content = self.extract_text_content(soup)
                if content and len(content) > 50:
                    records.append({
                        "id": f"hcgov_{page_id}",
                        "title": page_info["title_prefix"],
                        "content": content,
                        "category": page_info["category"],
                        "source": "healthcare.gov",
                        "source_url": page_info["url"]
                    })
                    print(f"  ✅ Extracted {len(content)} chars from {page_id}")
                else:
                    print(f"  ⚠ Insufficient content from {page_id}")

        return records

    def scrape_medicare_gov(self) -> List[Dict]:
        """Scrape Medicare.gov public pages (US federal government, public domain)."""
        records = []
        pages = {
            "eligibility": {
                "url": "https://www.medicare.gov/basics/get-started-with-medicare",
                "category": "eligibility",
                "title_prefix": "Medicare Eligibility & Getting Started"
            },
            "what_covers": {
                "url": "https://www.medicare.gov/what-medicare-covers",
                "category": "coverage",
                "title_prefix": "What Medicare Covers"
            },
            "costs": {
                "url": "https://www.medicare.gov/basics/costs/medicare-costs",
                "category": "costs_pricing",
                "title_prefix": "Medicare Costs Overview"
            },
        }

        self.check_robots_txt("https://www.medicare.gov")

        for page_id, page_info in pages.items():
            soup = self.fetch_page(page_info["url"])
            if soup:
                content = self.extract_text_content(soup)
                if content and len(content) > 50:
                    records.append({
                        "id": f"medicare_{page_id}",
                        "title": page_info["title_prefix"],
                        "content": content,
                        "category": page_info["category"],
                        "source": "medicare.gov",
                        "source_url": page_info["url"]
                    })
                    print(f"  ✅ Extracted {len(content)} chars from {page_id}")

        return records

    def scrape_all(self) -> List[Dict]:
        """Run all scrapers and combine results.

        Only scrapes US government public domain sources:
        - Healthcare.gov (federal government, public domain)
        - Medicare.gov / CMS.gov (federal government, public domain)

        Private company sites (BCBS, UHC, Aetna) are excluded
        to avoid copyright/ToS violations.
        """
        print("=" * 60)
        print("🔍 Starting Health Insurance Data Scraping")
        print("   Sources: US Government sites only (public domain)")
        print("=" * 60)

        all_records = []

        print("\n📋 Source 1: Healthcare.gov (Public Domain)")
        all_records.extend(self.scrape_healthcare_gov())

        print("\n📋 Source 2: Medicare.gov (Public Domain)")
        all_records.extend(self.scrape_medicare_gov())

        # Save raw data
        output_file = self.output_dir / "scraped_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_records, f, indent=2, ensure_ascii=False)

        print(f"\n{'=' * 60}")
        print(f"✅ Scraping complete! {len(all_records)} records saved to {output_file}")
        print(f"{'=' * 60}")

        self.scraped_data = all_records
        return all_records


def load_curated_content(filepath: str = "knowledge_base/data/raw/curated_content.json") -> List[Dict]:
    """
    Load curated health insurance content from the separate JSON data file.

    This content is written based on publicly available information from
    Healthcare.gov and other public domain sources — NOT scraped, NOT synthetic.
    Kept separate from the scraper to maintain clean separation of concerns.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} curated records from {filepath}")
        return data
    except FileNotFoundError:
        print(f"⚠ Curated content file not found: {filepath}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing curated content: {e}")
        return []


if __name__ == "__main__":
    # Run the scraper (US government public domain sources)
    scraper = HealthInsuranceScraper()
    scraped = scraper.scrape_all()
    print(f"\nScraped records: {len(scraped)}")

    # Load curated content (separate data file)
    curated = load_curated_content()
    print(f"Curated records: {len(curated)}")
    print(f"Total KB source records: {len(scraped) + len(curated)}")
