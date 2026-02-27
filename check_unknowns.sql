-- Check total count of items with Unknown Generic or Unknown Manufacturer
SELECT 
    COUNT(*) as total_unknown_items
FROM 
    public.inventory_global ig
LEFT JOIN 
    public.inventory_generics gen ON ig.generic_id = gen.id
LEFT JOIN 
    public.inventory_manufacturers man ON ig.manufacturer_id = man.id
WHERE 
    gen.name ILIKE 'Unknown Generic' 
    OR man.name ILIKE 'Unknown Manufacturer';

-- Breakdown by specific issues
SELECT 
    'Missing Generic (Unknown Generic)' as category,
    COUNT(*) as item_count
FROM 
    public.inventory_global ig
JOIN 
    public.inventory_generics gen ON ig.generic_id = gen.id
WHERE 
    gen.name ILIKE 'Unknown Generic'

UNION ALL

SELECT 
    'Missing Manufacturer (Unknown Manufacturer)' as category,
    COUNT(*) as item_count
FROM 
    public.inventory_global ig
JOIN 
    public.inventory_manufacturers man ON ig.manufacturer_id = man.id
WHERE 
    man.name ILIKE 'Unknown Manufacturer';

-- View actual Data Rows containing Unknowns (Limit 50)
SELECT 
    ig.id,
    ig.brand,
    gen.name as generic_name,
    man.name as manufacturer_name,
    ig.medex_url
FROM 
    public.inventory_global ig
LEFT JOIN 
    public.inventory_generics gen ON ig.generic_id = gen.id
LEFT JOIN 
    public.inventory_manufacturers man ON ig.manufacturer_id = man.id
WHERE 
    gen.name ILIKE 'Unknown Generic' 
    OR man.name ILIKE 'Unknown Manufacturer'
LIMIT 50;
