"""
Unit testai simple_cache.py funkcijoms.
"""
import unittest
import tempfile
import shutil
import os
import time
from simple_cache import SimpleFileCache


class TestSimpleFileCache(unittest.TestCase):
    """Testai SimpleFileCache klasei."""
    
    def setUp(self):
        """Sukuria laikinį cache katalogą testams."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = SimpleFileCache(cache_dir=self.temp_dir, max_age_hours=1)
        
        # Sukuriame test failą
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("test content")
    
    def tearDown(self):
        """Išvalo laikinį katalogą."""
        shutil.rmtree(self.temp_dir)
    
    def test_cache_set_and_get(self):
        """Testuoja cache set ir get operacijas."""
        test_data = {"products": [{"name": "Test", "price": 10.0}]}
        
        # Išsaugome į cache
        self.cache.set(self.test_file, test_data)
        
        # Gauname iš cache
        cached_data = self.cache.get(self.test_file)
        
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data["products"][0]["name"], "Test")
        self.assertEqual(cached_data["products"][0]["price"], 10.0)
    
    def test_cache_miss(self):
        """Testuoja cache miss scenarijų."""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.txt")
        cached_data = self.cache.get(non_existent_file)
        self.assertIsNone(cached_data)
    
    def test_cache_expiry(self):
        """Testuoja cache galiojimo laiką."""
        # Sukuriame cache su labai trumpu galiojimo laiku
        short_cache = SimpleFileCache(cache_dir=self.temp_dir, max_age_hours=0.001)  # ~3.6 sekundės
        
        test_data = {"test": "data"}
        short_cache.set(self.test_file, test_data)
        
        # Iš karto turėtų veikti
        cached_data = short_cache.get(self.test_file)
        self.assertIsNotNone(cached_data)
        
        # Po trumpo laiko turėtų nebegalioti
        time.sleep(4)
        cached_data = short_cache.get(self.test_file)
        self.assertIsNone(cached_data)
    
    def test_cache_clear(self):
        """Testuoja cache išvalymą."""
        test_data = {"test": "data"}
        self.cache.set(self.test_file, test_data)
        
        # Patikrinti kad cache veikia
        cached_data = self.cache.get(self.test_file)
        self.assertIsNotNone(cached_data)
        
        # Išvalyti cache
        removed_count = self.cache.clear()
        self.assertGreaterEqual(removed_count, 1)
        
        # Patikrinti kad cache išvalytas
        cached_data = self.cache.get(self.test_file)
        self.assertIsNone(cached_data)
    
    def test_cache_stats(self):
        """Testuoja cache statistiką."""
        test_data = {"test": "data"}
        self.cache.set(self.test_file, test_data)
        
        stats = self.cache.get_stats()
        
        self.assertIn("cache_files_count", stats)
        self.assertIn("total_size_mb", stats)
        self.assertIn("cache_dir", stats)
        self.assertIn("max_age_hours", stats)
        
        self.assertGreaterEqual(stats["cache_files_count"], 1)
        self.assertGreaterEqual(stats["total_size_mb"], 0)


if __name__ == '__main__':
    unittest.main()