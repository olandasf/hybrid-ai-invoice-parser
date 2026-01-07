"""
Unit testai category.py funkcijoms.
"""
import unittest
from category import classify_alcohol, simplify_text, check_for_keyword


class TestCategory(unittest.TestCase):
    """Testai category.py funkcijoms."""
    
    def test_simplify_text(self):
        """Testuoja simplify_text funkciją."""
        test_cases = [
            ("Château Margaux", "chateau margaux"),
            ("Müller-Thurgau", "muller-thurgau"),
            ("José Cuervo", "jose cuervo"),
            ("Žalgiris Alus", "zalgiris alus"),
            ("", ""),
            (None, "")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = simplify_text(input_text)
                self.assertEqual(result, expected)
    
    def test_check_for_keyword(self):
        """Testuoja check_for_keyword funkciją."""
        keywords = ["wine", "vynas", "beer", "alus"]
        
        # Teigiami testai
        positive_cases = [
            ("red wine bottle", "wine"),
            ("lietuviškas vynas", "vynas"),
            ("craft beer", "beer"),
            ("šviesus alus", "alus")
        ]
        
        for text, expected_keyword in positive_cases:
            with self.subTest(text=text):
                result = check_for_keyword(text, keywords)
                self.assertEqual(result, expected_keyword)
        
        # Neigiami testai
        negative_cases = [
            "vodka bottle",
            "whiskey glass",
            "champagne flute",
            ""
        ]
        
        for text in negative_cases:
            with self.subTest(text=text):
                result = check_for_keyword(text, keywords)
                self.assertIsNone(result)
    
    def test_classify_alcohol_beer(self):
        """Testuoja alaus klasifikavimą."""
        beer_cases = [
            ("Heineken Beer 5%", 5.0, "beer"),
            ("Švyturys Alus", 5.2, "beer"),
            ("Craft IPA", 6.5, "beer"),
            ("Guinness Stout", 4.2, "beer")
        ]
        
        for name, abv, expected in beer_cases:
            with self.subTest(name=name, abv=abv):
                result = classify_alcohol(name, abv)
                self.assertEqual(result, expected)
    
    def test_classify_alcohol_wine(self):
        """Testuoja vynų klasifikavimą."""
        wine_cases = [
            ("Bordeaux Rouge", 13.5, "wine_8.5_15"),
            ("Riesling White Wine", 7.5, "wine_up_to_8.5"),
            ("Moscato d'Asti", 5.5, "wine_up_to_8.5"),
            ("Barolo DOCG", 14.5, "wine_8.5_15"),  # Aukšto ABV vynas
            ("Amarone della Valpolicella", 16.0, "wine_8.5_15")  # Specialus atvejis
        ]
        
        for name, abv, expected in wine_cases:
            with self.subTest(name=name, abv=abv):
                result = classify_alcohol(name, abv)
                self.assertEqual(result, expected)
    
    def test_classify_alcohol_sparkling(self):
        """Testuoja putojančių vynų klasifikavimą."""
        sparkling_cases = [
            ("Dom Pérignon Champagne", 12.5, "sparkling_wine_over_8_5"),
            ("Prosecco di Valdobbiadene", 11.0, "sparkling_wine_over_8_5"),
            ("Cava Brut", 11.5, "sparkling_wine_over_8_5"),
            ("Moscato Spumante", 7.0, "sparkling_wine_up_to_8_5")
        ]
        
        for name, abv, expected in sparkling_cases:
            with self.subTest(name=name, abv=abv):
                result = classify_alcohol(name, abv)
                self.assertEqual(result, expected)
    
    def test_classify_alcohol_spirits(self):
        """Testuoja stipriųjų gėrimų klasifikavimą."""
        spirits_cases = [
            ("Grey Goose Vodka", 40.0, "ethyl_alcohol"),
            ("Jameson Irish Whiskey", 40.0, "ethyl_alcohol"),
            ("Bombay Sapphire Gin", 47.0, "ethyl_alcohol"),
            ("Bacardi Rum", 37.5, "ethyl_alcohol"),
            ("Hennessy Cognac", 40.0, "ethyl_alcohol"),
            ("Baileys Irish Cream Liqueur", 17.0, "ethyl_alcohol")  # Su 'liqueur' raktažodžiu
        ]
        
        for name, abv, expected in spirits_cases:
            with self.subTest(name=name, abv=abv):
                result = classify_alcohol(name, abv)
                self.assertEqual(result, expected)
    
    def test_classify_alcohol_intermediate(self):
        """Testuoja tarpinių produktų klasifikavimą."""
        intermediate_cases = [
            ("Porto Vintage", 20.0, "intermediate_15_22"),
            ("Sherry Fino", 15.0, "intermediate_up_to_15"),
            ("Vermouth Rosso", 16.0, "ethyl_alcohol"),  # Pakeista: vermouth dabar etilo alkoholis
            ("Madeira Wine", 19.0, "intermediate_15_22")
        ]
        
        for name, abv, expected in intermediate_cases:
            with self.subTest(name=name, abv=abv):
                result = classify_alcohol(name, abv)
                self.assertEqual(result, expected)
    
    def test_classify_alcohol_non_alcoholic(self):
        """Testuoja nealkoholinių gėrimų klasifikavimą."""
        non_alcoholic_cases = [
            ("Heineken 0.0", 0.0, "non_alcohol"),
            ("Alcohol Free Beer", 0.5, "non_alcohol"),
            ("Grape Juice", 0.0, "non_alcohol"),
            ("Low Alcohol Wine", 1.0, "non_alcohol")
        ]
        
        for name, abv, expected in non_alcoholic_cases:
            with self.subTest(name=name, abv=abv):
                result = classify_alcohol(name, abv)
                self.assertEqual(result, expected)
    
    def test_classify_alcohol_edge_cases(self):
        """Testuoja kraštinių atvejų klasifikavimą."""
        edge_cases = [
            ("", 0.0, "non_alcohol"),  # Tuščias pavadinimas
            ("Unknown Product", 25.0, "ethyl_alcohol"),  # Aukštas ABV be raktažodžių
            ("Mystery Drink", 8.5, "wine_up_to_8.5"),  # Tiksliai 8.5%
            ("Test Product", 15.0, "wine_8.5_15"),  # Tiksliai 15%
            ("Another Test", 23.0, "ethyl_alcohol")  # Virš 22%
        ]
        
        for name, abv, expected in edge_cases:
            with self.subTest(name=name, abv=abv):
                result = classify_alcohol(name, abv)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()