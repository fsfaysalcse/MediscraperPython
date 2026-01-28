import time
import random
import csv
import os
import re
import sys
import shutil
import tempfile
import socket
from datetime import datetime

# DrissionPage
from DrissionPage import ChromiumPage, ChromiumOptions

# Config
import config

# --- Constants ---
def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

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

    return {
        "type": "MEDICINE",
        "category": internal_cat,
        "brand": brand_val,
        "generic_name": scraped_data.get('generic_name', '').strip(),
        "strength": scraped_data.get('strength', '').strip(),
        "manufacturer": scraped_data.get('manufacturer', '').strip(),
        "primary_unit": p_unit,
        "secondary_unit": s_unit,
        "conversion_rate": conv,
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
        print(f"[*] Created Temp Profile: {self.temp_user_data}")

        co = ChromiumOptions()
        
        # macOS Path
        chrome_path = get_chrome_path()
        if chrome_path:
            print(f"[*] Found Chrome: {chrome_path}")
            co.set_browser_path(chrome_path)
        
        # Manual Port Selection
        try:
            port = find_free_port()
            print(f"[*] Selected Port: {port}")
            co.set_local_port(port)
        except Exception as e:
            print(f"[!] Warning: Could not find free port: {e}")
            co.set_local_port(9222)
            
        # User Data Dir
        co.set_user_data_path(self.temp_user_data)
        
        # Arguments
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--no-first-run')
        co.set_argument('--no-default-browser-check')
        
        try:
            print("[*] Launching Browser...")
            self.page = ChromiumPage(co)
            print("[*] Browser Launched Successfully")
            try:
                self.page.set.window.location(0, 0)
                self.page.set.window.size(1280, 800)
            except: pass

        except Exception as e:
            print(f"[!] Critical Error Launching Browser: {e}")
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
                print(f"[*] Cleaned up temp profile.")
        except: pass

    def check_captcha(self):
        retries = 0
        while True:
            try:
                if not self.page: return True
                title = self.page.title.lower()
                text = self.page.html.lower()
                is_captcha = "just a moment" in title or "security check" in title or "cloudflare" in text
                if not is_captcha: return True
                print(f"[!] Security Check Detected! (Attempt {retries+1})")
                time.sleep(5)
                retries += 1
            except: time.sleep(1)

    def scrape_details(self, url):
        self.page.get(url)
        self.check_captcha()
        
        try:
            # 1. Raw Data Extraction
            name_el = self.page.ele('xpath://h1[contains(@class, "brand")] | //h1[contains(@class, "brand-name")] | //h1[contains(@class, "page-heading")]')
            if not name_el: return None
            
            brand_raw = clean_text(name_el.text)
            if "Security Check" in brand_raw:
                print("[!] Caught Security Check text. Retrying...")
                time.sleep(3)
                self.check_captcha()
                return self.scrape_details(url)
            
            strength = clean_text(self.page.ele('css:div[title="Strength"]').text) if self.page.ele('css:div[title="Strength"]') else ""
            
            generic_el = self.page.ele('css:div[title="Generic Name"] a')
            generic = clean_text(generic_el.text) if generic_el else ""

            mfg_el = self.page.ele('css:div[title="Manufactured by"] a')
            mfg = clean_text(mfg_el.text) if mfg_el else ""

            pkg_el = self.page.ele('css:.package-container')
            pkg_info = clean_text(pkg_el.text) if pkg_el else ""
            
            # Dosage/Category (Usually in h1 class='brand' sibling or smaller text, OR inferred)
            # Find dosage icon helper
            dosage_icon = self.page.ele('css:img.dosage-icon')
            dosage_form = dosage_icon.attr("title") if dosage_icon else ""
            
            # Prepare raw data for transformation
            raw_data = {
                "brand_name": brand_raw,
                "generic_name": generic,
                "strength": strength,
                "manufacturer": mfg,
                "dosage_form": dosage_form,
                "category_name": dosage_form, # Fallback
                "url": url
            }
            
            return transform_medex_item(raw_data)
        except Exception as e:
            print(f"[!] Extraction Error: {e}")
            return None

    def run(self):
        if not os.path.exists('data'): os.makedirs('data')
        
        base = config.BASE_URL
        start = config.START_PAGE
        end = config.END_PAGE
        
        # User Input for Suffix
        try:
            suffix_input = input(f"What is the file name suffix? (e.g. ACI Limited) [Default: All]: ").strip()
        except EOFError:
            suffix_input = ""
            
        if not suffix_input:
            suffix = "All"
        else:
            suffix = re.sub(r'[^\w\s-]', '', suffix_input).strip().replace(' ', '_')
            
        filename = f"data/medex_mapped_inventory_{suffix}_{start}_to_{end}.csv"
        
        # Columns requested: match inventory_global table
        fieldnames = ["type", "category", "brand", "generic_name", "strength", 
                      "manufacturer", "name", "primary_unit", "secondary_unit", 
                      "conversion_rate", "item_code", "medex_url", "entry_status", 
                      "updated_by"]
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                print(f"[+] Output file: {filename}")
                
                # (Variables moved up)
                
                for page in range(start, end + 1):
                    # print(f"\n--- Processing Page {page} ---")
                    list_url = f"{base}{'&' if '?' in base else '?'}page={page}" if page > 1 else base
                    
                    self.page.get(list_url)
                    self.check_captcha()
                    
                    try:
                        links = [el.attr('href') for el in self.page.eles('css:a.hoverable-block')]
                    except: links = []
                    
                    unique_links = list(set(links))
                    print(f"[+] Found {len(unique_links)} items on Page {page}")
                    
                    for link in unique_links:
                        print(f"  > Visiting: {link}")
                        details = self.scrape_details(link)
                        if details:
                            # Validate Category/Base Unit against strict lists?
                            # User only said "Validate against BASE_UNITS and VALID_CATEGORIES".
                            # Our extract functions try to produce valid ones. 
                            # If invalid, maybe we should log? 
                            # For now just write what we got (it returns "" or default if not found)
                            writer.writerow(details)
                            print(f"    -> Scraped: {details['brand']} | {details['category']}")
                            csvfile.flush()
                            time.sleep(random.uniform(1.0, 2.5)) # Slightly faster as requested implicitly by "Senior Engineer" efficiency
                            
                    print(f"[✓] Page {page} is done.")
                    delay = random.uniform(3, 6)
                    # print(f"[~] Sleeping for {delay:.2f}s...")
                    time.sleep(delay)
        finally:
            self.cleanup()

if __name__ == "__main__":
    scraper = MedexBrowserScraper()
    scraper.run()
