"""
Unit testai akcizai.py funkcijoms.
"""
import unittest
from akcizai import safe_float, enrich_products_with_excise, TARIFAI


class TestAkcizai(unittest.TestCase):
    """Testai akcizai.py funkcijoms."""
    
    def test_safe_float(self):
        """Testuoja safe_float funkciją."""
        # Patikriname kaip veikia akcizai.py safe_float funkcija
        test_cases = [
            ("123.45", 0.0, 123.45),
            ("123,45", 0.0, 123.45),  # Europinis formatas
            (None, 10.0, 10.0),
            ("", 5.0, 5.0),
            ("abc", 0.0, 0.0),
            (123, 0.0, 123.0),
            (123.45, 0.0, 123.45)
        ]
        
        for value, default, expected in test_cases:
            with self.subTest(value=value, default=default):
                result = safe_float(value, default)
                self.assertEqual(result, expected)
    
    def test_enrich_products_with_excise_beer(self):
        """Testuoja alaus akcizo skaičiavimą."""
        products = [{
            'name': 'Test Beer',
            'volume': 0.5,  # 0.5L
            'abv': 5.0,     # 5%
            'quantity': 12,  # 12 butelių
            'unit_price': 2.0,
            'amount': 24.0,
            'unit_price_with_discount': 2.0,
            'amount_with_discount': 24.0,
            'discount_percentage': 0.0,
            'excise_category_key': 'beer'
        }]
        
        result = enrich_products_with_excise(products, 0.0)
        
        self.assertEqual(len(result), 1)
        product = result[0]
        
        # Alaus akcizas: (0.5L / 100) * 5% * 10.97 EUR = 0.02485 EUR už butelį
        expected_excise_per_unit = (0.5 / 100.0) * 5.0 * TARIFAI['beer']
        self.assertAlmostEqual(product['excise_per_unit'], expected_excise_per_unit, places=4)
        
        # Bendras akcizas: 0.02485 * 12 = 0.2982 EUR
        expected_excise_total = expected_excise_per_unit * 12
        self.assertAlmostEqual(product['excise_total'], expected_excise_total, places=4)
    
    def test_enrich_products_with_excise_wine(self):
        """Testuoja vyno akcizo skaičiavimą."""
        products = [{
            'name': 'Test Wine',
            'volume': 0.75,  # 0.75L
            'abv': 13.0,     # 13%
            'quantity': 6,   # 6 buteliai
            'unit_price': 15.0,
            'amount': 90.0,
            'unit_price_with_discount': 15.0,
            'amount_with_discount': 90.0,
            'discount_percentage': 0.0,
            'excise_category_key': 'wine_8.5_15'
        }]
        
        result = enrich_products_with_excise(products, 0.0)
        
        self.assertEqual(len(result), 1)
        product = result[0]
        
        # Vyno akcizas: (0.75L / 100) * 254 EUR = 1.905 EUR už butelį
        expected_excise_per_unit = (0.75 / 100.0) * TARIFAI['wine_8.5_15']
        self.assertAlmostEqual(product['excise_per_unit'], expected_excise_per_unit, places=3)
        
        # Bendras akcizas: 1.905 * 6 = 11.43 EUR
        expected_excise_total = expected_excise_per_unit * 6
        self.assertAlmostEqual(product['excise_total'], expected_excise_total, places=2)
    
    def test_enrich_products_with_excise_spirits(self):
        """Testuoja stipriųjų gėrimų akcizo skaičiavimą."""
        products = [{
            'name': 'Test Vodka',
            'volume': 0.7,   # 0.7L
            'abv': 40.0,     # 40%
            'quantity': 1,   # 1 butelis
            'unit_price': 25.0,
            'amount': 25.0,
            'unit_price_with_discount': 25.0,
            'amount_with_discount': 25.0,
            'discount_percentage': 0.0,
            'excise_category_key': 'ethyl_alcohol'
        }]
        
        result = enrich_products_with_excise(products, 0.0)
        
        self.assertEqual(len(result), 1)
        product = result[0]
        
        # Etilo alkoholio akcizas: (0.7L / 100) * (40% / 100) * 2778 EUR = 7.7784 EUR
        expected_excise_per_unit = (0.7 / 100.0) * (40.0 / 100.0) * TARIFAI['ethyl_alcohol']
        self.assertAlmostEqual(product['excise_per_unit'], expected_excise_per_unit, places=4)
    
    def test_enrich_products_with_excise_transport(self):
        """Testuoja transporto paskirstymą."""
        products = [
            {
                'name': 'Product 1',
                'volume': 0.75,
                'abv': 13.0,
                'quantity': 6,  # 6 * 0.75 = 4.5L
                'unit_price': 10.0,
                'amount': 60.0,
                'unit_price_with_discount': 10.0,
                'amount_with_discount': 60.0,
                'discount_percentage': 0.0,
                'excise_category_key': 'wine_8.5_15'
            },
            {
                'name': 'Product 2',
                'volume': 0.5,
                'abv': 5.0,
                'quantity': 12,  # 12 * 0.5 = 6.0L
                'unit_price': 2.0,
                'amount': 24.0,
                'unit_price_with_discount': 2.0,
                'amount_with_discount': 24.0,
                'discount_percentage': 0.0,
                'excise_category_key': 'beer'
            }
        ]
        
        transport_total = 21.0  # 21 EUR transportas
        result = enrich_products_with_excise(products, transport_total)
        
        self.assertEqual(len(result), 2)
        
        # Bendras tūris: 4.5L + 6.0L = 10.5L
        # Product 1 dalis: 4.5/10.5 = 0.4286 (42.86%)
        # Product 2 dalis: 6.0/10.5 = 0.5714 (57.14%)
        
        product1_transport = result[0]['transport_total']
        product2_transport = result[1]['transport_total']
        
        # Patikrinti ar transportas paskirstytas proporcingai
        self.assertAlmostEqual(product1_transport + product2_transport, transport_total, places=2)
        self.assertGreater(product2_transport, product1_transport)  # Product 2 turi didesnį tūrį
    
    def test_enrich_products_with_excise_cost_calculation(self):
        """Testuoja savikainos skaičiavimą."""
        products = [{
            'name': 'Test Product',
            'volume': 0.75,
            'abv': 13.0,
            'quantity': 1,
            'unit_price': 10.0,
            'amount': 10.0,
            'unit_price_with_discount': 9.0,  # Su nuolaida
            'amount_with_discount': 9.0,
            'discount_percentage': 10.0,
            'excise_category_key': 'wine_8.5_15'
        }]
        
        result = enrich_products_with_excise(products, 5.0)  # 5 EUR transportas
        
        self.assertEqual(len(result), 1)
        product = result[0]
        
        # Savikaina be PVM = kaina su nuolaida + akcizas + transportas
        expected_cost_wo_vat = (
            product['unit_price_with_discount'] + 
            product['excise_per_unit'] + 
            product['transport_per_unit']
        )
        self.assertAlmostEqual(product['cost_wo_vat'], expected_cost_wo_vat, places=2)
        
        # Savikaina su PVM = savikaina be PVM * 1.21
        expected_cost_w_vat = expected_cost_wo_vat * 1.21
        self.assertAlmostEqual(product['cost_w_vat'], expected_cost_w_vat, places=2)
    
    def test_enrich_products_with_excise_empty_list(self):
        """Testuoja tuščio sąrašo apdorojimą."""
        result = enrich_products_with_excise([], 10.0)
        self.assertEqual(result, [])
    
    def test_enrich_products_with_excise_non_alcohol(self):
        """Testuoja nealkoholinių produktų apdorojimą."""
        products = [{
            'name': 'Non-alcoholic Beer',
            'volume': 0.5,
            'abv': 0.0,
            'quantity': 12,
            'unit_price': 1.0,
            'amount': 12.0,
            'unit_price_with_discount': 1.0,
            'amount_with_discount': 12.0,
            'discount_percentage': 0.0,
            'excise_category_key': 'non_alcohol'
        }]
        
        result = enrich_products_with_excise(products, 0.0)
        
        self.assertEqual(len(result), 1)
        product = result[0]
        
        # Nealkoholiniams produktams akcizas = 0
        self.assertEqual(product['excise_per_unit'], 0.0)
        self.assertEqual(product['excise_total'], 0.0)


if __name__ == '__main__':
    unittest.main()