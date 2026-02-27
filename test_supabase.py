import config
from supabase import create_client, ClientOptions

print("Initializing Supabase client...")
options = ClientOptions(postgrest_client_timeout=5)
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY, options=options)

print("Attempting to query inventory_generics...")
try:
    res = supabase.table("inventory_generics").select("id").ilike("name", "Test").execute()
    print("Success! Data:", res.data)
except Exception as e:
    print("Error:", e)

print("Attempting to query inventory_global...")
try:
    res2 = supabase.table("inventory_global").select("id").limit(1).execute()
    print("Success! Data:", res2.data)
except Exception as e:
    print("Error:", e)

print("Done.")
