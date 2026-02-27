# Supabase Configuration
SUPABASE_URL = "https://dypnzxugrkbmlvljuknz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR5cG56eHVncmtibWx2bGp1a256Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzOTI5NDMsImV4cCI6MjA2OTk2ODk0M30.eM1vl7UFsWH_EqOeqGgQHB2a9SZ599ocDFeb2KlMLZQ"  # Prefer SERVICE_ROLE key for bulk operations, or ANON key if RLS allows
SUPABASE_TABLE = "inventory_global"

# Flask Admin Configuration
ADMIN_TOKEN = "super_secret_admin_token_2026"  # Change this to a secure random string in production


# Target URL (Can be overridden by command line args if implemented)
BASE_URL = "https://medex.com.bd/companies/48/nipro-jmi-pharma-ltd/brands"

# Range of pages to scrape
START_PAGE = 1
END_PAGE = 2

# Default File Suffix (Used if user presses Enter at prompt)
DEFAULT_SUFFIX = "Nipro JMI Pharma Ltd"

# Browser Configuration
HEADLESS_MODE = False  # Set to True for faster, invisible scraping (Riskier)

# User-Agent Rotation List
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]


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
