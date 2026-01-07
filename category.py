# category.py
import re
import logging
import json
import os

# Įkeliame išimtis iš JSON failo
EXCEPTIONS_FILE = "product_exceptions.json"
PRODUCT_EXCEPTIONS = {}

try:
    if os.path.exists(EXCEPTIONS_FILE):
        with open(EXCEPTIONS_FILE, 'r', encoding='utf-8') as f:
            PRODUCT_EXCEPTIONS = json.load(f)
            logging.info(f"Sėkmingai įkeltos produktų išimtys iš {EXCEPTIONS_FILE}")
    else:
        logging.warning(f"Išimčių failas {EXCEPTIONS_FILE} nerastas.")
except Exception as e:
    logging.error(f"Klaida įkeliant išimčių failą: {e}")

def simplify_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    replacements = {
        '[éèêë]': 'e', '[áàâä]': 'a', '[óòôö]': 'o', '[úùûü]': 'u',
        '[íìîï]': 'i', 'č': 'c', 'š': 's', 'ž': 'z', 'ņ': 'n', 'ķ': 'k',
        'ļ': 'l', 'ģ': 'g', 'ł': 'l', 'ś': 's', 'ź': 'z', 'ż': 'z'
    }
    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text)
    text = re.sub(r'[^\w\s\.-]', '', text)
    return text

def check_for_keyword(text: str, keywords: list) -> str | None:
    """Optimizuota raktažodžių paieška."""
    for kw in keywords:
        try:
            # Naudojame word boundary tik jei reikia
            if len(kw) > 2:  # Trumpiems žodžiams nereikia word boundary
                if re.search(r'\b' + re.escape(kw) + r'\b', text):
                    logging.debug("RASTAS RAKTAŽODIS '%s' tekste '%s'", kw, text[:50])
                    return kw
            else:
                if kw in text:
                    logging.debug("RASTAS RAKTAŽODIS (paprasta paieška) '%s' tekste '%s'", kw, text[:50])
                    return kw
        except re.error:
            if kw in text:
                logging.debug("RASTAS RAKTAŽODIS (fallback) '%s' tekste '%s'", kw, text[:50])
                return kw
    return None

