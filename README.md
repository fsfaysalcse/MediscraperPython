# Medex Python Scraper (Hardened Edition)

A robust, "bulletproof" Python scraper designed to scrape inventory data from Medex with advanced anti-blocking features, human simulation, and database-compliant output.

## Features
- **Anti-Blocking**: Automatically detects "Security Check" and "Terms of Use" blocks.
- **Auto-Restart**: If blocked, detects the issue, waits, and restarts the session from the exact page where it left off.
- **Human Simulation**: Random scrolling, pauses, and mouse movements to mimic real user behavior.
- **User-Agent Rotation**: Rotates valid User-Agents to avoid fingerprinting.
- **Database Compliant**: Outputs fully sanitized CSVs compatible with Supabase (strictly quoted, NULL handling).

## 🚀 Installation

1.  **Clone the Repository** (if not already done).

2.  **Set up Python Environment**:
    It is recommended to use a virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration (`config.py`)

Edit the `config.py` file to control the scraper behavior:

- **`BASE_URL`**: The target URL list page (e.g., specific manufacturer or brand list).
- **`START_PAGE` / `END_PAGE`**: Define the range of pages to scrape.
- **`HEADLESS_MODE`**:
    - `False` (Default): Opens a visible browser window. Safer, harder to detect.
    - `True`: Runs in background. Faster but slightly higher risk of detection.
- **`USER_AGENTS`**: List of browser fingerprints to rotate through.

## 🏃 Usage

Run the scraper using the main script:

```bash
source venv/bin/activate
python3 main_browser.py
```

1.  The script will prompt you for a **file suffix**.
2.  Enter a name (e.g., `Incepta` or `Square`).
3.  The scraper will run, handling all pages automatically.
4.  If a block occurs, check the terminal: it will say *"Restarting in 10 seconds..."* and resume automatically.

## 📂 Data Output

Scraped files are saved in the `data/` directory:
`data/medex_mapped_inventory_<Suffix>_<Start>_to_<End>.csv`

### 🔒 Security & Data Handling
> **IMPORTANT SECURITY NOTE**
> *   **Secure Storage**: Always keep the scraped CSV files in a secure, private folder. Do not expose them publicly.
> *   **Transfer Protocol**: Once scraping is complete and verified, please securely zip and send the data directly to **Faysal**.
> *   **Validation**: Before sending, briefly check the CSV to ensure column alignment (headers match values).

## 🛠 Troubleshooting

*   **"Session Blocked"**: The scraper will handle this automatically. If it loops continuously on the same page, try increasing `random` sleep times in `main_browser.py`.
*   **"Chrome not found"**: Ensure Google Chrome is installed in the default location.
