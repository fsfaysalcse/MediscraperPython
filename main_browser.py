import time
import random
import csv
import os
import re
import sys
import shutil
import tempfile
import socket
import logging
import unicodedata
from datetime import datetime

# DrissionPage
from DrissionPage import ChromiumPage, ChromiumOptions

# Config
import config

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Constants ---
def clean_text(text):
    """
    Normalizes text to remove invisible characters, unify whitespace, 
    and ensure clean UTF-8 string.
    """
    if not text: return ""
    
    # Normalize Unicode (NFKD compatibility decomposition)
    text = unicodedata.normalize('NFKD', text)
    
    # Remove non-printable characters (keep standard text, numbers, punctuation)
    # This regex keeps alphanumeric, common punctuation, and spaces.
    # We allow more broad range but strip control chars.
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    
    # Replace multiple spaces/tabs/newlines with single space
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_internal_category(medex_dosage):
    internal_categories = [
        "Transdermal Patch", "Cream", "Capsule", "Granules", "Injection", 
        "Medicated Soap", "Ointment", "Inhaler", "IV Infusion", "Gel", 
        "Solution", "Mouthwash", "Powder", "Suspension", "Suppository", 
        "Serum", "Eye/Ear/Nose Drops", "Nasal/Oral Spray", "Medicated Shampoo", 
        "Tablet", "Nebulizer Solution", "Syrup", "Lotion"
    ]
    
    for cat in internal_categories:
        if cat.lower() in medex_dosage.lower():
            return cat
    return "Miscellaneous"

def transform_medex_item(scraped_data):
    """
    Apply this logic to every item scraped from Medex.
    """
    dosage = scraped_data.get('dosage_form', '').lower()
    
    # Default Units
    p_unit = "piece"
    s_unit = "box"
    conv = 1
    
    # 1. Logic for Tablets/Capsules
    if any(x in dosage for x in ["tablet", "capsule"]):
        p_unit, s_unit, conv = "piece", "strip", 10
        
    # 2. Logic for Liquids (Syrup, Suspension, Solution, etc)
    elif any(x in dosage for x in ["syrup", "suspension", "drops", "solution", "mouthwash", "liquid", "elixir"]):
        p_unit, s_unit, conv = "bottle", "box", 1
        
    # 3. Logic for Injections
    elif "injection" in dosage:
        if "vial" in dosage:
            p_unit = "vial"
        elif "ampoule" in dosage:
            p_unit = "ampoule"
        else:
            p_unit = "ampoule" 
        s_unit, conv = "box", 1
        
    # 4. Logic for Topicals
    elif any(x in dosage for x in ["cream", "ointment", "gel", "lotion"]):
        p_unit, s_unit, conv = "tube", "box", 1
        
    # 5. Logic for Inhalers
    elif "inhaler" in dosage or "spray" in dosage or "puff" in dosage:
        p_unit, s_unit, conv = "puff", "box", 200

    # 6. Logic for Sachets/Powders
    elif any(x in dosage for x in ["sachet", "powder", "granules"]):
        p_unit, s_unit, conv = "sachet", "box", 1

    # 7. Logic for Suppositories
    elif "suppository" in dosage:
        p_unit, s_unit, conv = "piece", "box", 1

    # Determine Type (Medicine vs Other)
    # User Request: Field 'type': Always 'MEDICINE'
    
    # Internal Category Mapping
    internal_cat = get_internal_category(dosage)

    # Clean Brand Name: Remove Dosage/Category from Name
    full_brand = scraped_data.get('brand_name', '').strip()
    
    brand_val = full_brand
    if internal_cat and internal_cat != "Miscellaneous":
        pattern = re.compile(re.escape(internal_cat), re.IGNORECASE)
        brand_val = pattern.sub("", brand_val).strip()
    
    # Also try removing dosage form if different
    if dosage and dosage.lower() not in internal_cat.lower():
         pattern = re.compile(re.escape(dosage), re.IGNORECASE)
         brand_val = pattern.sub("", brand_val).strip()

    
    # Defaults for mandatory fields
    strength_val = scraped_data.get('strength', '').strip()
    if not strength_val: strength_val = "N/A"

    generic_val = scraped_data.get('generic_name', '').strip()
    if not generic_val: generic_val = "Unknown"

    return {
        "type": "MEDICINE",
        "category": internal_cat,
        "brand": brand_val,
        "generic_name": generic_val,
        "strength": strength_val,
        "manufacturer": scraped_data.get('manufacturer', '').strip(),
        "name": None, # Requested field, must be NULL for MEDICINE
        "primary_unit": p_unit,
        "secondary_unit": s_unit,
        "conversion_rate": conv,
        "item_code": "", # Requested field, empty for now
        "medex_url": scraped_data.get('url'),
        "entry_status": "AI_L1",
        "updated_by": "" # Must be valid UUID or NULL (empty string in CSV)
    }


