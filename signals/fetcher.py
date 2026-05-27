import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from utils.logger import logger
from utils.config import ENABLE_MOCK_FALLBACK
from utils.date_utils import get_current_iso
from signals.mock_data import MOCK_DOCUMENTS

def fetch_with_retry(url: str, headers: Dict[str, str] = None, retries: int = 3, backoff: float = 1.0, timeout: float = 5.0) -> bytes:
    """Performs HTTP GET request with retries and exponential backoff."""
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 competitor-detector/1.0"
        }
    req = urllib.request.Request(url, headers=headers)
    
    for attempt in range(retries):
        try:
            logger.info(f"Fetching URL: {url} (Attempt {attempt + 1}/{retries})")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP Error {e.code} on attempt {attempt + 1}: {e.reason}")
            if e.code == 429: # Rate limit, sleep longer
                if attempt < retries - 1:
                    sleep_time = backoff * 3 * (attempt + 1)
                    logger.info(f"Rate limited (429). Sleeping {sleep_time}s before retry...")
                    time.sleep(sleep_time)
                    continue
            elif e.code in (401, 403, 404):
                # Auth/Not Found errors are immediate failures
                raise e
        except Exception as e:
            logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            
        if attempt < retries - 1:
            sleep_time = backoff * (2 ** attempt)
            logger.info(f"Sleeping {sleep_time}s before retry...")
            time.sleep(sleep_time)
            
    raise Exception(f"Failed to fetch {url} after {retries} attempts.")

def fetch_reddit(live: bool = False) -> List[Dict[str, Any]]:
    """Fetches public posts from r/recruiting and r/jobs."""
    if not live:
        logger.info("Live mode disabled. Loading Reddit mock data.")
        return [doc for doc in MOCK_DOCUMENTS if doc["source"] == "reddit"]
        
    url = "https://www.reddit.com/r/recruiting/new.json?limit=10"
    try:
        raw_data = fetch_with_retry(url, timeout=6.0)
        json_data = json.loads(raw_data.decode("utf-8"))
        posts = json_data.get("data", {}).get("children", [])
        
        results = []
        for post in posts:
            pdata = post.get("data", {})
            text = f"{pdata.get('title', '')}\n{pdata.get('selftext', '')}"
            created_utc = pdata.get("created_utc")
            timestamp = datetime_from_utc_timestamp(created_utc) if created_utc else get_current_iso()
            
            results.append({
                "text": text,
                "source": "reddit",
                "url": f"https://www.reddit.com{pdata.get('permalink', '')}",
                "timestamp": timestamp,
                "author": pdata.get("author", "anonymous"),
                "company": "Unknown"  # Reddit is typically anonymous
            })
        logger.info(f"Successfully fetched {len(results)} live posts from Reddit.")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch live Reddit posts: {e}.")
        if ENABLE_MOCK_FALLBACK:
            logger.info("Falling back to cached Reddit mock data.")
            return [doc for doc in MOCK_DOCUMENTS if doc["source"] == "reddit"]
        return []

def fetch_g2_reviews(live: bool = False) -> List[Dict[str, Any]]:
    """G2 requires authentication and blocks standard web scrapers via Cloudflare.
    
    This function simulates G2 reviews using the high-fidelity mock dataset.
    """
    # G2 reviews cannot be reliably fetched unauthenticated, we rely on mock data or local cache
    logger.info("G2 reviews require premium API or browser automation. Ingesting from high-fidelity mock cache.")
    return [doc for doc in MOCK_DOCUMENTS if doc["source"] == "g2"]

def fetch_trustpilot(live: bool = False) -> List[Dict[str, Any]]:
    """Trustpilot reviews. Live fetches are simulated using the mock dataset."""
    logger.info("Trustpilot reviews require premium API or browser automation. Ingesting from high-fidelity mock cache.")
    return [doc for doc in MOCK_DOCUMENTS if doc["source"] == "trustpilot"]

def fetch_public_blog_comments(live: bool = False) -> List[Dict[str, Any]]:
    """Fetches public RSS feeds of recruiting/HR blogs or blog comments."""
    if not live:
        logger.info("Live mode disabled. Loading Blog mock data.")
        return [doc for doc in MOCK_DOCUMENTS if doc["source"] == "blog"]
        
    # We attempt to fetch a real HR public RSS feed
    rss_url = "https://www.hiringlab.org/feed/"
    try:
        raw_xml = fetch_with_retry(rss_url, timeout=5.0)
        root = ET.fromstring(raw_xml)
        
        results = []
        for item in root.findall(".//item")[:10]:
            title = item.find("title")
            desc = item.find("description")
            link = item.find("link")
            creator = item.find("{http://purl.org/dc/elements/1.1/}creator")
            pub_date = item.find("pubDate")
            
            text = f"{title.text if title is not None else ''}\n{desc.text if desc is not None else ''}"
            # Simple cleanup of HTML tags if description is HTML
            text = clean_html(text)
            
            results.append({
                "text": text,
                "source": "blog",
                "url": link.text if link is not None else "",
                "timestamp": parse_rss_date(pub_date.text) if pub_date is not None else get_current_iso(),
                "author": creator.text if creator is not None else "Staff Writer",
                "company": "Unknown"
            })
        logger.info(f"Successfully fetched {len(results)} live entries from hiringlab.org RSS.")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch live blog comments RSS: {e}.")
        if ENABLE_MOCK_FALLBACK:
            logger.info("Falling back to cached Blog mock data.")
            return [doc for doc in MOCK_DOCUMENTS if doc["source"] == "blog"]
        return []

# Helper utilities
def datetime_from_utc_timestamp(epoch: float) -> str:
    """Converts epoch timestamp to ISO 8601 string."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()

def clean_html(raw_html: str) -> str:
    """Removes HTML tags from a string."""
    import re
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

def parse_rss_date(rss_date_str: str) -> str:
    """Parses standard RSS date string (RFC 822) to ISO 8601."""
    from datetime import datetime
    import email.utils
    try:
        parsed_date = email.utils.parsedate_to_datetime(rss_date_str)
        return parsed_date.isoformat()
    except Exception:
        return get_current_iso()
