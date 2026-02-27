-- Run this exact SQL snippet in your Supabase SQL Editor to fix the broken RPC!
-- The previous RPC attempted to insert into `category_id`, but your table uses `category text`.

CREATE OR REPLACE FUNCTION public.global_inventory_add_data_from_python(
    p_type text, 
    p_category text, 
    p_brand text, 
    p_generic_name text, 
    p_strength text, 
    p_manufacturer_name text, 
    p_name text, 
    p_primary_unit text, 
    p_secondary_unit text, 
    p_conversion_rate integer, 
    p_item_code text, 
    p_medex_url text
) RETURNS json
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
DECLARE
    v_generic_id UUID;
    v_manufacturer_id UUID;
    v_enum_primary_unit public.unit_enum;
    v_enum_secondary_unit public.unit_enum;
    v_new_id UUID;
BEGIN
    IF p_generic_name IS NOT NULL AND p_generic_name != '' THEN 
        INSERT INTO public.inventory_generics (name)
        VALUES (TRIM(p_generic_name))
        ON CONFLICT (lower(btrim(name))) DO UPDATE SET name = EXCLUDED.name
        RETURNING id INTO v_generic_id;
    END IF;

    IF p_manufacturer_name IS NOT NULL AND p_manufacturer_name != '' THEN 
        INSERT INTO public.inventory_manufacturers (name)
        VALUES (TRIM(p_manufacturer_name))
        ON CONFLICT (lower(btrim(name))) DO UPDATE SET name = EXCLUDED.name
        RETURNING id INTO v_manufacturer_id;
    END IF;
    
    -- Fallbacks to satisfy `inventory_global_data_integrity`
    IF p_type = 'MEDICINE' THEN
        IF v_generic_id IS NULL THEN
            INSERT INTO public.inventory_generics (name)
            VALUES ('Unknown Generic')
            ON CONFLICT (lower(btrim(name))) DO UPDATE SET name = EXCLUDED.name
            RETURNING id INTO v_generic_id;
        END IF;
        
        IF v_manufacturer_id IS NULL THEN
            INSERT INTO public.inventory_manufacturers (name)
            VALUES ('Unknown Manufacturer')
            ON CONFLICT (lower(btrim(name))) DO UPDATE SET name = EXCLUDED.name
            RETURNING id INTO v_manufacturer_id;
        END IF;
    END IF;
    
    v_enum_primary_unit := COALESCE(public.text_to_unit_enum(p_primary_unit), 'piece'::public.unit_enum);
    v_enum_secondary_unit := public.text_to_unit_enum(p_secondary_unit);

    IF p_type = 'MEDICINE' THEN
        INSERT INTO public.inventory_global (
            type, category, brand, generic_id, strength, manufacturer_id, name,
            primary_unit, secondary_unit, conversion_rate, item_code, medex_url, entry_status
        )
        VALUES (
            CAST(p_type AS public.inventory_type_enum), p_category, p_brand, v_generic_id, p_strength, v_manufacturer_id, p_name,
            v_enum_primary_unit, v_enum_secondary_unit, COALESCE(p_conversion_rate, 1), COALESCE(p_item_code, ''), p_medex_url, 'AI_L1'
        )
        ON CONFLICT (lower(btrim(brand)), generic_id, lower(btrim(COALESCE(strength, ''::text))), manufacturer_id, lower(btrim(category))) WHERE (type = 'MEDICINE'::public.inventory_type_enum) DO NOTHING
        RETURNING id INTO v_new_id;
    ELSE
        INSERT INTO public.inventory_global (
            type, category, brand, generic_id, strength, manufacturer_id, name,
            primary_unit, secondary_unit, conversion_rate, item_code, medex_url, entry_status
        )
        VALUES (
            CAST(p_type AS public.inventory_type_enum), p_category, p_brand, v_generic_id, p_strength, v_manufacturer_id, p_name,
            v_enum_primary_unit, v_enum_secondary_unit, COALESCE(p_conversion_rate, 1), COALESCE(p_item_code, ''), p_medex_url, 'AI_L1'
        )
        RETURNING id INTO v_new_id;
    END IF;

    RETURN json_build_object('code', 'SUCCESS', 'id', v_new_id);
EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object('code', 'INTERNAL_ERROR', 'message', SQLERRM);
END;
$$;
