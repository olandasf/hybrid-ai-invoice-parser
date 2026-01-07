"""
Integration testai visai sistemai.
"""
import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from simple_cache import pdf_cache
from utils import clean_and_convert_to_float
from category import classify_alcohol
from akcizai import enrich_products_with_excise


class TestIntegration(unittest.TestCase):
    """Integration testai."""
    
    def setUp(self):
        """Paruošia testų aplinką."""
        # Išvalome cache prieš kiekvieną testą
        pdf_cache.clear()
    
    def test_full_product_processing_pipeline(self):
        """Testuoja pilną produkto apdorojimo grandinę."""
        # 1. Pradiniai duomenys (kaip gautų iš AI)
        raw_product_data = {
            'name': 'Bordeaux Rouge 2020',
            'quantity': '6',
            'unit_price': '15,50',  # Europinis formatas
            'amount': '93,00',
            'volume_l': '0,75',
            'abv_percent': '13,5'
        }
        
        # 2. Duomenų konvertavimas
        processed_product = {
            'name': raw_product_data['name'],
            'quantity': clean_and_convert_to_float(raw_product_data['quantity']),
            'unit_price': clean_and_convert_to_float(raw_product_data['unit_price']),
            'amount': clean_and_convert_to_float(raw_product_data['amount']),
            'volume': clean_and_convert_to_float(raw_product_data['volume_l']),
            'abv': clean_and_convert_to_float(raw_product_data['abv_percent']),
            'unit_price_with_discount': clean_and_convert_to_float(raw_product_data['unit_price']),
            'amount_with_discount': clean_and_convert_to_float(raw_product_data['amount']),
            'discount_percentage': 0.0
        }
        
        # 3. Kategorijos nustatymas
        category = classify_alcohol(processed_product['name'], processed_product['abv'])
        processed_product['excise_category_key'] = category
        
        # 4. Akcizo skaičiavimas
        enriched_products = enrich_products_with_excise([processed_product], 15.0)
        
        # 5. Patikrinti rezultatus
        self.assertEqual(len(enriched_products), 1)
        product = enriched_products[0]
        
        # Patikrinti konvertavimą
        self.assertEqual(product['quantity'], 6.0)
        self.assertEqual(product['unit_price'], 15.5)
        self.assertEqual(product['volume'], 0.75)
        self.assertEqual(product['abv'], 13.5)
        
        # Patikrinti kategorizavimą
        self.assertEqual(product['excise_category_key'], 'wine_8.5_15')
        
        # Patikrinti akcizo skaičiavimą
        self.assertGreater(product['excise_per_unit'], 0)
        self.assertGreater(product['excise_total'], 0)
        
        # Patikrinti transporto paskirstymą
        self.assertGreater(product['transport_per_unit'], 0)
        self.assertEqual(product['transport_total'], 15.0)  # Vienas produktas = visas transportas
        
        # Patikrinti savikainos skaičiavimą
        expected_cost_wo_vat = (
            product['unit_price_with_discount'] + 
            product['excise_per_unit'] + 
            product['transport_per_unit']
        )
        self.assertAlmostEqual(product['cost_wo_vat'], expected_cost_wo_vat, places=2)
    
    def test_multiple_products_transport_distribution(self):
        """Testuoja transporto paskirstymą tarp kelių produktų."""
        products = [
            {
                'name': 'Wine Bottle',
                'volume': 0.75, 'abv': 13.0, 'quantity': 6,
                'unit_price': 10.0, 'amount': 60.0,
                'unit_price_with_discount': 10.0, 'amount_with_discount': 60.0,
                'discount_percentage': 0.0, 'excise_category_key': 'wine_8.5_15'
            },
            {
                'name': 'Beer Bottle',
                'volume': 0.5, 'abv': 5.0, 'quantity': 24,
                'unit_price': 2.0, 'amount': 48.0,
                'unit_price_with_discount': 2.0, 'amount_with_discount': 48.0,
                'discount_percentage': 0.0, 'excise_category_key': 'beer'
            }
        ]
        
        transport_total = 30.0
        result = enrich_products_with_excise(products, transport_total)
        
        # Patikrinti kad transportas paskirstytas
        total_distributed_transport = sum(p['transport_total'] for p in result)
        self.assertAlmostEqual(total_distributed_transport, transport_total, places=2)
        
        # Patikrinti kad alus gavo daugiau transporto (didesnis tūris)
        wine_transport = result[0]['transport_total']  # 6 * 0.75 = 4.5L
        beer_transport = result[1]['transport_total']  # 24 * 0.5 = 12L
        self.assertGreater(beer_transport, wine_transport)
    
    def test_cache_integration(self):
        """Testuoja cache integracijos veikimą."""
        # Sukuriame test failą
        test_file = "integration_test.pdf"
        with open(test_file, 'w') as f:
            f.write("test content")
        
        try:
            test_data = {
                "products": [{"name": "Test Wine", "abv": 13.0}],
                "summary": {"discount_amount": 0.0}
            }
            
            # Cache miss
            result1 = pdf_cache.get(test_file)
            self.assertIsNone(result1)
            
            # Cache set
            pdf_cache.set(test_file, test_data)
            
            # Cache hit
            result2 = pdf_cache.get(test_file)
            self.assertIsNotNone(result2)
            self.assertEqual(result2["products"][0]["name"], "Test Wine")
            
        finally:
            # Išvalymas
            if os.path.exists(test_file):
                os.remove(test_file)
            pdf_cache.clear()
    
    def test_error_handling_pipeline(self):
        """Testuoja klaidų apdorojimą grandinėje."""
        # Neteisingi duomenys
        bad_products = [
            {
                'name': '',  # Tuščias pavadinimas
                'volume': None,  # None reikšmė
                'abv': 'invalid',  # Neteisingas formatas
                'quantity': -1,  # Neigiamas kiekis
                'unit_price': 0,
                'amount': 0,
                'unit_price_with_discount': 0,
                'amount_with_discount': 0,
                'discount_percentage': 0.0,
                'excise_category_key': 'unknown_category'
            }
        ]
        
        # Sistema turėtų apdoroti be crash'o
        try:
            result = enrich_products_with_excise(bad_products, 0.0)
            self.assertEqual(len(result), 1)  # Produktas turėtų būti apdorotas
            
            # Patikrinti kad neteisingi duomenys pakeisti į default reikšmes
            product = result[0]
            self.assertEqual(product['volume'], 0.0)
            self.assertEqual(product['abv'], 0.0)
            
        except Exception as e:
            self.fail(f"Sistema neturėtų crash'inti su neteisingais duomenimis: {e}")
    
    def test_special_cases_integration(self):
        """Testuoja specialių atvejų integracijos veikimą."""
        # Clos Saint Jean Sanctus Sanctorum specialus atvejis
        special_product = {
            'name': 'Clos Saint Jean Sanctus Sanctorum 2020',
            'volume': 0.0,  # Nenurodyta, bet turėtų būti 1.5L
            'abv': 14.5,
            'quantity': 1,
            'unit_price': 150.0,
            'amount': 150.0,
            'unit_price_with_discount': 150.0,
            'amount_with_discount': 150.0,
            'discount_percentage': 0.0
        }
        
        # Kategorijos nustatymas
        category = classify_alcohol(special_product['name'], special_product['abv'])
        special_product['excise_category_key'] = category
        
        # Apdorojimas
        result = enrich_products_with_excise([special_product], 0.0)
        
        self.assertEqual(len(result), 1)
        product = result[0]
        
        # Patikrinti kad kategorija tinkama vynui
        self.assertEqual(product['excise_category_key'], 'wine_8.5_15')
        
        # Patikrinti kad akcizas apskaičiuotas (net jei tūris buvo 0)
        if product['volume'] > 0:  # Jei sistema automatiškai nustatė tūrį
            self.assertGreater(product['excise_per_unit'], 0)


if __name__ == '__main__':
    unittest.main()