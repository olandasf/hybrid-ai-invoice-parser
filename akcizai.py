import re
import logging
from category import classify_alcohol
from utils import clean_and_convert_to_float, safe_float as utils_safe_float

def safe_float(value, default=0.0):
    """Saugiai konvertuoja reikšmę į float, apdorodamas None ir kitas problemas"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            # Pašaliname tarpus ir keičiame kablelį į tašką
            cleaned = str(value).strip().replace(',', '.')
            if not cleaned or cleaned == '':
                return default
            return float(cleaned)
        except (ValueError, TypeError):
            return default
    return default

# AKCIZŲ TARIFAI 2026 m. (nuo 2026-01-01 iki 2026-12-31)
TARIFAI = {
    'ethyl_alcohol': 3130.0,           # 3130 EUR/HL gryno etilo alkoholio
    'intermediate_15_22': 411.0,       # 411 EUR/HL (>15% ABV)
    'intermediate_up_to_15': 365.0,    # 365 EUR/HL (≤15% ABV)
    'wine_8.5_15': 296.0,              # 296 EUR/HL (>8,5% ABV)
    'wine_up_to_8.5': 148.0,           # 148 EUR/HL (≤8,5% ABV)
    'sparkling_wine_over_8_5': 296.0,  # 296 EUR/HL (>8,5% ABV)
    'sparkling_wine_up_to_8_5': 148.0, # 148 EUR/HL (≤8,5% ABV)
    'beer': 12.74,                     # 12,74 EUR už 1% ABV/HL
}

CATEGORY_LABELS = {
    'ethyl_alcohol': 'Etilo alkoholis (spiritiniai gėrimai, likeriai)',
    'intermediate_15_22': 'Tarpinis produktas >15%-22% (pvz., portveinas, cheresas)',
    'intermediate_up_to_15': 'Tarpinis produktas >1,2%-15% (pvz., vermutas)',
    'wine_8.5_15': 'Vynas/fermentuotas neputojantis >8,5%-15%',
    'wine_up_to_8.5': 'Vynas/fermentuotas neputojantis >1,2%-8,5%',
    'sparkling_wine_over_8_5': 'Putojantis vynas/fermentuotas >8,5%',
    'sparkling_wine_up_to_8_5': 'Putojantis vynas/fermentuotas >1,2%-8,5%',
    'beer': 'Alus',
    'non_alcohol': 'Nealkoholinis/Neapmokestinama',
}

def parse_volume_and_abv(name_str: str) -> tuple[float | None, float | None]:
    if not name_str: return None, None
    name_lower = name_str.lower()
    volume, abv = None, None
    
    # Specialūs produktai su fiksuotu tūriu
    if 'clos saint jean sanctus sanctorum' in name_lower:
        volume = 1.5  # Šis vynas visada pilstomas tik į 1,5L butelius
    elif 'jack daniel' in name_lower:
        volume = 3.0  # Jack Daniel's VISADA 3L buteliai (BSC importuoja tik tokius)
    
    # Specialūs butelių dydžiai (tikrinti ilgesnius pavadinimus pirma!)
    elif 'double magnum' in name_lower or 'dbl mgn' in name_lower:
        volume = 3.0
    elif 'magnum' in name_lower or 'mgn' in name_lower: 
        volume = 1.5
    elif 'jeroboam' in name_lower: 
        volume = 3.0
    elif 'rehoboam' in name_lower:
        volume = 4.5
    elif 'mathusalem' in name_lower or 'methuselah' in name_lower:
        volume = 6.0
    elif 'salmanazar' in name_lower:
        volume = 9.0
    elif 'balthazar' in name_lower:
        volume = 12.0
    elif 'nebuchadnezzar' in name_lower:
        volume = 15.0
    
    # Jei specialus dydis nerastas, ieškome standartinio tūrio
    if volume is None:
        vol_match = re.search(r'(\d+[\.,]?\d*)\s*(l|cl|ml)', name_lower)
        if vol_match:
            val = float(vol_match.group(1).replace(',', '.'))
            unit = vol_match.group(2)
            if unit == 'l': volume = val
            elif unit == 'cl': volume = val / 100.0
            elif unit == 'ml': volume = val / 1000.0
    
    # ABV paieška
    abv_match = re.search(r'(\d+[\.,]?\d*)\s*%', name_lower)
    if abv_match: abv = float(abv_match.group(1).replace(',', '.'))
    
    return volume, abv

def enrich_products_with_excise(products_data: list, transport_total_overall: float = 0.0) -> list:
    """
    Pakeista: Funkcija nebeskaičiuoja nuolaidos iš naujo, o naudoja
    jau apskaičiuotas reikšmes iš 'app.py'.
    """
    enriched_products = []
    if not products_data:
        return []

    # Skaičiuojame bendrą tūrį transporto paskirstymui
    total_volume_quantity_for_transport = 0
    for prod_data in products_data:
        try:
            # Gauti produkto pavadinimą
            name = str(prod_data.get('name', '')).lower()
            
            # Tikriname ar tai stiklinės (glassware)
            is_glassware = any(keyword in name for keyword in [
                'glas', 'glass', 'taure', 'taures', 'stiklinė', 'stiklines', 'goblet', 
                'bokalas', 'bokalai', 'kupa', 'čižas', 'čiažai', 'decanter', 'dekanteris',
                'spiegelau', 'schott', 'ravenscroft', 'nordic', 'orrefors'
            ])
            
            vol = float(str(prod_data.get('volume', 0)).replace(',', '.'))
            qty = float(str(prod_data.get('quantity', 0)).replace(',', '.'))
            
            # Jei tai stiklinės, naudojame 0.2L tūrį skaičiavimams
            if is_glassware and qty > 0:
                vol = 0.2  # Standartinis stiklinės tūris 0.2L (pagal naują reikalavimą)
                logging.info(f"Stiklinėms '{name}' naudojamas tūris transporto skaičiavimui: {vol}L")
            
            if qty > 0 and vol > 0:
                total_volume_quantity_for_transport += vol * qty
        except (ValueError, TypeError): 
            pass
    
    logging.debug(f"AKCIZAI.PY - Bendras tūris*kiekis transportui: {total_volume_quantity_for_transport}")

    # Apdorojame kiekvieną produktą
    for product_item in products_data:
        # 1. Gauname pradinius duomenis su saugiu konvertavimu
        name = str(product_item.get('name', ''))
        name_lower = name.lower()
        quantity = safe_float(product_item.get('quantity', 0))
        unit_price = safe_float(product_item.get('unit_price', 0))
        
        # Perskaičiuojame 'amount' pagal pakeistą 'unit_price'
        if quantity > 0:
            amount = unit_price * quantity
        else:
            amount = safe_float(product_item.get('amount', 0))
        volume = safe_float(product_item.get('volume', 0))
        abv = safe_float(product_item.get('abv', 0))
        
        # 2. Paimame JAU APSKAIČIUOTAS kainas su nuolaida iš app.py
        unit_price_with_discount = safe_float(product_item.get('unit_price_with_discount', unit_price))
        
        # Perskaičiuojame 'amount_with_discount' pagal pakeistą 'unit_price_with_discount'
        if quantity > 0:
            amount_with_discount = unit_price_with_discount * quantity
        else:
            amount_with_discount = safe_float(product_item.get('amount_with_discount', amount))

        discount_percentage = safe_float(product_item.get('discount_percentage', 0))
        
        # 3. Kategorijos nustatymas
        final_category_key = product_item.get('excise_category_key')
        if not final_category_key or final_category_key not in CATEGORY_LABELS:
            final_category_key = classify_alcohol(name, abv, volume)  # Perduodame ir tūrį pakuočių atpažinimui 

        # 4. Akcizo skaičiavimas
        excise_per_unit = 0.0
        if final_category_key != 'non_alcohol' and volume > 0 and final_category_key in TARIFAI:
            rate = TARIFAI[final_category_key]
            if final_category_key == 'ethyl_alcohol':
                excise_per_unit = (volume / 100.0) * (abv / 100.0) * rate
            elif final_category_key == 'beer':
                excise_per_unit = (volume / 100.0) * rate
            else:
                excise_per_unit = (volume / 100.0) * rate # Tarifai dabar yra EUR/HL
        excise_total = excise_per_unit * quantity

        # 5. Transporto skaičiavimas
        transport_per_unit = 0.0
        transport_total_item = 0.0
        
        # Tikriname ar tai stiklinės
        is_glassware = any(keyword in name_lower for keyword in [
            'glas', 'glass', 'taure', 'taures', 'stiklinė', 'stiklines', 'goblet', 
            'bokalas', 'bokalai', 'kupa', 'čižas', 'čiažai', 'decanter', 'dekanteris',
            'spiegelau', 'schott', 'ravenscroft', 'nordic', 'orrefors'
        ])
        
        # Jei tai stiklinės, naudojame 0.2L tūrį transporto skaičiavimui
        transport_volume = volume
        if is_glassware and quantity > 0:
            transport_volume = 0.2
            logging.info(f"Stiklinėms '{name}' naudojamas tūris transporto skaičiavimui: {transport_volume}L")
        
        if quantity > 0 and transport_volume > 0 and total_volume_quantity_for_transport > 0 and transport_total_overall > 0:
            item_volume_qty_product = transport_volume * quantity
            proportion = item_volume_qty_product / total_volume_quantity_for_transport
            transport_total_item = transport_total_overall * proportion
            transport_per_unit = transport_total_item / quantity 

        # 6. Savikainos skaičiavimas (naudojant kainą su nuolaida)
        cost_wo_vat = unit_price_with_discount + excise_per_unit + transport_per_unit
        cost_w_vat = cost_wo_vat * 1.21
        
        enriched_products.append({
            'name': name,
            'volume': volume,  # Koreguotas tūris pagal produkto kategoriją
            'abv': abv,
            'quantity': quantity,
            'unit_price': unit_price,
            'unit_price_with_discount': unit_price_with_discount,
            'discount_percentage': discount_percentage,
            'amount': amount,
            'amount_with_discount': amount_with_discount,
            'excise_category_key': final_category_key, 
            'excise_category': CATEGORY_LABELS.get(final_category_key, 'N/A'),
            'excise_per_unit': excise_per_unit,
            'excise_total': excise_total,
            'transport_per_unit': transport_per_unit,
            'transport_total': transport_total_item,
            'cost_wo_vat': cost_wo_vat,
            'cost_w_vat': cost_w_vat,
            'cost_wo_vat_total': cost_wo_vat * quantity,
            'cost_w_vat_total': cost_w_vat * quantity,
        })
        
    return enriched_products