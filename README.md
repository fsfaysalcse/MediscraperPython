# Medex Python Scraper (Hardened Edition)

A robust, "bulletproof" Python scraper designed to scrape inventory data from Medex with advanced anti-blocking features, human simulation, and database-compliant output.

## Features
- **Anti-Blocking**: Automatically detects "Security Check" and "Terms of Use" blocks.
- **Auto-Restart**: If blocked, detects the issue, waits, and restarts the session from the exact page where it left off.
- **Human Simulation**: Random scrolling, pauses, and mouse movements to mimic real user behavior.
- **User-Agent Rotation**: Rotates valid User-Agents to avoid fingerprinting.
- **Database Compliant**: Outputs fully sanitized CSVs compatible with Supabase (strictly quoted, NULL handling).

## 🚀 Installation on Windows

1.  **Install Python**:
    - Download and install Python (3.10 or later) from [python.org](https://www.python.org/downloads/windows/).
    - **Important**: Check the box **"Add Python to PATH"** during installation.

2.  **Clone/Download the Repository**:
    - Download the code folder to your computer and unzip it.
    - Open the folder in VS Code or File Explorer.

3.  **Open Command Prompt (cmd) or PowerShell**:
    - In the folder address bar, type `cmd` and hit Enter to open a terminal in that folder.

4.  **Set up Virtual Environment**:
    ```cmd
    python -m venv venv
    ```

5.  **Activate Virtual Environment**:
    - **Command Prompt (cmd)**:
      ```cmd
      venv\Scripts\activate
      ```
    - **PowerShell**:
      ```powershell
      venv\Scripts\Activate.ps1
      ```
    *(You should see `(venv)` appear at the start of your command line)*

6.  **Install Dependencies**:
    ```cmd
    pip install -r requirements.txt
    ```

## ⚙️ Configuration (`config.py`)

Edit the `config.py` file to control the scraper behavior.

### Setting the Target URL
**Crucial**: When copying the URL from the browser, copy **only** up to the `/brands` part. Do **not** include page numbers or other parameters.

*   ✅ **CORRECT**:
    `https://medex.com.bd/companies/103/ad-din-pharmaceuticals-ltd/brands`

*   ❌ **WRONG**:
    `https://medex.com.bd/companies/103/ad-din-pharmaceuticals-ltd/brands?page=2`

### Other Settings
- **`START_PAGE` / `END_PAGE`**: Define the range of pages to scrape (e.g., 1 to 50).
- **`HEADLESS_MODE`**:
    - `False` (Default): Opens a visible browser window. Safer, harder to detect.
    - `True`: Runs in background. Faster but slightly higher risk of detection.

## 🏃 Usage

Run the scraper using the main script. Make sure your virtual environment is activated (`(venv)` is visible).

```cmd
python main_browser.py
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
*   **"Python not found"**: Ensure you installed Python and checked "Add to PATH".
