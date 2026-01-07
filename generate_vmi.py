"""
VMI banderolių apskaitos failų generatorius.

Šis modulis generuoja CSV failus VMI sistemai pagal lietuvių mokesčių 
inspekcijos reikalavimus banderolių apskaitai.
"""

import csv
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from banderoles import VMI_CONSTANTS


class VMIGenerator:
    """VMI failų generavimo klasė."""
    
    # VMI CSV stulpelių pavadinimai
    VMI_HEADERS = [
        'Įrašo numeris',
        'Banderolės rūšies kodas', 
        'Atskaitinis laikotarpis nuo',
        'Atskaitinis laikotarpis iki',
        'Gaminio pavadinimas',
        'Tarifinės grupės kodas',
        'Alkoholio koncentracija',
        'Įpilstymas',
        'Ar klijuota akciziniame sandėlyje',
        'SEED arba klijavimo adresas',
        'Serija',
        'Numeris nuo',
        'Numeris iki', 
        'Užklijuota, vnt.',
        'Sugadinta, vnt.',
        'Prarasta, vnt.',
        'Sunaikinta užsienyje, vnt.',
        'Panaudotas kiekis, vnt.',
        'Įrašo pateikimo data',
        'Įrašo modifikavimo data'
    ]
    
    def __init__(self):
        """Inicializuoja VMI generatorių."""
        self.record_counter = 1
        self.bac_record_counter = 1
        self.aah_record_counter = 1
        
    def generate_vmi_files(self, 
                          products: List[Dict], 
                          period_start: date,
                          period_end: date,
                          output_dir: str = 'output') -> Tuple[str, str]:
        """
        Generuoja VMI failus produktų sąrašui.
        
        Args:
            products: Produktų sąrašas su banderolių informacija
            period_start: Atskaitinio laikotarpio pradžia
            period_end: Atskaitinio laikotarpio pabaiga
            output_dir: Išvesties katalogo kelias
            
        Returns:
            (bac_file_path, aah_file_path) - sugeneruotų failų keliai
        """
        # Sukurti išvesties katalogą
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Suskirstyti produktus pagal banderolių tipą
        bac_products = [p for p in products if p.get('banderole_type') == 'BAC']
        aah_products = [p for p in products if p.get('banderole_type') == 'AAH']
        
        # Generuoti failus
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        bac_file = None
        aah_file = None
        
        if bac_products:
            bac_file = output_path / f'VMI_BAC_{timestamp}.csv'
            self._generate_csv_file(bac_products, period_start, period_end, bac_file, 'BAC')
            logging.info(f"Sugeneruotas BAC failas: {bac_file}")
        
        if aah_products:
            aah_file = output_path / f'VMI_AAH_{timestamp}.csv'
            self._generate_csv_file(aah_products, period_start, period_end, aah_file, 'AAH')
            logging.info(f"Sugeneruotas AAH failas: {aah_file}")
        
        return str(bac_file) if bac_file else None, str(aah_file) if aah_file else None
    
    def _generate_csv_file(self, 
                          products: List[Dict],
                          period_start: date,
                          period_end: date, 
                          file_path: Path,
                          banderole_type: str) -> None:
        """
        Generuoja vieną VMI CSV failą.
        
        Args:
            products: Produktų sąrašas
            period_start: Laikotarpio pradžia
            period_end: Laikotarpio pabaiga
            file_path: Failo kelias
            banderole_type: 'BAC' arba 'AAH'
        """
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:  # UTF-8 su BOM
                writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_ALL)
                
                # Rašyti antraštę
                writer.writerow(self.VMI_HEADERS)
                
                # Rašyti produktų duomenis
                for product in products:
                    row = self._create_vmi_row(product, period_start, period_end, banderole_type)
                    writer.writerow(row)
                    
        except Exception as e:
            logging.error(f"Klaida generuojant VMI failą {file_path}: {e}")
            raise
    
    def _append_to_csv_file(self, 
                           products: List[Dict],
                           period_start: date,
                           period_end: date, 
                           file_path: Path,
                           banderole_type: str) -> None:
        """
        Prideda duomenis į esamą VMI CSV failą arba sukuria naują.
        
        Args:
            products: Produktų sąrašas
            period_start: Laikotarpio pradžia
            period_end: Laikotarpio pabaiga
            file_path: Failo kelias
            banderole_type: 'BAC' arba 'AAH'
        """
        try:
            # Patikrinti ar failas egzistuoja ir gauti paskutinius numerius
            file_exists = file_path.exists()
            logging.info(f"VMI failas egzistuoja: {file_exists}, kelias: {file_path}")
            
            if file_exists:
                try:
                    last_record_num, last_banderole_num = get_last_record_numbers(file_path)
                    logging.info(f"Esamo failo paskutiniai numeriai: įrašas={last_record_num}, banderolė={last_banderole_num}")
                    
                    # Nustatyti skaitiklius
                    if banderole_type == 'BAC':
                        self.bac_record_counter = last_record_num + 1 if last_record_num > 0 else self.bac_record_counter
                    else:
                        self.aah_record_counter = last_record_num + 1 if last_record_num > 0 else self.aah_record_counter
                    
                    # Atnaujinti banderolių skaitiklį banderoles.py
                    if last_banderole_num > 0:
                        self._update_banderole_counter(banderole_type, last_banderole_num)
                except Exception as e:
                    logging.warning(f"Nepavyko gauti paskutinių numerių iš failo {file_path}: {e}")
                    # Naudoti esamus skaitiklius
            
            # Jei failas egzistuoja, įterpti naujus įrašus viršuje
            if file_exists:
                self._insert_rows_at_top(file_path, products, period_start, period_end, banderole_type)
            else:
                # Naujas failas - rašyti normaliai
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_ALL)
                    writer.writerow(self.VMI_HEADERS)
                    
                    for product in products:
                        row = self._create_vmi_row(product, period_start, period_end, banderole_type)
                        writer.writerow(row)
                    
                logging.info(f"Sukurtas naujas VMI failas: {file_path}")
                    
        except Exception as e:
            logging.error(f"Klaida pridedant duomenis į VMI failą {file_path}: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _insert_rows_at_top(self, file_path: Path, products: List[Dict], 
                           period_start: date, period_end: date, banderole_type: str):
        """Įterpia naujus įrašus į failo viršų po antraštės."""
        try:
            # Perskaityti esamą failą su encoding aptikimu
            lines = []
            encodings = ['utf-8-sig', 'utf-8', 'cp1257', 'windows-1257']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            
            if not lines:
                raise ValueError("Nepavyko perskaityti failo su jokiu encoding")
            
            # Sukurti naujus įrašus
            new_rows = []
            for product in products:
                row = self._create_vmi_row(product, period_start, period_end, banderole_type)
                # Konvertuoti visas reikšmes į string ir pridėti kabutes, kad atitiktų VMI formatą
                row_str = [f'"{str(item).replace('"', '""')}"' for item in row]
                new_rows.append(';'.join(row_str) + '\r\n')
            
            # Apversti naujų įrašų tvarką, kad didžiausias numeris būtų viršuje
            new_rows.reverse()
            
            # Įterpti naujus įrašus po antraštės
            if len(lines) > 0:
                # Antraštė + nauji įrašai (atvirkštine tvarka) + seni įrašai
                updated_lines = [lines[0]] + new_rows + lines[1:]
            else:
                # Jei failas tuščias, pridėti antraštę
                header_line = ';'.join([f'"{h}"' for h in self.VMI_HEADERS]) + '\r\n'
                updated_lines = [header_line] + new_rows
            
            # Perrašyti failą
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                f.writelines(updated_lines)
                
            logging.info(f"Įterpti {len(new_rows)} nauji įrašai į failo viršų: {file_path}")
            
        except Exception as e:
            logging.error(f"Klaida įterpiant įrašus į failo viršų: {e}")
            raise

    def _update_banderole_counter(self, banderole_type: str, last_number: int):
        """Atnaujina banderolių skaitiklį banderoles.py faile."""
        try:
            from banderoles import BanderoleManager
            manager = BanderoleManager()
            
            # Atnaujinti tik jei esamas numeris mažesnis
            current_number = manager.state[banderole_type]['current_number']
            if last_number > current_number:
                manager.reset_numbers(banderole_type, last_number)
                logging.info(f"Atnaujintas {banderole_type} skaitiklis į {last_number}")
                
        except Exception as e:
            logging.warning(f"Nepavyko atnaujinti banderolių skaitiklio: {e}")
    
    def _create_vmi_row(self, 
                       product: Dict,
                       period_start: date,
                       period_end: date,
                       banderole_type: str) -> List[str]:
        """
        Sukuria VMI eilutę produktui.
        
        Args:
            product: Produkto duomenys
            period_start: Laikotarpio pradžia
            period_end: Laikotarpio pabaiga
            banderole_type: 'BAC' arba 'AAH'
            
        Returns:
            VMI eilutės duomenys
        """
        # Generuoti įrašo numerį pagal banderolės tipą
        if banderole_type == 'BAC':
            record_number = f"BP25000193_{self.bac_record_counter}"
            self.bac_record_counter += 1
        else:
            record_number = f"BP25000192_{self.aah_record_counter}"
            self.aah_record_counter += 1
        
        # Formatuoti datas
        date_from = period_start.strftime('%Y-%m-%d')
        date_to = period_end.strftime('%Y-%m-%d')
        submission_date = datetime.now().strftime('%Y-%m-%d')
        
        # Gauti produkto duomenis
        name = product.get('name', '')
        tariff_group = int(float(product.get('tariff_group', 280)))
        abv_raw = float(product.get('abv', 0))
        volume_raw = float(product.get('volume', 0))
        banderole_code = product.get('banderole_code', '101A')
        banderole_start = int(float(product.get('banderole_start', 0)))
        banderole_end = int(float(product.get('banderole_end', 0)))
        quantity = int(float(product.get('banderole_count', 0)))
        
        # Formatuoti skaičius su kableliu (Europos standartas)
        abv = str(abv_raw).replace('.', ',')
        volume = str(volume_raw).replace('.', ',')
        
        # Sukurti eilutę
        row = [
            record_number,                              # Įrašo numeris
            banderole_code,                            # Banderolės rūšies kodas
            date_from,                                 # Atskaitinis laikotarpis nuo
            date_to,                                   # Atskaitinis laikotarpis iki
            name,                                      # Gaminio pavadinimas
            tariff_group,                              # Tarifinės grupės kodas
            abv,                                       # Alkoholio koncentracija
            volume,                                    # Įpilstymas
            VMI_CONSTANTS['warehouse_flag'],           # Ar klijuota akciziniame sandėlyje
            VMI_CONSTANTS['seed_address'],             # SEED arba klijavimo adresas
            banderole_type,                            # Serija
            banderole_start,                           # Numeris nuo
            banderole_end,                             # Numeris iki
            quantity,                                  # Užklijuota, vnt.
            VMI_CONSTANTS['default_values']['sugadinta'],           # Sugadinta, vnt.
            VMI_CONSTANTS['default_values']['prarasta'],            # Prarasta, vnt.
            VMI_CONSTANTS['default_values']['sunaikinta_uzsienyje'], # Sunaikinta užsienyje, vnt.
            quantity,                                  # Panaudotas kiekis, vnt.
            submission_date,                           # Įrašo pateikimo data
            ''                                         # Įrašo modifikavimo data (tuščia)
        ]
        
        return row
    
    def validate_products(self, products: List[Dict]) -> List[str]:
        """
        Validuoja produktų duomenis VMI reikalavimams.
        
        Args:
            products: Produktų sąrašas
            
        Returns:
            Klaidų sąrašas (tuščias jei viskas gerai)
        """
        errors = []
        
        for i, product in enumerate(products):
            product_name = product.get('name', f'Produktas #{i+1}')
            
            # Tikrinti privalomas reikšmes
            required_fields = [
                'name', 'banderole_type', 'banderole_code',
                'banderole_start', 'banderole_end', 'banderole_count',
                'tariff_group', 'abv', 'volume'
            ]
            
            for field in required_fields:
                if field not in product or product[field] is None:
                    errors.append(f"{product_name}: trūksta lauko '{field}'")
            
            # Tikrinti numerių logiką
            start = int(float(product.get('banderole_start', 0)))
            end = int(float(product.get('banderole_end', 0)))
            count = int(float(product.get('banderole_count', 0)))
            
            if start > 0 and end > 0:
                if end < start:
                    errors.append(f"{product_name}: galutinis numeris ({end}) mažesnis už pradinį ({start})")
                
                expected_count = end - start + 1
                if count != expected_count:
                    errors.append(f"{product_name}: kiekis ({count}) neatitinka numerių intervalo ({expected_count})")
            
            # Tikrinti ABV
            abv = product.get('abv', 0)
            if abv < 0 or abv > 100:
                errors.append(f"{product_name}: neteisingas ABV ({abv}%)")
            
            # Tikrinti tūrį (tik akcizinėms prekėms)
            excise_category = product.get('excise_category_key', 'non_alcohol')
            if excise_category != 'non_alcohol':
                volume = product.get('volume', 0)
                if volume <= 0:
                    errors.append(f"{product_name}: neteisingas tūris ({volume}L) akcizinei prekei")
        
        return errors


def get_last_record_numbers(file_path: Path) -> Tuple[int, int]:
    """
    Gauna paskutinius įrašo ir banderolės numerius iš esamo failo, naudojant patikimą CSV skaitytuvą.
    
    Returns:
        (last_record_number, last_banderole_number)
    """
    if not file_path.exists():
        return 0, 0

    max_record_num = 0
    max_banderole_num = 0
    
    # Bandome kelias populiariausias koduotes
    encodings = ['utf-8-sig', 'utf-8', 'windows-1257', 'cp1257']
    
    for encoding in encodings:
        try:
            with file_path.open('r', newline='', encoding=encoding) as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                
                # Praleisti antraštę
                try:
                    header = next(reader)
                except StopIteration:
                    # Failas tuščias
                    return 0, 0

                # Iteruoti per eilutes ir rasti maksimalias reikšmes
                for row in reader:
                    if not row or len(row) < 13:
                        continue

                    # 1. Ieškoti maksimalaus įrašo numerio
                    record_num_str = row[0]
                    if '_' in record_num_str:
                        try:
                            num_part = int(record_num_str.split('_')[1])
                            if num_part > max_record_num:
                                max_record_num = num_part
                        except (ValueError, IndexError):
                            logging.warning(f"Nepavyko apdoroti įrašo numerio: '{record_num_str}' faile {file_path}")
                            pass

                    # 2. Ieškoti maksimalaus banderolės numerio ("Numeris iki")
                    banderole_num_str = row[12]
                    try:
                        num_part = int(banderole_num_str.strip())
                        if num_part > max_banderole_num:
                            max_banderole_num = num_part
                    except (ValueError, IndexError):
                        # Ignoruojame, jei stulpelis tuščias ar netinkamo formato
                        pass
            
            # Jei nuskaitymas pavyko, išeiname iš ciklo
            logging.info(f"Failas {file_path} sėkmingai nuskaitytas su {encoding} koduote.")
            logging.info(f"Rasti didžiausi numeriai: Įrašas={max_record_num}, Banderolė={max_banderole_num}")
            return max_record_num, max_banderole_num

        except UnicodeDecodeError:
            # Tęsiame su kita koduote
            continue
        except Exception as e:
            logging.error(f"Kritinė klaida skaitant {file_path} su {encoding}: {e}")
            # Jei įvyko kita klaida, geriau sustoti
            return 0, 0
            
    logging.error(f"Nepavyko perskaityti failo {file_path} su jokia iš bandytų koduocių.")
    return 0, 0


def append_to_existing_vmi_files(products: List[Dict], 
                               period_start: date,
                               period_end: date,
                               banderoles_dir: str = 'Banderolių apskaita') -> Tuple[bool, bool]:
    """
    Prideda duomenis į esamus VMI failus arba sukuria naujus.
    
    Args:
        products: Produktų sąrašas su banderolių informacija
        period_start: Atskaitinio laikotarpio pradžia
        period_end: Atskaitinio laikotarpio pabaiga
        banderoles_dir: Banderolių apskaitos katalogo kelias
        
    Returns:
        (bac_success, aah_success) - boolean reikšmės
        bac_success: True jei BAC failas atnaujintas sėkmingai, False jei ne, None jei klaida
        aah_success: True jei AAH failas atnaujintas sėkmingai, False jei ne, None jei klaida
    """
    try:
        generator = VMIGenerator()
        
        # Debug: produktų informacija
        logging.info(f"VMI duomenų pridėjimas: {len(products)} produktų")
        if not products:
            logging.warning("PRODUKTŲ SĄRAŠAS TUŠČIAS!")
            # Grąžiname True, True nes nėra ką atnaujinti - tai nėra klaida
            return True, True
            
        # Validuoti duomenis
        errors = generator.validate_products(products)
        if errors:
            logging.error("VMI duomenų validacijos klaidos:")
            for error in errors:
                logging.error(f"  - {error}")
            # Grąžiname False, False nes yra validacijos klaidų
            return False, False
        else:
            logging.info("VMI duomenų validacija praėjo sėkmingai")
        
        # Sukurti banderolių katalogą jei neegzistuoja
        banderoles_path = Path(banderoles_dir)
        banderoles_path.mkdir(exist_ok=True)
        
        # Filtruoti tik alkoholinius produktus, turinčius banderolių informaciją
        alkoholiniai_produktai = [p for p in products if p.get('banderole_type') in ['BAC', 'AAH']]
        
        # Filtruoti testinius įrašus (produktais, kurių pavadinime yra 'Test' arba 'test')
        alkoholiniai_produktai = [p for p in alkoholiniai_produktai if 'test' not in p.get('name', '').lower()]
        
        # Suskirstyti produktus pagal banderolių tipą
        bac_products = [p for p in alkoholiniai_produktai if p.get('banderole_type') == 'BAC']
        aah_products = [p for p in alkoholiniai_produktai if p.get('banderole_type') == 'AAH']
        
        bac_success = None  # Default to None (no operation)
        aah_success = None  # Default to None (no operation)
        
        # Naudoti esamus BAC.csv ir AAH.csv failus
        # Svarbu: apdoroti abu failus nepriklausomai vienas nuo kito
        bac_file = banderoles_path / 'BAC.csv'
        aah_file = banderoles_path / 'AAH.csv'
        
        # Apdoroti BAC failą
        if bac_products:
            try:
                generator._append_to_csv_file(bac_products, period_start, period_end, bac_file, 'BAC')
                logging.info(f"Duomenys pridėti į BAC failą: {bac_file}")
                bac_success = True
            except Exception as e:
                logging.error(f"Nepavyko pridėti duomenų į BAC failą: {e}")
                bac_success = False  # Grąžiname False, nes įvyko klaida
        else:
            # Jei nėra BAC produktų, tai nėra klaida
            bac_success = True
            
        # Apdoroti AAH failą
        if aah_products:
            try:
                generator._append_to_csv_file(aah_products, period_start, period_end, aah_file, 'AAH')
                logging.info(f"Duomenys pridėti į AAH failą: {aah_file}")
                aah_success = True
            except Exception as e:
                logging.error(f"Nepavyko pridėti duomenų į AAH failą: {e}")
                aah_success = False  # Grąžiname False, nes įvyko klaida
        else:
            # Jei nėra AAH produktų, tai nėra klaida
            aah_success = True
        
        # Jei nebuvo jokių alkoholinių produktų, grąžiname True, True nes tai nėra klaida
        if not alkoholiniai_produktai:
            logging.info("Nebuvo alkoholinių produktų su banderolėmis, VMI failai neatnaujinti - tai nėra klaida")
            return True, True
        
        logging.info(f"VMI funkcija grąžina: BAC={bac_success}, AAH={aah_success}")
        return bac_success, aah_success
        
    except Exception as e:
        logging.error(f"Klaida pridedant duomenis į VMI failus: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        # Grąžiname None, None tik tada kai įvyksta kritinė klaida
        return None, None


def generate_vmi_files_for_products(products: List[Dict], 
                                   period_start: date,
                                   period_end: date,
                                   output_dir: str = 'output') -> Tuple[Optional[str], Optional[str]]:
    """
    Pagrindinė funkcija VMI failų generavimui.
    
    Args:
        products: Produktų sąrašas su banderolių informacija
        period_start: Atskaitinio laikotarpio pradžia
        period_end: Atskaitinio laikotarpio pabaiga
        output_dir: Išvesties katalogo kelias
        
    Returns:
        (bac_file_path, aah_file_path) arba (None, None) jei klaida
    """
    try:
        generator = VMIGenerator()
        
        # Debug: produktų informacija
        logging.info(f"VMI generavimas: {len(products)} produktų")
        if not products:
            logging.error("PRODUKTŲ SĄRAŠAS TUŠČIAS!")
            return None, None
            
        for i, product in enumerate(products[:2]):
            logging.info(f"Produktas {i}: {product.get('name', 'N/A')} - banderolės: {product.get('banderole_type', 'N/A')}")
            logging.info(f"  Raktai: {list(product.keys())}")
        
        # Validuoti duomenis
        errors = generator.validate_products(products)
        if errors:
            logging.error("VMI duomenų validacijos klaidos:")
            for error in errors:
                logging.error(f"  - {error}")
            return None, None
        else:
            logging.info("VMI duomenų validacija praėjo sėkmingai")
        
        # Generuoti failus
        return generator.generate_vmi_files(products, period_start, period_end, output_dir)
        
    except Exception as e:
        logging.error(f"Klaida generuojant VMI failus: {e}")
        return None, None


def create_sample_vmi_files() -> None:
    """Sukuria pavyzdinius VMI failus testavimui."""
    from banderoles import enrich_products_with_banderoles
    
    # Testiniai produktai
    test_products = [
        {
            'name': 'Champagne Brut Premium',
            'quantity': 12,
            'volume': 0.75,
            'abv': 12.5,
            'excise_category_key': 'sparkling_wine'
        },
        {
            'name': 'Bordeaux Rouge AOC',
            'quantity': 6,
            'volume': 0.75,
            'abv': 13.5,
            'excise_category_key': 'wine'
        },
        {
            'name': 'Premium Vodka',
            'quantity': 24,
            'volume': 0.7,
            'abv': 40.0,
            'excise_category_key': 'spirits'
        }
    ]
    
    # Priskirti banderoles
    enriched_products = enrich_products_with_banderoles(test_products)
    
    # Generuoti VMI failus
    period_start = date(2025, 1, 9)
    period_end = date(2025, 1, 10)
    
    bac_file, aah_file = generate_vmi_files_for_products(
        enriched_products, period_start, period_end
    )
    
    print("Sugeneruoti pavyzdiniai VMI failai:")
    if bac_file:
        print(f"  BAC: {bac_file}")
    if aah_file:
        print(f"  AAH: {aah_file}")


if __name__ == "__main__":
    # Testavimo kodas
    logging.basicConfig(level=logging.INFO)
    create_sample_vmi_files()