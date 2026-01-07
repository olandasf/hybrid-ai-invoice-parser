"""
Bendros utility funkcijos, naudojamos visame projekte.
"""
import re
import logging
from typing import Union, Optional


def clean_and_convert_to_float(value: Union[str, int, float, None]) -> Optional[float]:
    """
    Saugiai konvertuoja reikšmę į float tipą, apdorodamas europinį skaičių formatą.
    
    Args:
        value: Konvertuojama reikšmė
        
    Returns:
        float arba None jei konvertavimas nepavyko
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        # Pakeista, kad teisingai apdorotų neigiamus skaičius ir tarpus
        text = str(value).strip()
        
        # Pašaliname nereikalingus simbolius iš galo (pvz. taškus po OCR)
        text = text.rstrip('.')
        
        text = text.replace(' ', '').replace(',', '.')
        # Pašalinam viską, išskyrus skaičius, tašką ir minuso ženklą priekyje
        text = re.sub(r'[^\d.-]', '', text)
        if not text or text == '-':
            return None
        return float(text)
    except (ValueError, TypeError):
        return None


def safe_float(value: Union[str, int, float, None], default: float = 0.0) -> float:
    """
    Saugiai konvertuoja reikšmę į float su default reikšme.
    
    Args:
        value: Konvertuojama reikšmė
        default: Default reikšmė jei konvertavimas nepavyko
        
    Returns:
        float reikšmė
    """
    result = clean_and_convert_to_float(value)
    return result if result is not None else default


def format_currency(amount: float, decimals: int = 2) -> str:
    """
    Formatuoja sumą kaip valiutą su nurodytais dešimtainiais ženklais.
    
    Args:
        amount: Suma
        decimals: Dešimtainių ženklų skaičius
        
    Returns:
        Suformatuota suma
    """
    return f"{amount:.{decimals}f}"


def validate_positive_number(value: float, max_value: Optional[float] = None) -> tuple[bool, str]:
    """
    Validuoja ar skaičius yra teigiamas ir neviršija maksimalios reikšmės.
    
    Args:
        value: Validuojama reikšmė
        max_value: Maksimali leistina reikšmė
        
    Returns:
        tuple: (ar_validus, klaidos_pranešimas)
    """
    if value < 0:
        return False, "Reikšmė negali būti neigiama"
    
    if max_value is not None and value > max_value:
        return False, f"Reikšmė negali viršyti {max_value}"
    
    return True, ""


def log_function_call(func_name: str, **kwargs) -> None:
    """
    Užregistruoja funkcijos kvietimą su parametrais.
    
    Args:
        func_name: Funkcijos pavadinimas
        **kwargs: Funkcijos parametrai
    """
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logging.info("Kviečiama funkcija: %s(%s)", func_name, params)


def clean_volume_value(value: Union[str, int, float, None]) -> Optional[float]:
    """
    Specializuotas valymas tūrio laukui.
    Pašalina ABV procentus (pvz. '38%') iš tūrio eilutės, kad '0.7 38%' netaptų 0.738.
    Taip pat konvertuoja mililitrus į litrus, jei reikšmė > 20 (pvz. 750 -> 0.75).
    
    Args:
        value: Tūrio reikšmė su galimu ABV procentu
        
    Returns:
        float arba None jei konvertavimas nepavyko
    """
    if value is None:
        return None
    text = str(value)
    # Pašaliname procentus (pvz. "38%", "40 %")
    text = re.sub(r'\d+[.,]?\d*\s*%', '', text)
    
    val = clean_and_convert_to_float(text)
    
    if val is not None:
        # Jei reikšmė > 20, darome prielaidą, kad tai mililitrai (pvz. 750, 700, 500)
        # ir konvertuojame į litrus.
        # Tai ištaiso klaidą, kai "750" interpretuojama kaip 750 litrų.
        if val > 20:
            return val / 1000.0
            
    return val


def clean_product_name(name: str) -> str:
    """
    Išvalo produkto pavadinimą nuo pakavimo informacijos, kiekių ir kitų nereikalingų dalių.
    
    Pavyzdžiai:
        "Navimer Alcohol Pur Glass - carton @ 6 bottles x1 liter 96%" -> "Navimer Alcohol Pur Glass"
        "Chateau Margaux 2015 - case of 12 x 750ml" -> "Chateau Margaux 2015"
        "Vodka Premium 40% 0.7L x6" -> "Vodka Premium"
        "0.75L 12% Pinot Grigio" -> "Pinot Grigio"
        "carton @ 6 bottles x1 liter Navimer Alcohol" -> "Navimer Alcohol"
    
    Args:
        name: Originalus produkto pavadinimas
        
    Returns:
        Išvalytas produkto pavadinimas
    """
    if not name:
        return name
    
    original_name = name
    
    # ======================
    # A. PREFIKSAI (Pradžia)
    # ======================
    
    # 1. Pakuotės informacija pradžioje (pvz. "carton @ 6 bottles x", "case of 12")
    name = re.sub(r'^(carton|case|box|pack)\s*(@|of)?\s*\d+\s*(bottles?|btls?|buteliai|pcs|vnt\.?)?\s*(x|×)?\s*', '', name, flags=re.IGNORECASE).strip()
    
    # 2. Tūrio informacija su "x" pradžioje (pvz. "x 1 liter", "x 0.75l")
    name = re.sub(r'^(x|×)\s*\d+([.,]\d+)?\s*(liter|liters|litre|litres|l|cl|ml|ltr)\.?\s*', '', name, flags=re.IGNORECASE).strip()
    
    # 3. Standartinė tūrio informacija pradžioje (pvz. "0.75L ...", "1 liter ...", "750ml ...")
    name = re.sub(r'^\d+([.,]\d+)?\s*(liter|liters|litre|litres|l|cl|ml|ltr)\.?\s+', '', name, flags=re.IGNORECASE).strip()
    
    # 4. ABV informacija pradžioje (pvz. "39% ...", "40 % ...")
    name = re.sub(r'^\d+([.,]\d+)?\s*%\s*', '', name).strip()
    
    # 5. Tik skaičiai su kableliu/tašku pradžioje (pvz. "0,70 ...", "0.75 ...", "1,0 ...")
    # Svarbu: reikalaujame bent vieno skaitmens po kablelio, kad neištrintume "12 Years..."
    name = re.sub(r'^\d+[.,]\d+\s+', '', name).strip()
    
    # 6. Išvalome skyrybos ženklus pradžioje (pvz. "..Fernet", "- Fernet")
    name = re.sub(r'^[.,\-_]+\s*', '', name).strip()
    
    # ======================
    # B. SUFIKSAI (Pabaiga)
    # ======================
    
    # 1. Pašaliname pakavimo informaciją po brūkšnio ar dvitaškio
    # Pvz: "Product Name - carton @ 6 bottles" -> "Product Name"
    packaging_separators = [
        r'\s*-\s*carton\b.*',           # - carton ...
        r'\s*-\s*case\s*(of)?\b.*',     # - case of ...
        r'\s*-\s*box\s*(of)?\b.*',      # - box of ...
        r'\s*-\s*pack\s*(of)?\b.*',     # - pack of ...
        r'\s*-\s*\d+\s*(x|×)\s*\d+.*',  # - 6 x 750ml
        r'\s*:\s*\d+\s*(x|×)\s*\d+.*',  # : 6 x 750ml
    ]
    
    for pattern in packaging_separators:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # 2. Pašaliname "@" su kiekiu ir tolimesne informacija
    # Pvz: "Product @ 6 bottles x1 liter" -> "Product"
    name = re.sub(r'\s*@\s*\d+\s*(bottles?|btls?|buteliai|but\.?|pcs|vnt\.?|units?)?\b.*', '', name, flags=re.IGNORECASE)
    
    # 3. Pašaliname "x" arba "×" su kiekiu pavadinimo gale
    # Pvz: "Product x6" -> "Product", "Product 6x750ml" -> "Product"
    name = re.sub(r'\s*\d+\s*(x|×)\s*\d*\s*(ml|l|cl|liter|litre|bottles?|btls?|buteliai)?\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*(x|×)\s*\d+\s*(ml|l|cl|liter|litre|bottles?|btls?|buteliai)?\s*$', '', name, flags=re.IGNORECASE)
    
    # 4. Pašaliname tūrį ir ABV pavadinimo gale (tik jei jie pavadinimo pabaigoje)
    # Bet NELIEČIAME jei tai dalis pavadinimo kaip "Absolut 100" ar "Bacardi 151"
    # Pvz: "Vodka 0.7L 40%" -> "Vodka", bet "Absolut 100" lieka
    name = re.sub(r'\s+\d+[.,]?\d*\s*%\s*$', '', name)  # Pašalina "40%" gale
    name = re.sub(r'\s+\d+[.,]?\d*\s*(l|L|liter|litre|cl|ml)\b\s*(\d+[.,]?\d*\s*%)?$', '', name, flags=re.IGNORECASE)  # "0.7L 40%" gale
    
    # 5. Pašaliname pakavimo raktažodžius pavadinimo gale
    packaging_keywords = [
        r'\s+carton\s*(x|×)?\s*$',      # carton, carton x
        r'\s+carton\s+liter\s*$',       # carton liter
        r'\s+case\s*$', 
        r'\s+box\s*$',
        r'\s+pack\s*$',
        r'\s+bottles?\s*$',
        r'\s+btls?\s*$',
        r'\s+buteliai\s*$',
        r'\s+fee\s*$',                  # fee
        r'\s+liter\s*$',                # liter (be skaičiaus)
        r'\s+litre\s*$',                # litre
    ]
    for pattern in packaging_keywords:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # 6. Pašaliname pavienį "x" ar "×" gale (be skaičių)
    name = re.sub(r'\s+(x|×)\s*$', '', name, flags=re.IGNORECASE)
    
    # 7. Priedai su pliusu (pvz. "... + GB", "... + Gift Box")
    name = re.sub(r'\s*\+\s*(GB|Gift Box|Glass|Taurė|Dėžutė).*$', '', name, flags=re.IGNORECASE)
    
    # 8. Išvalome likusius tarpus ir skyrybos ženklus
    name = ' '.join(name.split())
    name = name.strip(' -:,')
    
    # Jei pavadinimas tapo tuščias arba per trumpas, grąžiname originalą
    if len(name) < 3:
        return original_name.strip()
    
    if name != original_name.strip():
        logging.debug(f"Produkto pavadinimas išvalytas: '{original_name}' -> '{name}'")
    
    return name