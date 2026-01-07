"""
Unit testai utils.py funkcijoms.
"""
import unittest
from utils import clean_and_convert_to_float, safe_float, format_currency, validate_positive_number


class TestUtils(unittest.TestCase):
    """Testai utils.py funkcijoms."""
    
    def test_clean_and_convert_to_float(self):
        """Testuoja clean_and_convert_to_float funkciją."""
        # Normalūs atvejai
        self.assertEqual(clean_and_convert_to_float("123.45"), 123.45)
        self.assertEqual(clean_and_convert_to_float("123,45"), 123.45)  # Europinis formatas
        self.assertEqual(clean_and_convert_to_float("1 234,56"), 1234.56)  # Su tarpais
        self.assertEqual(clean_and_convert_to_float(123), 123.0)
        self.assertEqual(clean_and_convert_to_float(123.45), 123.45)
        
        # Neigiami skaičiai
        self.assertEqual(clean_and_convert_to_float("-123.45"), -123.45)
        self.assertEqual(clean_and_convert_to_float("-123,45"), -123.45)
        
        # Kraštiniai atvejai
        self.assertIsNone(clean_and_convert_to_float(None))
        self.assertIsNone(clean_and_convert_to_float(""))
        self.assertIsNone(clean_and_convert_to_float("-"))
        self.assertIsNone(clean_and_convert_to_float("abc"))
        
        # Su valiutos simboliais
        self.assertEqual(clean_and_convert_to_float("€123.45"), 123.45)
        self.assertEqual(clean_and_convert_to_float("123.45 EUR"), 123.45)
    
    def test_safe_float(self):
        """Testuoja safe_float funkciją."""
        # Normalūs atvejai
        self.assertEqual(safe_float("123.45"), 123.45)
        self.assertEqual(safe_float("123,45"), 123.45)
        
        # Su default reikšme
        self.assertEqual(safe_float(None, 10.0), 10.0)
        self.assertEqual(safe_float("abc", 5.0), 5.0)
        self.assertEqual(safe_float("", 0.0), 0.0)
        
        # Be default reikšmės
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float("abc"), 0.0)
    
    def test_format_currency(self):
        """Testuoja format_currency funkciją."""
        self.assertEqual(format_currency(123.456), "123.46")
        self.assertEqual(format_currency(123.456, 3), "123.456")
        self.assertEqual(format_currency(123, 0), "123")
        self.assertEqual(format_currency(0), "0.00")
        self.assertEqual(format_currency(-123.45), "-123.45")
    
    def test_validate_positive_number(self):
        """Testuoja validate_positive_number funkciją."""
        # Teigiami skaičiai
        is_valid, msg = validate_positive_number(123.45)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")
        
        is_valid, msg = validate_positive_number(0)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")
        
        # Neigiami skaičiai
        is_valid, msg = validate_positive_number(-123.45)
        self.assertFalse(is_valid)
        self.assertEqual(msg, "Reikšmė negali būti neigiama")
        
        # Su maksimalia reikšme
        is_valid, msg = validate_positive_number(50, 100)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")
        
        is_valid, msg = validate_positive_number(150, 100)
        self.assertFalse(is_valid)
        self.assertEqual(msg, "Reikšmė negali viršyti 100")


if __name__ == '__main__':
    unittest.main()