def get_chrome_path():
    """Attempts to find the Chrome executable on macOS."""
    paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def find_free_port():
    """Finds a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

class MedexBrowserScraper:
    def __init__(self):
        # Create a temporary user data directory
        self.temp_user_data = tempfile.mkdtemp(prefix="medex_scraper_profile_")
        logger.info(f"Created Temp Profile: {self.temp_user_data}")
        
        self.seen_urls = set() # Duplicate Trackers

        co = ChromiumOptions()
        
        # User Agent Rotation
        user_agent = random.choice(config.USER_AGENTS)
        co.set_user_agent(user_agent)
        logger.info(f"Using User-Agent: {user_agent}")
        
        # macOS Path
        chrome_path = get_chrome_path()
        if chrome_path:
            logger.info(f"Found Chrome: {chrome_path}")
            co.set_browser_path(chrome_path)
        
        # Manual Port Selection
        try:
            port = find_free_port()
            logger.info(f"Selected Port: {port}")
            co.set_local_port(port)
        except Exception as e:
            logger.warning(f"Could not find free port: {e}")
            co.set_local_port(9222)
            
        # User Data Dir
        co.set_user_data_path(self.temp_user_data)
        
        # Arguments
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--no-first-run')
        co.set_argument('--no-default-browser-check')
        
        if config.HEADLESS_MODE:
            logger.info("Running in Headless Mode")
            co.set_argument('--headless=new')
        
        try:
            logger.info("Launching Browser...")
            self.page = ChromiumPage(co)
            logger.info("Browser Launched Successfully")
            try:
                self.page.set.window.location(0, 0)
                self.page.set.window.size(1280, 800)
            except: pass

        except Exception as e:
            logger.critical(f"Critical Error Launching Browser: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def cleanup(self):
        try:
            if hasattr(self, 'page') and self.page:
                self.page.quit()
        except: pass
        try:
            if os.path.exists(self.temp_user_data):
                shutil.rmtree(self.temp_user_data, ignore_errors=True)
                logger.info("Cleaned up temp profile.")
        except: pass

    def check_for_block(self):
        """Checks if current page is blocked (Terms of Use)."""
        try:
            if "terms-of-use" in self.page.url:
                logger.warning("Detected Terms of Use block page!")
                return True
        except: pass
        return False

    def simulate_human_behavior(self):
        """Simulates human-like scrolling and small pauses."""
        try:
            # Scroll down a bit
            self.page.scroll.down(random.randint(100, 400))
            time.sleep(random.uniform(0.1, 0.3))
            
            # Maybe scroll up a tiny bit
            if random.random() < 0.3:
                self.page.scroll.up(random.randint(10, 50))
            
            # Wait a tick
            time.sleep(random.uniform(0.2, 0.5))
            
        except: pass

    def handle_security_check(self):
        """Checks for 'Security Check' and attempts to click Continue."""
        retries = 0
        max_retries = 3
        
        while retries < max_retries:
            try:
                if not self.page: return False
                
                title = self.page.title.lower()
                text = self.page.html.lower()
                is_captcha = "security check" in title or "captcha-button" in text
                
                if not is_captcha:
                    return True # Passed
                
                logger.warning(f"Security Check Page Detected! (Attempt {retries+1})")
                
                # Human-like delay before reacting
                time.sleep(random.uniform(1.5, 3.0))
                
                # Try to click the button
                btn = self.page.ele('.captcha-button')
                if btn:
                    logger.info("Found Captcha Button. Clicking...")
                    btn.click()
                    time.sleep(3) # Wait for reload
                    
                    # Check if we passed
                    if "security check" not in self.page.title.lower():
                        logger.info("Captcha passed!")
                        return True
                else:
                    logger.warning("Captcha button not found on security page.")
                
                time.sleep(3)
                retries += 1
            except Exception as e:
                logger.error(f"Error in captcha handler: {e}")
                time.sleep(1)
        
        return False # Failed

    def scrape_details(self, url):
        self.page.get(url)
        
        # Check for block
        if self.check_for_block():
            return "BLOCKED"

        if not self.handle_security_check():
             logger.error("Failed to pass captcha.")
             return "SKIP"
        
        # Double check block after captcha
        if self.check_for_block(): return "BLOCKED"
        
        # Simulate Human Reading
        self.simulate_human_behavior()
        
        try:
            # 1. Raw Data Extraction
            name_el = self.page.ele('xpath://h1[contains(@class, "brand")] | //h1[contains(@class, "brand-name")] | //h1[contains(@class, "page-heading")]')
            
            # If name not found, check if we got redirected to some weird page or still loading
            if not name_el:
                if self.check_for_block(): return "BLOCKED"
                return None
            
            brand_raw = clean_text(name_el.text)
            
            strength = clean_text(self.page.ele('css:div[title="Strength"]').text) if self.page.ele('css:div[title="Strength"]') else ""
            
            generic_el = self.page.ele('css:div[title="Generic Name"] a')
            generic = clean_text(generic_el.text) if generic_el else ""

            mfg_el = self.page.ele('css:div[title="Manufactured by"] a')
            mfg = clean_text(mfg_el.text) if mfg_el else ""
            
            # Dosage/Category
            dosage_icon = self.page.ele('css:img.dosage-icon')
            dosage_form = dosage_icon.attr("title") if dosage_icon else ""
            
            # Prepare raw data
            raw_data = {
                "brand_name": brand_raw,
                "generic_name": generic,
                "strength": strength,
                "manufacturer": mfg,
                "dosage_form": dosage_form,
                "category_name": dosage_form, 
                "url": url
            }
            
            return transform_medex_item(raw_data)
        except Exception as e:
            logger.error(f"Extraction Error for {url}: {e}")
            return None

    def validate_csv(self, filename):
        """Validates the CSV file integrity."""
        # logger.info(f"Validating {filename}...")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return False
                
                required_cols = ["type", "category", "brand", "generic_name", "strength", 
                                "manufacturer", "name", "primary_unit", "secondary_unit", 
                                "conversion_rate", "item_code", "medex_url", "entry_status", 
                                "updated_by"]
                
                # Check header length equal
                if len(header) != len(required_cols):
                    return False # Strict header check
                
                row_count = 0
                for row in reader:
                    row_count += 1
                    if len(row) != len(required_cols):
                         logger.error(f"Row {row_count + 1} validation failed: Expected {len(required_cols)} cols, got {len(row)}")
                         return False
                
                return True
        except Exception as e:
            logger.error(f"CSV Validation Exception: {e}")
            return False

    def load_processed_urls(self, filename):
        if os.path.exists(filename):
            logger.info(f"Loading processed URLs from {filename}...")
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get("medex_url")
                        if url: self.seen_urls.add(url)
                logger.info(f"Loaded {len(self.seen_urls)} processed URLs.")
            except Exception as e:
                logger.error(f"Error loading processed URLs: {e}")

    def run_session(self, start_page, end_page, filename, suffix=""):
        """
        Runs the scraper for the given range.
        Returns:
            (status_code, last_processed_page)
            status_code: 'DONE', 'BLOCKED', 'ERROR'
        """
        if not os.path.exists('data'): os.makedirs('data')
        
        base = config.BASE_URL
        
        # Load processed URLs to avoid duplicates
        self.load_processed_urls(filename)

        # Columns
        fieldnames = ["type", "category", "brand", "generic_name", "strength", 
                      "manufacturer", "name", "primary_unit", "secondary_unit", 
                      "conversion_rate", "item_code", "medex_url", "entry_status", 
                      "updated_by"]
        
        try:
            # Check if file exists to decide mode
            mode = 'a' if os.path.exists(filename) else 'w'
            
            with open(filename, mode, newline='', encoding='utf-8') as csvfile:
                # Use QUOTE_ALL as requested by user to safe-guard row integrity
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore', quoting=csv.QUOTE_ALL)
                
                if mode == 'w':
                    writer.writeheader()
                
                for page in range(start_page, end_page + 1):
                    logger.info(f"--- Processing Page {page} ---")
                    list_url = f"{base}{'&' if '?' in base else '?'}page={page}" if page > 1 else base
                    
                    self.page.get(list_url)
                    
                    if self.check_for_block():
                        logger.warning(f"BLOCKED at Page {page} List View.")
                        return "BLOCKED", page
                    
                    if not self.handle_security_check():
                         logger.error(f"Failed captcha on list page {page}. Skipping page or Blocked?")
                         # If we fail captcha here, likely blocked.
                         return "BLOCKED", page
                    
                    # Human behavior on list page
                    self.simulate_human_behavior()
                    
                    try:
                        links = [el.attr('href') for el in self.page.eles('css:a.hoverable-block')]
                    except: links = []
                    
                    # Dedup links on the page itself
                    unique_links = list(set(links))
                    logger.info(f"Found {len(unique_links)} items on Page {page}")
                    
                    for link in unique_links:
                        if link in self.seen_urls:
                            # logger.info(f"Skipping duplicate URL: {link}")
                            continue
                            
                        logger.info(f"Visiting: {link}")
                        details_or_status = self.scrape_details(link)
                        
                        if details_or_status == "BLOCKED":
                            logger.warning(f"BLOCKED at Item: {link}")
                            return "BLOCKED", page
                        
                        if isinstance(details_or_status, dict):
                            writer.writerow(details_or_status)
                            csvfile.flush() 
                            self.seen_urls.add(link)
                            logger.info(f"    -> Scraped: {details_or_status['brand']}")
                            time.sleep(random.uniform(0.5, 1.5))
                    
                    logger.info(f"Page {page} done. Validating CSV...")
                    if not self.validate_csv(filename):
                        logger.critical("CSV Validation Failed! Stopping.")
                        return "ERROR", page

                    # Random delay between pages
                    time.sleep(random.uniform(2, 4))
            
            return "DONE", end_page
            
        except Exception as e:
            logger.error(f"Session Error: {e}")
            import traceback
            traceback.print_exc()
            return "ERROR", start_page


def main_loop():
    start_page = int(config.START_PAGE)
    end_page = int(config.END_PAGE)
    
    # User Input for Suffix (Ask once)
    try:
        suffix_input = input(f"What is the file name suffix? (e.g. ACI Limited) [Default: All]: ").strip()
    except EOFError:
        suffix_input = ""
        
    if not suffix_input:
        suffix = "All"
    else:
        suffix = re.sub(r'[^\w\s-]', '', suffix_input).strip().replace(' ', '_')
        
    filename = f"data/medex_mapped_inventory_{suffix}_{start_page}_to_{end_page}.csv"
    logger.info(f"Output File: {filename}")

    current_page = start_page
    
    while current_page <= end_page:
        logger.info(f"=== Starting Session from Page {current_page} ===")
        scraper = MedexBrowserScraper()
        
        status, stop_page = scraper.run_session(current_page, end_page, filename, suffix)
        
        scraper.cleanup()
        
        if status == "DONE":
            logger.info("Scraping Completed Successfully.")
            break
        elif status == "BLOCKED":
            logger.warning(f"Session Blocked at Page {stop_page}. Restarting in 10 seconds...")
            current_page = stop_page # Resume from the page we got blocked on
            time.sleep(10)
        elif status == "ERROR":
            logger.error(f"Session Error at Page {stop_page}. Stopping.")
            break
        else:
            logger.error(f"Unknown status {status}. Stopping.")
            break

if __name__ == "__main__":
    main_loop()
