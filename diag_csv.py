import csv
import glob
from collections import defaultdict

def scan_csv_files():
    all_files = glob.glob("data/*.csv")
    total_rows = 0
    missing_generic = 0
    missing_manufacturer = 0
    
    issues_by_file = defaultdict(list)

    for file in all_files:
        with open(file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                total_rows += 1
                
                # Check for MEDICINE missing generic
                if row.get('type', '').upper() != 'OTHER':
                    gen = row.get('generic_name') or row.get('generic_id')
                    if not gen or str(gen).strip() == '':
                        missing_generic += 1
                        issues_by_file[file].append(f"Row {i+2}: Missing Generic")
                
                # Check missing manufacturer
                man = row.get('manufacturer') or row.get('manufacturer_id')
                if not man or str(man).strip() == '':
                    missing_manufacturer += 1
                    if len(issues_by_file[file]) == 0 or not issues_by_file[file][-1].startswith(f"Row {i+2}"):
                         issues_by_file[file].append(f"Row {i+2}: Missing Manufacturer")
                    else:
                         issues_by_file[file][-1] += " & Missing Manufacturer"

    print(f"--- Diagnostic Scan Complete ---")
    print(f"Total CSV Files Scanned: {len(all_files)}")
    print(f"Total Rows Checked: {total_rows}")
    print(f"Rows missing Generic Name: {missing_generic}")
    print(f"Rows missing Manufacturer Name: {missing_manufacturer}")
    
    if len(issues_by_file) > 0:
        print("\nFiles with issues:")
        for file, issues in list(issues_by_file.items())[:5]: # Show first 5
             print(f" - {file}: {len(issues)} issues (e.g., {issues[0]})")

if __name__ == "__main__":
    scan_csv_files()
