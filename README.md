# Medex Python Scraper (Ultimate Bypass Edition)

A robust scraper for Medex with "Attach Mode" to fully bypass Cloudflare protections by using your real browser session.

## 🚀 The "Attach Mode" (Recommended)

This is the most reliable way to scrape. You open Chrome, verify you're human, and the scraper takes over.

### Step 1: Open Chrome in Debug Mode
Open your **Terminal** or **PowerShell** and run this command EXACTLY:

**Mac (Terminal):**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_debug"
```

**Windows (cmd):**
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug"
```

### Step 2: Use the Browser
1.  A new Chrome window will open.
2.  Go to **medex.com.bd**.
3.  Navigate to a brand page.
4.  **Solve the Captcha** if it appears. Ensure you can browse the site normally.

### Step 3: Run the Scraper
In your project folder terminal:
```bash
source venv/bin/activate
python3 main_browser.py
```
*The scraper will detect the open Chrome window and start scraping inside it.*

---

## ⚙️ Configuration (`config.py`)

- **`DEFAULT_SUFFIX`**: Set your default filename suffix (e.g., "Beximco") here to skip typing it every time.
- **`START_PAGE` / `END_PAGE`**: Set the page range to scrape.

## 🏃 Legacy Mode (Fresh Browser)
If you just run `python3 main_browser.py` *without* opening the debug Chrome first, it will launch a new, fresh browser instance.
*   **Warning**: This is more likely to be blocked by Cloudflare.
*   **Stealth**: We have disabled automation flags, but "Attach Mode" is superior.

## 📂 Data Output
Files saved in `data/` folder.
format: `medex_mapped_inventory_<Suffix>_<Start>_to_<End>.csv`
