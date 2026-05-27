import unittest
from signals.classifier import classify_complaints

class TestClassifier(unittest.TestCase):
    
    def test_basic_classification(self):
        text = "Our team is frustrated with HireVue. The candidate experience is clunky and slow."
        comp_matches = [{"competitor": "HireVue", "matched_phrase": "HireVue"}]
        
        results = classify_complaints(text, comp_matches)
        
        # Should flag speed ("slow") and experience ("frustrated", "clunky", "experience")
        self.assertTrue(len(results["speed"]) > 0)
        self.assertTrue(len(results["experience"]) > 0)
        self.assertEqual(results["speed"][0]["matched_keyword"], "slow")
        self.assertEqual(results["speed"][0]["pain_point"], "speed")
        
    def test_negation_filtering(self):
        # "not slow" should be ignored for speed
        text = "We switched to Greenhouse and it is not slow. Although it is overpriced."
        comp_matches = [{"competitor": "Greenhouse", "matched_phrase": "Greenhouse"}]
        
        results = classify_complaints(text, comp_matches)
        
        self.assertEqual(len(results["speed"]), 0) # "not slow" negated
        self.assertTrue(len(results["cost"]) > 0)  # "overpriced" not negated
        self.assertEqual(results["cost"][0]["matched_keyword"], "overpriced")

    def test_false_positive_rejection(self):
        # "HireVue claims competitors are slow" -> HireVue is speaker, not the slow platform
        text = "HireVue claims competitors are slow and expensive."
        comp_matches = [{"competitor": "HireVue", "matched_phrase": "HireVue"}]
        
        results = classify_complaints(text, comp_matches)
        
        self.assertEqual(len(results["speed"]), 0)
        self.assertEqual(len(results["cost"]), 0)

    def test_multi_competitor_isolation(self):
        # "Greenhouse is slow but Lever is expensive" -> isolates Greenhouse to speed, Lever to cost
        text = "Greenhouse is slow. In contrast, Lever is expensive."
        comp_matches = [
            {"competitor": "Greenhouse", "matched_phrase": "Greenhouse"},
            {"competitor": "Lever", "matched_phrase": "Lever"}
        ]
        
        results = classify_complaints(text, comp_matches)
        
        # Greenhouse is in the sentence with slow
        greenhouse_speed = [r for r in results["speed"] if "greenhouse" in r["sentence"].lower()]
        self.assertEqual(len(greenhouse_speed), 1)
        
        # Lever is in the sentence with expensive
        lever_cost = [r for r in results["cost"] if "lever" in r["sentence"].lower()]
        self.assertEqual(len(lever_cost), 1)

if __name__ == "__main__":
    unittest.main()
