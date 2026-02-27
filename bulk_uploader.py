import os
import sys
import csv
import glob
import logging
import asyncio
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from supabase import create_async_client, ClientOptions
import config

def debug_log(msg):
    with open("debug.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} - {msg}\n")

# Suppress debug logs from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.ERROR)

console = Console()

async def get_supabase_client():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    if "your-project" in url or "your-service" in key:
        return None
    options = ClientOptions(postgrest_client_timeout=15)
    return await create_async_client(url, key, options=options)

def sanitize_row(row):
    """
    Cleans up a CSV row to stricly match the Supabase `inventory_global` schema.
    """
    clean = {}
    clean['type'] = row.get('type', 'MEDICINE').upper()
    if clean['type'] not in ['MEDICINE', 'OTHER']:
        clean['type'] = 'MEDICINE'

    clean['category'] = row.get('category', 'Miscellaneous')
    
    clean['brand'] = row.get('brand', None)
    if clean['brand'] and clean['brand'].strip() == "":
        clean['brand'] = None

    clean['strength'] = row.get('strength', 'N/A')
    
    clean['name'] = row.get('name', None)
    if clean['type'] == 'MEDICINE':
        clean['name'] = None
    elif clean['type'] == 'OTHER' and not clean['name']:
        clean['name'] = 'Unknown Product'

    clean['primary_unit'] = row.get('primary_unit', 'piece')
    clean['secondary_unit'] = row.get('secondary_unit', None)
    if clean['secondary_unit'] and clean['secondary_unit'].strip() == "":
        clean['secondary_unit'] = None

    try:
        clean['conversion_rate'] = int(row.get('conversion_rate', 1))
    except:
        clean['conversion_rate'] = 1

    clean['item_code'] = row.get('item_code', '')
    clean['medex_url'] = row.get('medex_url', None)
    if clean['medex_url'] and clean['medex_url'].strip() == "":
        clean['medex_url'] = None

    clean['entry_status'] = row.get('entry_status', 'AI_L1')
    
    clean['updated_by'] = row.get('updated_by', None)
    if clean['updated_by'] and clean['updated_by'].strip() == "":
         clean['updated_by'] = None

    clean['generic_name_raw'] = row.get('generic_id', None)
    clean['manufacturer_name_raw'] = row.get('manufacturer_id', None)
    
    clean['generic_id'] = None
    clean['manufacturer_id'] = None

    return clean

async def resolve_dependency_direct(supabase, table_name, name_val):
    if not name_val or name_val.strip() == "":
        return None
    name_val = name_val.strip()
    
    debug_log(f"Resolving dependency: {table_name} for '{name_val}'")
    try:
        # 1. Select
        debug_log(f"Executing SELECT on {table_name}")
        res = await supabase.table(table_name).select("id").ilike("name", name_val).execute()
        debug_log(f"SELECT returned: {res.data}")
        if res.data and len(res.data) > 0:
            return res.data[0]['id']
            
        # 2. Insert
        debug_log(f"Executing INSERT on {table_name}")
        ins = await supabase.table(table_name).insert({"name": name_val}).execute()
        debug_log(f"INSERT returned: {ins.data}")
        if ins.data and len(ins.data) > 0:
            return ins.data[0]['id']
    except Exception as e:
        debug_log(f"Exception in resolve_dependency_direct: {e}")
        pass
    return None

