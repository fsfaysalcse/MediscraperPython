# Python Medex Scraper

A robust, standalone Python scraper designed to bypass CAPTCHA and WAF protections using `curl_cffi` for TLS fingerprint impersonation.

## Setup

1.  **Install Python 3.9+** (if not already installed).

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Edit `config.py` to set:
*   `BASE_URL`: The starting URL (e.g., `https://medex.com.bd/brands`).
*   `START_PAGE`: Starting page number.
*   `END_PAGE`: Ending page number.
*   **`CURL_COMMAND`** (Recommended): Paste a cURL command from your browser (Chrome DevTools -> Network -> Copy as cURL) to auto-configure cookies and headers for the best success rate.

## Usage

Run the scraper:

```bash
python mani_browser.py
```

## Output

Data is saved to the `data/` directory in CSV format: `medex_scrape_YYYYMMDD_HHMMSS.csv`.
