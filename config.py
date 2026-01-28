# Scraper Configuration

# Target URL (Can be overridden by command line args if implemented)
BASE_URL = "https://medex.com.bd/companies/106/incepta-pharmaceuticals-ltd/brands"

# Range of pages to scrape
START_PAGE = 1
END_PAGE = 50

# cURL Command to Import (Paste your cURL here to auto-extract headers/cookies)
# If empty, default headers will be used (which might be blocked)
CURL_COMMAND = """
"""

# Default Headers (Fallback if no cURL command provided)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