async def process_single_row(supabase, row, semaphore):
    async with semaphore:
        try:
            data = sanitize_row(row)
            
            is_medicine = data['type'] == 'MEDICINE'
            
            # Helper to return None instead of an empty string
            def none_if_empty(val, default_val=None):
                if val is None: return default_val
                if isinstance(val, str) and str(val).strip() == '': return default_val
                return val
            
            data['generic_name_raw'] = none_if_empty(row.get('generic_name'))
            data['manufacturer_name_raw'] = none_if_empty(row.get('manufacturer'))

            # 2. Check existence
            debug_log(f"Checking existence in global inventory")
            if data['type'] == 'MEDICINE':
                res = await supabase.table(config.SUPABASE_TABLE).select("id").match({
                    "brand": data['brand'],
                    "strength": data['strength'],
                    "category": data['category']
                }).execute()
            else:
                res = await supabase.table(config.SUPABASE_TABLE).select("id").match({
                    "name": data['name'],
                    "category": data['category']
                }).execute()
                
            debug_log(f"Existence check returned: {res.data}")
            if res.data:
                identifier = data['brand'] if data['type'] == 'MEDICINE' else data['name']
                return 'SKIPPED', identifier
                
            # 3. Insert via SECURITY DEFINER RPC to bypass table permissions
            debug_log(f"Inserting into global inventory via RPC")
            
            # The RPC has two signatures. The newest uses category_id UUIDs exclusively.
            # To avoid UUID lookups entirely for the primary script, we use the older signature:
            # function global_inventory_add_data_from_python(p_category text, p_name text, p_brand text, p_generic_name text, p_strength text, p_base_unit text, p_manufacturer text, p_item_code text, p_unit_per_strip smallint DEFAULT 1)
            
            # Since the user specifically disabled RLS and expects direct inserts, and the 2nd signature supports only limited args
            # We will use the second overloaded RPC which natively handles generics and manufacturers for us and bypasses Grants!
            
            # Strictly obey `inventory_global_data_integrity` Postgres CHECK constraints:
            # MEDICINE: brand NOT NULL, generic_id NOT NULL, strength NOT NULL, name IS NULL
            # OTHER: name NOT NULL, brand IS NULL, generic_id IS NULL, strength IS NULL
            
            rpc_payload = {
                "p_type": data['type'],
                "p_category": none_if_empty(data.get('category'), 'Miscellaneous'), 
                "p_brand": none_if_empty(data.get('brand')) if is_medicine else None,
                "p_generic_name": data['generic_name_raw'] if is_medicine else None, 
                "p_strength": none_if_empty(data.get('strength'), 'N/A') if is_medicine else None,
                "p_manufacturer_name": data['manufacturer_name_raw'], 
                "p_name": None if is_medicine else none_if_empty(data.get('name')),
                "p_primary_unit": none_if_empty(data.get('primary_unit', 'piece')),
                "p_secondary_unit": none_if_empty(data.get('secondary_unit')),
                "p_conversion_rate": data.get('conversion_rate', 1),
                "p_item_code": none_if_empty(data.get('item_code'), ''),
                "p_medex_url": none_if_empty(data.get('medex_url'))
            }
            
            # Temporary Debug Print
            if is_medicine:
                debug_log(f"RPC Payload: {rpc_payload}")

            res = await supabase.rpc("global_inventory_add_data_from_python", rpc_payload).execute()
            debug_log(f"RPC Insert returned: {res.data}")
            
            if res.data and isinstance(res.data, dict) and res.data.get('code') != 'SUCCESS':
                 raise Exception(res.data.get('message', 'RPC Failed'))
                 
            identifier = data.get('brand') if data['type'] == 'MEDICINE' else data.get('name')
            return 'INSERTED', identifier
            
        except Exception as e:
            debug_log(f"Exception in process_single_row: {e}")
            identifier = row.get('brand') or row.get('name') or "Unknown"
            return 'ERROR', f"{identifier} - {str(e)}"

