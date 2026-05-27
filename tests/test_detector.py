import unittest
from signals.detector import detect_competitors

class TestDetector(unittest.TestCase):
    
    def test_exact_matches(self):
        text = "We are using Greenhouse and HackerRank."
        matches = detect_competitors(text)
        competitors = {m["competitor"] for m in matches}
        self.assertIn("Greenhouse", competitors)
        self.assertIn("HackerRank", competitors)
        self.assertEqual(len(matches), 2)
        
    def test_case_insensitivity(self):
        text = "we deployed hirevue last quarter and also lever for ats."
        matches = detect_competitors(text)
        competitors = {m["competitor"] for m in matches}
        self.assertIn("HireVue", competitors)
        self.assertIn("Lever", competitors)
        self.assertEqual(len(matches), 2)

    def test_plural_matching(self):
        text = "Our recruiters love using hackerranks for testing."
        matches = detect_competitors(text)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["competitor"], "HackerRank")
        self.assertEqual(matches[0]["matched_phrase"], "hackerranks")

    def test_typo_tolerance_valid(self):
        # "hackerranc" has edit distance 1 from "hackerrank"
        text = "The coding test on hackerranc was buggy."
        matches = detect_competitors(text)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["competitor"], "HackerRank")
        self.assertEqual(matches[0]["matched_phrase"], "hackerranc")

        # "leven" has edit distance 1 from "lever" and shares first letter
        text = "We are migrating away from Leven today."
        matches = detect_competitors(text)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["competitor"], "Lever")
        self.assertEqual(matches[0]["matched_phrase"], "leven")

    def test_typo_tolerance_invalid(self):
        # "clever" has distance 1 from "lever" but starts with 'c' not 'l'
        text = "Our HR team is clever and fast."
        matches = detect_competitors(text)
        self.assertEqual(len(matches), 0)
        
        # "never" has distance 1 from "lever" but starts with 'n'
        text = "We would never switch our ATS."
        matches = detect_competitors(text)
        self.assertEqual(len(matches), 0)
        
        # Typos that exceed threshold distance ratio should be skipped
        text = "We are using Green."
        matches = detect_competitors(text)
        self.assertEqual(len(matches), 0)

    def test_empty_input(self):
        self.assertEqual(detect_competitors(""), [])
        self.assertEqual(detect_competitors(None), [])

if __name__ == "__main__":
    unittest.main()
