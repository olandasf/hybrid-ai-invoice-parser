"""
Banderolių automatinio priskyrimo sistema.

Šis modulis valdo VMI banderolių priskyrimą alkoholio produktams.
Naudojama tik BAC serija visoms akcizinėms prekėms (AAH serija išnaudota).
"""

import os
import json
import logging
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from category import classify_alcohol

# Banderolių konfigūracija - TIK BAC serija (AAH išnaudota)
BANDEROLE_CONFIG = {
    'BAC': {
        'code': '102A',
        'current_number': 370000,  # Pradinis numeris, bus atnaujintas iš failo
        'batch_size': 10000,
        'categories': 'all',  # Visos akcizinės prekės
        'tariff_group': 235,
        'description': 'Visos akcizinės prekės'
    }
}

# VMI konstantos
VMI_CONSTANTS = {
    'seed_address': os.getenv('WAREHOUSE_ID', 'LT00000000000'),  # Configure in .env
    'warehouse_flag': 'TAIP',
    'default_values': {
        'sugadinta': 0,
        'prarasta': 0,
        'sunaikinta_uzsienyje': 0
    }
}

def get_last_banderole_numbers_from_vmi_files() -> Dict[str, int]:
    """
    Gauna paskutinius banderolių numerius iš esamų VMI failų.
    
    Returns:
        Dict su banderolių tipais ir jų paskutiniais numeriais
    """
    banderole_numbers = {'BAC': 0}
    
    try:
        banderoles_dir = Path('Banderolių apskaita')
        bac_file = banderoles_dir / 'BAC.csv'
        if bac_file.exists():
            banderole_numbers['BAC'] = _extract_last_banderole_number(bac_file, 'BAC')
                
        logging.info(f"Nustatyti paskutiniai numeriai iš VMI failų: {banderole_numbers}")
    except Exception as e:
        logging.error(f"Klaida skaitant banderolių numerius iš VMI failų: {e}")
    
    return banderole_numbers

def _extract_last_banderole_number(file_path: Path, banderole_type: str) -> int:
    """
    Ištraukia paskutinį banderolės numerį iš VMI failo.
    """
    try:
        encodings = ['utf-8-sig', 'utf-8', 'cp1257', 'windows-1257']
        last_number = 0
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, newline='') as f:
                    # Pirmiausia bandome nustatyti skirtuką
                    sample = f.read(1024)
                    f.seek(0)
                    delimiter = ';'
                    if sample and ',' in sample and ';' not in sample:
                        delimiter = ','
                    
                    reader = csv.reader(f, delimiter=delimiter)
                    lines = list(reader)
                    if len(lines) > 1:
                        for line in lines[1:]:
                            # Jei skirtukas kablelis, indeksas gali būti kitoks, bet VMI failai turi fiksuotą struktūrą
                            # Tikimės, kad 13-as stulpelis (indeksas 12) yra numeris "iki"
                            if len(line) >= 13:
                                try:
                                    banderole_num = int(line[12])
                                    if banderole_num > last_number:
                                        last_number = banderole_num
                                except (ValueError, IndexError):
                                    continue
                    
                    # Jei pavyko nuskaityti bent vieną eilutę, nutraukiame ciklą per koduotes
                    if len(lines) > 0:
                        break 
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logging.warning(f"Klaida skaitant {file_path} su {encoding}: {e}")
                continue
        
        logging.info(f"Iš failo {file_path} nuskaitytas paskutinis numeris: {last_number}")
        return last_number
    except Exception as e:
        logging.error(f"Klaida ištraukiant paskutinį banderolės numerį iš {file_path}: {e}")
        return 0