async def async_main():
    console.print(Panel(Text("Medidesh Supabase Data Uploader", justify="center", style="bold cyan"), expand=False))
    
    supabase = await get_supabase_client()
    if not supabase:
        console.print("[bold red]Error:[/] Supabase connection failed. Check your config.py credentials.")
        sys.exit(1)

    # File Selection
    files = glob.glob("data/*.csv")
    if not files:
        console.print("[bold yellow]No CSV files found in the 'data/' folder.[/]")
        sys.exit(0)
    
    files.sort()
    
    table = Table(title="Available CSV Data Files", show_header=True, header_style="bold magenta")
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Filename", style="green")
    table.add_column("Size", justify="right")
    
    for idx, f in enumerate(files):
        size_mb = os.path.getsize(f) / (1024 * 1024)
        table.add_row(str(idx + 1), os.path.basename(f), f"{size_mb:.2f} MB")
        
    console.print(table)
    
    file_idx = Prompt.ask("\nSelect the [cyan]ID[/] of the file to upload (or type 'all')", default="1")
    
    if file_idx.lower() == 'all':
        selected_files = files
        console.print(f"\n[bold]Selected All Files:[/] [green]{len(selected_files)} files[/]")
    else:
        try:
            selected_files = [files[int(file_idx) - 1]]
            console.print(f"\n[bold]Selected File:[/] [green]{os.path.basename(selected_files[0])}[/]")
        except (IndexError, ValueError):
            console.print("[bold red]Invalid selection. Exiting.[/]")
            sys.exit(1)
        
    if not Confirm.ask("Are you sure you want to continuously upload to Supabase now?"):
        sys.exit(0)

    overall_inserted = 0
    overall_skipped = 0
    overall_failed = 0
    overall_errors = []
    total_processed_global = 0

    console.print("\n[bold cyan]Starting Bulk Upload...[/]")
    
    semaphore = asyncio.Semaphore(15)
    
    for selected_file in selected_files:
        console.print(f"\n[bold blue]Processing File:[/] {os.path.basename(selected_file)}")
        with open(selected_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        total_rows = len(rows)
        if total_rows == 0:
            console.print("[bold yellow]Skipping empty file.[/]")
            continue
            
        total_processed_global += total_rows

        inserted = 0
        skipped = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[green]Uploading...", total=total_rows)
            
            # Create asynchronous tasks for all rows
            tasks = [process_single_row(supabase, row, semaphore) for row in rows]
            
            # Process them as they complete to update the progress bar in real-time
            for coroutine in asyncio.as_completed(tasks):
                status, msg = await coroutine
                
                if status == 'INSERTED':
                    inserted += 1
                    overall_inserted += 1
                elif status == 'SKIPPED':
                    skipped += 1
                    overall_skipped += 1
                else:
                    failed += 1
                    overall_failed += 1
                    overall_errors.append(f"{os.path.basename(selected_file)} - {msg}")
                    
                progress.update(task, advance=1, description=f"[cyan]({inserted} Ins, {skipped} Skip, {failed} Err)")

    # Beautiful Summary
    console.print("\n")
    
    permission_denied = any("permission denied" in str(err) or "42501" in str(err) for err in overall_errors)
    if permission_denied:
        warning_text = Text()
        warning_text.append("Oops! Supabase rejected the upload due to Database Permissions (42501).\n\n", style="bold red")
        warning_text.append("Even with RLS disabled, the 'anon' key requires explicit table grants.\n", style="yellow")
        warning_text.append("To fix this permanently, please do ONE of the following:\n\n", style="white")
        warning_text.append("Option A (Recommended): ", style="bold cyan")
        warning_text.append("Replace SUPABASE_KEY in config.py with your ", style="white")
        warning_text.append("service_role", style="bold green")
        warning_text.append(" secret key.\n", style="white")
        warning_text.append("Option B: ", style="bold cyan")
        warning_text.append("Run this SQL in your Supabase dashboard:\n", style="white")
        warning_text.append("GRANT INSERT, UPDATE ON inventory_global TO anon;\n", style="bold magenta")
        warning_text.append("GRANT INSERT, UPDATE ON inventory_generics TO anon;\n", style="bold magenta")
        warning_text.append("GRANT INSERT, UPDATE ON inventory_manufacturers TO anon;", style="bold magenta")
        
        console.print(Panel(warning_text, title="[bold red]⚠️  Permission Denied Detected", border_style="red", padding=(1, 2)))
        console.print("\n")

    summary = Table(title="Upload Summary Results", show_header=True, header_style="bold")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value", justify="right")
    
    summary.add_row("Total Files Processed", str(len(selected_files)))
    summary.add_row("Total Rows Processed", str(total_processed_global))
    summary.add_row("[green]Successfully Inserted[/]", f"[green]{overall_inserted}[/]")
    summary.add_row("[yellow]Duplicates Skipped[/]", f"[yellow]{overall_skipped}[/]")
    summary.add_row("[red]Failed Rows[/]", f"[red]{overall_failed}[/]")
    
    console.print(summary)
    
    if overall_failed > 0:
        console.print("\n[bold red]Error Log Extract (First 10):[/]")
        for e in overall_errors[:10]:
            console.print(f" - [red]{e}[/]")

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nUpload aborted.")

if __name__ == "__main__":
    main()
