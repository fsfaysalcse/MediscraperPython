import os
import time
import random
import csv
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Third-party
from curl_cffi import requests
from bs4 import BeautifulSoup
import config

# --- Utility: Parse cURL into structure ---
def parse_curl_simple(curl_cmd):
    """
    Simulated parser for the python config.
    Just returns a dict of headers and cookies from the config string if provided.
    For this MVP, we might just ask user to paste cookie string in config.py 
    or we can implement a regex parser similar to the TypeScript one.
    """
    if not curl_cmd:
        return {}, {}
    
    headers = {}
    cookie_str = ""
    
    # Extract Headers
    header_regex = re.finditer(r"(?:-H|--header)\s+['\"]([^'\"]+):([^'\"]+)['\"]", curl_cmd)
    for match in header_regex:
        k = match.group(1).strip()
        v = match.group(2).strip()
        # requests (curl_cffi) handles casing, but let's keep it clean
        if k.lower() == 'cookie':
            cookie_str = v
        else:
            headers[k] = v

    # Extract Cookie Flag
    cookie_regex = re.search(r"(?:-b|--cookie)\s+['\"]([^'\"]+)['\"]", curl_cmd)
    if cookie_regex:
        cookie_str = cookie_regex.group(1).strip()

    # Manual Cookie Parser
    cookies = {}
    if cookie_str:
        for pair in cookie_str.split(';'):
            if '=' in pair:
                ck, cv = pair.split('=', 1)
                cookies[ck.strip()] = cv.strip()

    return headers, cookies

# --- Extraction Logic (Ported from TypeScript) ---
def clean_text(text):
    if not text:
        return ""
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
            # Default for injection if unspecified
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
    # entry_status: "AI_L1"
    # updated_by: "PythonBro"
    
    # Internal Category Mapping
    internal_cat = get_internal_category(dosage)

    # Clean Brand Name: Remove Dosage/Category from Name
    full_brand = scraped_data.get('brand_name', '').strip()
    
    brand_val = full_brand
    if internal_cat and internal_cat != "Miscellaneous":
        # Case insensitive replace
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
        # Keeping units as they are useful for the DB, even if not explicitly requested in the *export* list?
        # The prompt said: "Process the scraped data and save it to 'medex_mapped_inventory.csv' with the following rules: Columns: ..."
        # I will stick to the columns requested in the CSV writing part, but here I return the full dict.
        "primary_unit": p_unit,
        "secondary_unit": s_unit,
        "conversion_rate": conv,
        "medex_url": scraped_data.get('url'),
        "entry_status": "AI_L1",
        "updated_by": "" # Must be valid UUID or NULL (empty string in CSV)
    }

def extract_unit_info(pkg_info):
    # E.g. "500's Pack (10x50)" -> Base: Pack, Unit: 500
    if not pkg_info:
        return {"base_unit": "", "unit_per_base": 1}
    
    # Simple regex
    # Match: "30 Tablets" or "100 ml Bottle"
    match = re.search(r"(\d+)\s+([a-zA-Z\s]+)", pkg_info)
    if match:
        return {"base_unit": match.group(2).strip(), "unit_per_base": int(match.group(1))}
    
    return {"base_unit": pkg_info, "unit_per_base": 1}

# --- Scraper Class ---
class MedexScraper:
    def __init__(self):
        self.session = requests.Session(impersonate="chrome120")
        
        # Load Headers/Cookies from Config
        headers, cookies = parse_curl_simple(config.CURL_COMMAND)
        
        # Merge with default if generic
        if not headers:
            self.session.headers.update(config.DEFAULT_HEADERS)
        else:
            self.session.headers.update(headers)
        
        if cookies:
            self.session.cookies.update(cookies)
            
        print(f"[*] Initialized Impersonated Session")

    def fetch(self, url, retries=3):
        for i in range(retries):
            try:
                # Random delay before request
                time.sleep(random.uniform(1, 3))
                
                print(f"[*] Fetching: {url}")
                resp = self.session.get(url, timeout=30)
                
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code == 403:
                    print(f"[!] 403 Forbidden. Captcha/WAF? Retrying...")
                elif resp.status_code == 404:
                    print(f"[!] 404 Not Found.")
                    return None
                    
                time.sleep(2 ** (i + 1)) # Exp backoff
                
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(2)
        return None

    def scrape_details(self, url):
        html = self.fetch(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Name
        name_el = soup.find('h1', class_='brand') or soup.find('h1', class_='brand-name') or soup.find('h1', class_='page-heading')
        if not name_el:
            return None
        brand_name = clean_text(name_el.text)
        
        if "Security Check" in brand_name:
            print("[!] Security Check Page Detected!")
            return None

        # Strength
        strength_el = soup.find('div', attrs={'title': 'Strength'})
        strength = clean_text(strength_el.text) if strength_el else ""

        # Generic
        generic_el = soup.find('div', attrs={'title': 'Generic Name'})
        generic = clean_text(generic_el.find('a').text) if generic_el and generic_el.find('a') else ""

        # Manufacturer
        mfg_el = soup.find('div', attrs={'title': 'Manufactured by'})
        mfg = clean_text(mfg_el.find('a').text) if mfg_el and mfg_el.find('a') else ""

        # Dosage / Category extraction
        # We need to find the dosage icon title or infer category
        dosage_icon = soup.select_one("img.dosage-icon")
        dosage_form = dosage_icon.get("title", "") if dosage_icon else ""
        
        # Fallback category to dosage form
        # Or try to extract from brand name if dosage_form is empty
        # For now, relying on dosage_form as the primary category indicator
        category_name = dosage_form
        if not category_name:
             # Try to find category in brand name?
             # For now, let's assume if no dosage icon, it might be Unknown or Other
             category_name = "Unknown"

        # Prepare raw data for transformation
        raw_data = {
            "brand_name": brand_name,
            "generic_name": generic,
            "strength": strength,
            "manufacturer": mfg,
            "dosage_form": dosage_form,
            "category_name": category_name,
            "url": url
        }

        return transform_medex_item(raw_data)

    def run(self):
        # Setup CSV
        if not os.path.exists('data'):
            os.makedirs('data')
            
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
                      
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            print(f"[+] Output file: {filename}")
            
            # (Variables moved up for filename generation)
            
            for page in range(start, end + 1):
                print(f"\n--- Processing Page {page} ---")
                
                list_url = base
                if page > 1:
                    sep = '&' if '?' in base else '?'
                    list_url = f"{base}{sep}page={page}"
                
                list_html = self.fetch(list_url)
                if not list_html:
                    continue
                
                soup = BeautifulSoup(list_html, 'html.parser')
                links = [a['href'] for a in soup.select('a.hoverable-block')]
                unique_links = list(set(links))
                
                print(f"[+] Found {len(unique_links)} items.")
                
                for link in unique_links:
                    details = self.scrape_details(link)
                    if details:
                        writer.writerow(details)
                        print(f"  > Scraped: {details['brand']}")
                        csvfile.flush() # Ensure data is written
                
                # Page Delay
                delay = random.uniform(4, 8)
                print(f"[~] Sleeping for {delay:.2f}s...")
                time.sleep(delay)

if __name__ == "__main__":
    scraper = MedexScraper()
    scraper.run()