class BanderoleManager:
    """Banderolių valdymo klasė."""
    
    def __init__(self, config_file: str = 'banderoles_state.json'):
        self.config_file = Path(config_file)
        self.state = self._load_state()
        
    def _load_state(self) -> Dict:
        """
        Visada iš naujo sukuria būseną pagal CSV failus, kad išvengtų neatitikimų.
        """
        real_numbers = get_last_banderole_numbers_from_vmi_files()
        
        initial_state = {
            'BAC': {
                'current_number': real_numbers.get('BAC', 0),
                'last_updated': datetime.now().isoformat()
            }
        }
        
        self.state = initial_state
        initial_state['BAC']['batch_info'] = self._calculate_batch_info('BAC')

        self._save_state(initial_state)
        return initial_state

    def _save_state(self, state: Dict = None) -> None:
        if state is None:
            state = self.state
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Klaida saugant banderolių būseną: {e}")

    def _calculate_batch_info(self, banderole_type: str) -> Dict:
        config = BANDEROLE_CONFIG[banderole_type]
        if hasattr(self, 'state') and self.state:
            current = self.state.get(banderole_type, {}).get('current_number', 0)
        else:
            current = 0
        
        batch_start = (current // config['batch_size']) * config['batch_size'] + 1
        batch_end = batch_start + config['batch_size'] - 1
        remaining = batch_end - current
        
        return {
            'batch_start': batch_start,
            'batch_end': batch_end,
            'remaining': remaining,
            'batch_size': config['batch_size']
        }

    def get_banderole_type(self, product: Dict) -> str:
        """Visos akcizinės prekės naudoja BAC seriją."""
        return 'BAC'

    def get_tariff_group(self, banderole_type: str, category: str, abv: float) -> int:
        if category in ['sparkling_wine_over_8_5', 'sparkling_wine_up_to_8_5']:
            return 235
        if category == 'ethyl_alcohol':
            return 280
        if category == 'intermediate_15_22':
            return 250
        if category == 'intermediate_up_to_15':
            return 240
        if category == 'wine_8.5_15':
            return 230
        if category == 'wine_up_to_8.5':
            return 210
        if category == 'beer':
            return 280
        logging.warning(f"Nenustatytas tarifo kodas kategorijai: '{category}'. Naudojamas numatytasis 280.")
        return 280

    def assign_banderoles(self, products: List[Dict]) -> List[Dict]:
        enriched_products = []
        for product in products:
            enriched_product = product.copy()
            category = product.get('excise_category_key') or classify_alcohol(product.get('name', ''), product.get('abv', 0), product.get('volume', 0))
            
            if category == 'non_alcohol':
                enriched_products.append(enriched_product)
                continue
            
            quantity = int(product.get('quantity', 0))
            if quantity <= 0:
                enriched_products.append(enriched_product)
                continue

            banderole_type = self.get_banderole_type(product)
            
            # VISADA priskirti naujus numerius pagal faktinį paskutinį numerį CSV faile
            # Tai užtikrina, kad po testinių eilučių ištrynimo numeracija tęsiama teisingai
            start_number, end_number = self._allocate_numbers(banderole_type, quantity)
            logging.info(f"Priskirtos banderolės produktui '{product.get('name', '')[:30]}': {start_number}-{end_number} (kiekis: {quantity})")
            
            enriched_product.update({
                'banderole_type': banderole_type,
                'banderole_code': BANDEROLE_CONFIG[banderole_type]['code'],
                'banderole_start': start_number,
                'banderole_end': end_number,
                'banderole_count': quantity,
                'tariff_group': self.get_tariff_group(banderole_type, category, product.get('abv', 0))
            })
            enriched_products.append(enriched_product)
        return enriched_products

    def _allocate_numbers(self, banderole_type: str, quantity: int) -> Tuple[int, int]:
        current_number = self.state[banderole_type]['current_number']
        start_number = current_number + 1
        end_number = current_number + quantity
        self.state[banderole_type]['current_number'] = end_number
        self.state[banderole_type]['last_updated'] = datetime.now().isoformat()
        self.state[banderole_type]['batch_info'] = self._calculate_batch_info(banderole_type)
        self._save_state()
        return start_number, end_number

    def get_statistics(self) -> Dict:
        stats = {}
        state = self.state['BAC']
        batch_info = state['batch_info']
        stats['BAC'] = {
            'description': BANDEROLE_CONFIG['BAC']['description'],
            'current_number': state['current_number'],
            'batch_start': batch_info['batch_start'],
            'batch_end': batch_info['batch_end'],
            'used_in_batch': state['current_number'] - batch_info['batch_start'] + 1,
            'remaining_in_batch': batch_info['remaining'],
            'usage_percentage': round(((state['current_number'] - batch_info['batch_start'] + 1) / batch_info['batch_size']) * 100, 1),
            'last_updated': state['last_updated']
        }
        return stats

def enrich_products_with_banderoles(products: List[Dict]) -> List[Dict]:
    try:
        manager = BanderoleManager()
        return manager.assign_banderoles(products)
    except Exception as e:
        logging.error(f"Klaida priskiriant banderoles: {e}")
        return products

def get_banderole_statistics() -> Dict:
    try:
        manager = BanderoleManager()
        return manager.get_statistics()
    except Exception as e:
        logging.error(f"Klaida gaunant banderolių statistikas: {e}")
        return {}
