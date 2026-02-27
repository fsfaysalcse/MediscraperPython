import csv
import os
import time
import glob
from supabase import create_client, Client
import config
from datetime import datetime

# --- constants ---
BATCH_SIZE = 100 # Safe batch size for bulk inserts

def get_supabase_client():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    if "your-project" in url or "your-service" in key:
        print("❌ Error: Please set SUPABASE_URL and SUPABASE_KEY in config.py")
        return None
    return create_client(url, key)

def santize_row(row):
    """
    Cleans up a CSV row to match Supabase schema types.
    """
    # 1. Handle NULLs
    if not row.get('name') or row['name'].strip() == "":
        row['name'] = None
    
    # 2. Handle Numbers
    try:
        row['conversion_rate'] = int(row.get('conversion_rate', 1))
    except:
        row['conversion_rate'] = 1
        
    # 3. Handle Empty Strings for Text Fields
    for key in ['manufacturer', 'medex_url']:
        if not row.get(key):
            row[key] = ""
            
    # 4. Entry Status Default
    if not row.get('entry_status'):
        row['entry_status'] = "AI_L1"
    
    # 5. Handle UUIDs (updated_by) -> Must be None if empty, not ""
    if not row.get('updated_by'):
        row['updated_by'] = None
        
    return row

def process_single_row(supabase, row):
    """
    Uploads a single row. Returns (status, brand)
    status: 'INSERTED', 'SKIPPED', 'ERROR'
    """
    try:
        row = santize_row(row)
        
        # Check existence
        # Using exact match on (brand, strength, category) which covers main unique variance
        # Adding manufacturer/generic_name might be stricter but let's stick to core identity
        res = supabase.table(config.SUPABASE_TABLE).select("id").match({
            "brand": row['brand'],
            "strength": row['strength'],
            "category": row['category']
        }).execute()
        
        if res.data:
            return 'SKIPPED', row['brand']
            
        # Insert
        supabase.table(config.SUPABASE_TABLE).insert(row).execute()
        return 'INSERTED', row['brand']
        
    except Exception as e:
        return 'ERROR', f"{row.get('brand')} - {str(e)}"

def upload_csv_to_supabase(filepath):
    supabase = get_supabase_client()
    if not supabase: return

    print(f"\n🚀 Starting Parallel Upload for: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    total_rows = len(rows)
    print(f"📊 Found {total_rows} rows. Processing via ThreadPool...")
    
    if total_rows == 0:
        print("⚠️ File is empty.")
        return

    success_count = 0
    skip_count = 0
    fail_count = 0
    
    import concurrent.futures
    start_time = time.time()
    
    # Adjust workers based on CPU/Network. 3 is safer for Mac OS FD limits.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        future_to_row = {executor.submit(process_single_row, supabase, row): row for row in rows}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_row)):
            try:
                status, msg = future.result()
                
                if status == 'INSERTED':
                    success_count += 1
                    # print(f"   [+] Uploaded: {msg}") # Too spammy if fast
                elif status == 'SKIPPED':
                    skip_count += 1
                    # print(f"   [.] Skipped: {msg}")
                else:
                    fail_count += 1
                    print(f"   [!] Error: {msg}")
                    
                # Progress Bar effect
                if (i + 1) % 10 == 0:
                    print(f"   ... Processed {i + 1}/{total_rows} rows ...")
                    
            except Exception as exc:
                print(f"   [!!!] Data Error: {exc}")
                fail_count += 1

    duration = time.time() - start_time
    print(f"\n✨ Upload Complete in {duration:.2f}s")
    print(f"   Total: {total_rows}")
    print(f"   Inserted: {success_count}")
    print(f"   Skipped (Duplicates): {skip_count}")
    print(f"   Failed: {fail_count}")

def main():
    # 1. List Files
    files = glob.glob("data/*.csv")
    if not files:
        print("No CSV files found in data/ folder.")
        return

    print("\n📂 Available CSV Files:")
    for idx, f in enumerate(files):
        print(f"[{idx+1}] {f}")
        
    # 2. Ask User
    try:
        choice = input("\nEnter file number OR full file path to upload (or 'all'): ").strip()
        
        if choice.lower() == 'all':
            for f in files:
                upload_csv_to_supabase(f)
        elif os.path.exists(choice) and os.path.isfile(choice):
            # User entered a valid path
            upload_csv_to_supabase(choice)
        elif choice.isdigit():
            # User entered a number
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                upload_csv_to_supabase(files[idx])
            else:
                print("Invalid number selection.")
        else:
            print("Invalid input. Please enter a number or a valid file path.")
            
    except Exception as e:
        print(f"Invalid input: {e}")

if __name__ == "__main__":
    main()