def classify_alcohol(name: str, abv_param: float | None, volume_param: float | None = None) -> str:
    logging.info(f"Pradedamas klasifikavimas: prekė - '{name}', ABV - {abv_param}, Tūris - {volume_param}")
    if not isinstance(name, str):
        name = ""
    s_name = simplify_text(name)
    abv = float(abv_param) if isinstance(abv_param, (int, float)) and abv_param >= 0 else 0.0
    volume = float(volume_param) if isinstance(volume_param, (int, float)) and volume_param > 0 else 0.0
    logging.info(f"Klasifikuojama: '{s_name}', ABV: {abv}%, Tūris: {volume}L")

    # Taisyklė #-1: PAKUOTĖS/DĖŽUTĖS be tūrio ir be alkoholio
    # Jei produktas neturi nei tūrio, nei ABV, ir pavadinime yra "box", "gift", "packaging" - tai pakuotė
    packaging_keywords = ['gift box', 'giftbox', 'gift-box', 'single box', 'packaging', 'pakuotė', 'dėžutė', 'empty box', 'wooden box', 'wood box']
    if volume == 0 and abv == 0:
        if check_for_keyword(s_name, packaging_keywords):
            logging.info(f"Priskirta 'non_alcohol' - pakuotė/dėžutė be tūrio ir alkoholio: '{name}'")
            return 'non_alcohol'

    # Taisyklė #0: KONKREČIOS IŠIMTYS (Iš JSON failo)
    # 1. Tikslūs pavadinimai
    if PRODUCT_EXCEPTIONS.get('force_non_alcohol_exact'):
        for exact_name in PRODUCT_EXCEPTIONS['force_non_alcohol_exact']:
            if simplify_text(exact_name) in s_name:
                logging.info(f"Priskirta 'non_alcohol' pagal tikslią išimtį: {exact_name}")
                return 'non_alcohol'

    # Taisyklė #0.5: Priverstinės vyno išimtys (Hardcoded)
    # Tai apeina visas kitas taisykles, įskaitant etilo alkoholį
    forced_wine_exceptions = ['acediano']
    if check_for_keyword(s_name, forced_wine_exceptions):
        logging.info(f"Priverstinė vyno išimtis: '{name}' -> wine_8.5_15")
        return 'wine_8.5_15'

    # 2. Sudėtiniai raktažodžiai (visi turi būti rasti)
    if PRODUCT_EXCEPTIONS.get('force_non_alcohol_combined'):
        for combo in PRODUCT_EXCEPTIONS['force_non_alcohol_combined']:
            if all(simplify_text(k) in s_name for k in combo):
                logging.info(f"Priskirta 'non_alcohol' pagal sudėtinę išimtį: {combo}")
                return 'non_alcohol'

    # 3. Pavieniai raktažodžiai (bet kuris)
    if PRODUCT_EXCEPTIONS.get('force_non_alcohol_contains'):
        for kw in PRODUCT_EXCEPTIONS['force_non_alcohol_contains']:
            if simplify_text(kw) in s_name:
                logging.info(f"Priskirta 'non_alcohol' pagal raktažodį išimtyse: {kw}")
                return 'non_alcohol'

    # Taisyklė #1: Etilo alkoholis (AUKŠČIAUSIAS PRIORITETAS)
    # Jei randame stipraus alkoholio raktažodį, iškart priskiriame kategoriją,
    # neatsižvelgiant į kitus raktažodžius, pvz., 'glass' ar 'box'.
    ethyl_main_keywords = [
        'vodka', 'degtine', 'spiritus', 'spirytus', 'whisky', 'viskis', 'whiskey', 'bourbon', 'scotch',
        'rum', 'romas', 'rhum', 'gin', 'dzinas', 'tequila', 'tekila', 'brandy', 'brendis',
        'cognac', 'konjakas', 'armagnac', 'absinthe', 'absentas', 'liqueur', 'likeris', 'likor', 'likieris',
        'spirituose', 'bitter', 'balzams', 'trauktine', 'nalewka', 'nastoyka', 'aquavit', 'grappa',
        'calvados', 'jagermeister', 'st germain', 'st. germain', 'unicum',
        # Papildomi raktažodžiai pagal vartotojo pavyzdžius
        'laphroaig', 'barcelo', 'glen grant', 'fernet', 'old pulteney',
        'glendronach', 'corazon', 'frapin', 'crown royal', 'bunnahabhain',
        'oban', 'tomatin', 'sheridans',
        # Likieriai ir kreminiai gėrimai
        'carolans', 'irish cream', 'cream liqueur', 'baileys', 'kahlua', 'amaretto', 'sambuca', 'passoa',
        # Vermutas ir aperityvai
        'dubonnet', 'vermouth', 'vermutas', 'aperitif', 'aperityvas', 'martini rosso', 'martini bianco',
        'campari', 'aperol', 'cynar', 'punt e mes'
    ]
    if check_for_keyword(s_name, ethyl_main_keywords):
        logging.info(f"Priskirta kategorija 'ethyl_alcohol' pagal aukščiausio prioriteto raktažodį.")
        return 'ethyl_alcohol'

    # Taisyklė #2: IŠIMTYS - ne produktai (veikia tik jei nerastas stiprus alkoholis)
    non_product_exceptions = [
        # Stiklinės ir priedai
        'glas', 'glass', 'taure', 'taures', 'stiklinė', 'stiklines', 'goblet', 
        'bokalas', 'bokalai', 'kupa', 'čižas', 'čiažai', 'decanter', 'dekanteris',
        'spiegelau', 'schott', 'ravenscroft', 'nordic', 'orrefors',
        # Pakuotės ir transportas
        'palette', 'palete', 'box', 'gift box', 'giftbox', 'gift-box', 'dėžutė', 'packaging', 'pakuotė', 'empty box', 'carton', 'case',
        # Sistemos sugeneruoti pavadinimai
        '(be pavadinimo)'
    ]
    
    if check_for_keyword(s_name, non_product_exceptions):
        logging.info(f"Priskirta kategorija 'non_alcohol' pagal išimtį (pvz., 'glass'), nes nerasta stipraus alkoholio raktažodžių.")
        return 'non_alcohol'

    # Taisyklė #3: Alus
    beer_keywords = ['beer', 'alus', 'bier', 'biere', 'cerveza', 'birra', 'õlu', 'lager', 'ale', 'stout', 'pilsner', 'ipa', 'porter', 'saison', 'gose', 'sour', 'gira']
    if check_for_keyword(s_name, beer_keywords):
        logging.info(f"Priskirta kategorija 'beer' arba 'non_alcohol' pagal ABV.")
        return 'beer' if abv > 1.2 else 'non_alcohol'

    # Taisyklė #4: Nealkoholinis pagal ABV ARBA "alc free" raktažodžius
    non_alcohol_keywords = [
        'alc free', 'alcohol free', 'non alcoholic', 'sans alcool', 'alkoholfrei', 'sin alcohol',
        # Dutch terms for non-alcoholic
        'alcoholvrije', 'alcoholvrij', 'alcoholvri'
    ]
    if abv <= 1.2 or check_for_keyword(s_name, non_alcohol_keywords):
        logging.info(f"Priskirta kategorija 'non_alcohol' pagal ABV <= 1.2 arba raktažodį.")
        return 'non_alcohol'

    # Taisyklė #5: Putojantys vynai - PATOBULINTA LOGIKA
    sparkling_keywords = [
        'champagne', 'sampanas', 'champagner', 'prosecco', 'cava', 'sekt', 'spumante', 'frizzante', 
        'asti', 'sparkling', 'putojantis', 'cremant', 'mousseux', 'franciacorta', 
        'brut', 'extra brut', 'crystal',
        # Šampano namai ir žinomi brendai
        'louis roederer', 'roederer', 'moet', 'veuve clicquot', 'dom perignon', 'krug', 'bollinger',
        'pol roger', 'taittinger', 'perrier jouet', 'mumm', 'piper heidsieck', 'lanson'
    ]
    
    # IŠIMTYS - šie raktažodžiai NEREIŠKIA putojančio vyno
    sparkling_exceptions = [
        'blanc sec',  # sausas baltas vynas
        'rouge sec',  # sausas raudonas vynas
        'bergerac',   # Bergerac regionas - ne putojantis vynas
        'mousserend', # olandiškai "putojantis", bet dažnai klaidingai naudojamas
    ]
    
    # Tikrinti ar yra išimčių
    has_exception = check_for_keyword(s_name, sparkling_exceptions)
    
    sparkling_found = check_for_keyword(s_name, sparkling_keywords)
    if sparkling_found and not has_exception:
        logging.info(f"Rastas putojančio vyno raktažodis: '{sparkling_found}'")
        logging.info(f"Priskirta kategorija 'sparkling_wine_... pagal ABV.")
        return 'sparkling_wine_over_8_5' if abv > 8.5 else 'sparkling_wine_up_to_8_5'
    elif sparkling_found and has_exception:
        logging.info(f"Rastas putojančio vyno raktažodis '{sparkling_found}', bet taip pat išimtis '{has_exception}' - laikoma paprastu vynu")

    # Taisyklė #6: Tarpiniai produktai - TIKTAI tikri tarpiniai produktai
    # PAŠALINTAS VERMOUTH iš tarpinių produktų - jis dabar etilo alkoholis
    intermediate_keywords = ['port', 'porto', 'portveinas', 'sherry', 'cheresas', 'xeres', 'jerez', 'marsala', 'madeira', 'ratafia', 'spirituotas vynas', 'fortified wine']
    intermediate_found = check_for_keyword(s_name, intermediate_keywords)
    if intermediate_found:
        logging.info(f"Rastas tarpinio produkto raktažodis: '{intermediate_found}'")
        if 15.0 < abv <= 22.0: 
            logging.info(f"Priskirta kategorija 'intermediate_15_22' pagal ABV.")
            return 'intermediate_15_22'
        if 1.2 < abv <= 15.0: 
            logging.info(f"Priskirta kategorija 'intermediate_up_to_15' pagal ABV.")
            return 'intermediate_up_to_15'
        if abv > 22.0:
            logging.info(f"Tarpinis produktas su aukštu ABV, priskiriama 'ethyl_alcohol'.")
            return 'ethyl_alcohol'

    # Taisyklė #7: Vynai - SPECIALUS APDOROJIMAS AUKŠTO ABV VYNAMS
    wine_keywords = [
        'wine', 'vynas', 'wein', 'vin', 'vino', 'rose', 'rosado', 'blanc', 'blanco', 'white', 'bianco', 
        'rouge', 'rosso', 'red', 'tinto', 'cuvee', 'aop', 'aoc', 'doc', 'sidras', 'cider', 'midus', 'mead', 'sake',
        # Italų vynų regionai ir tipai - SVARBIAUSIA DALIS
        'amarone', 'barolo', 'barbaresco', 'brunello', 'chianti', 'primitivo', 'sangiovese', 'nebbiolo',
        'montepulciano', 'barbera', 'dolcetto', 'valpolicella', 'soave', 'pinot grigio',
        # Prancūzų vynų regionai
        'bordeaux', 'burgundy', 'bourgogne', 'rhone', 'loire', 'alsace', 'languedoc', 'provence',
        'chablis', 'sancerre', 'pouilly', 'muscadet', 'cotes du rhone', 'chateauneuf', 'bergerac',
        # Ispanų vynų regionai
        'rioja', 'ribera del duero', 'priorat', 'rias baixas', 'rueda', 'jumilla', 'toro', 'acediano',
        # Vokiečių vynai
        'riesling', 'gewurztraminer', 'spatburgunder', 'dornfelder', 'muller thurgau',
        # Vynuogių rūšys
        'malbec', 'cabernet', 'merlot', 'syrah', 'shiraz', 'grenache', 'tempranillo', 'garnacha',
        'chardonnay', 'sauvignon', 'pinot noir', 'pinot blanc', 'viognier', 'chenin blanc'
    ]
    
    wine_found = check_for_keyword(s_name, wine_keywords)
    if wine_found:
        logging.info(f"Rastas vyno raktažodis: '{wine_found}'")
        
        # SPECIALŪS AUKŠTO ABV VYNAI - visada vynai, nepriklausomai nuo ABV
        high_abv_wine_keywords = [
            'amarone', 'primitivo', 'barolo', 'barbaresco', 'brunello', 'ripasso',
            'amarone della valpolicella', 'primitivo di manduria'
        ]
        
        high_abv_wine_found = check_for_keyword(s_name, high_abv_wine_keywords)
        if high_abv_wine_found:
            logging.info(f"Rastas aukšto ABV vyno raktažodis: '{high_abv_wine_found}' - priskiriama prie vynų nepriklausomai nuo ABV")
            logging.info(f"Priskirta kategorija 'wine_8.5_15'.")
            return 'wine_8.5_15'  # Visada vynas, net jei ABV > 15%
        
        # Įprastas vynų klasifikavimas pagal ABV
        if 8.5 < abv <= 15.0:
            logging.info(f"Priskirta kategorija 'wine_8.5_15' pagal ABV.")
            return 'wine_8.5_15'
        elif 1.2 < abv <= 8.5:
            logging.info(f"Priskirta kategorija 'wine_up_to_8.5' pagal ABV.")
            return 'wine_up_to_8.5'
        elif 15.0 < abv <= 22.0:
            # Jei ABV > 15% bet tai vynas, vis tiek priskiriame prie vynų
            logging.info(f"Priskirta kategorija 'wine_8.5_15' pagal ABV > 15, bet yra vynas.")
            return 'wine_8.5_15'
        elif abv > 22.0:
            logging.info(f"Priskirta kategorija 'ethyl_alcohol' pagal ABV > 22, bet yra vynas.")
            return 'ethyl_alcohol'
    
    # Taisyklė #8: Atsarginės taisyklės pagal ABV
    if abv > 22.0: 
        logging.info(f"Priskirta kategorija 'ethyl_alcohol' pagal ABV > 22.")
        return 'ethyl_alcohol'
    if 15.0 < abv <= 22.0: 
        logging.info(f"Priskirta kategorija 'intermediate_15_22' pagal ABV.")
        return 'intermediate_15_22'
    if 8.5 < abv <= 15.0: 
        logging.info(f"Priskirta kategorija 'wine_8.5_15' pagal ABV.")
        return 'wine_8.5_15'
    if 1.2 < abv <= 8.5: 
        logging.info(f"Priskirta kategorija 'wine_up_to_8.5' pagal ABV.")
        return 'wine_up_to_8.5'
    
    logging.warning(f"Galutinai nepavyko priskirti kategorijos: '{name}'. Grąžinama 'non_alcohol'.")
    return 'non_alcohol'