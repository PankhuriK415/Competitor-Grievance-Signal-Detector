import unittest
from unittest.mock import patch

from signals.scorer import (
    calculate_competitor_confidence,
    calculate_complaint_strength,
    calculate_distance_score,
    calculate_source_score,
    calculate_recency_score,
    evaluate_signal
)
from signals.schemas import IngestedDocument, CompetitorMatch, ComplaintMatch

class TestScorer(unittest.TestCase):
    
    def test_competitor_confidence(self):
        # Exact match
        self.assertEqual(calculate_competitor_confidence("HireVue", "HireVue"), 25)
        self.assertEqual(calculate_competitor_confidence("HireVue", "hirevue"), 25)
        # Typo match distance 1
        self.assertEqual(calculate_competitor_confidence("HireVue", "Hirevuee"), 18)
        # Typo match distance 2
        self.assertEqual(calculate_competitor_confidence("HackerRank", "Hackerranc"), 18) # dist = 1 ('k' -> 'c')

    def test_complaint_strength(self):
        # Standard keyword
        self.assertEqual(calculate_complaint_strength("slow", "Our platform was slow."), 15)
        # Strong keyword
        self.assertEqual(calculate_complaint_strength("broken", "Our platform was broken."), 20)
        # Exclamation boost
        self.assertEqual(calculate_complaint_strength("slow", "Our platform was slow!"), 18)
        # Caps boost (excluding competitor name or first word)
        self.assertEqual(calculate_complaint_strength("slow", "Our platform is REALLY slow."), 17)
        # Combined boosts
        self.assertEqual(calculate_complaint_strength("broken", "Our platform was BROKEN!"), 25)

    def test_distance_score(self):
        self.assertEqual(calculate_distance_score(2), 20)
        self.assertEqual(calculate_distance_score(5), 15)
        self.assertEqual(calculate_distance_score(12), 10)
        self.assertEqual(calculate_distance_score(25), 5)

    def test_source_score(self):
        self.assertEqual(calculate_source_score("g2"), 15)
        self.assertEqual(calculate_source_score("trustpilot"), 15)
        self.assertEqual(calculate_source_score("reddit"), 12)
        self.assertEqual(calculate_source_score("blog"), 10)
        self.assertEqual(calculate_source_score("unknown_src"), 8)

    @patch("signals.scorer.get_days_ago")
    def test_recency_score(self, mock_days_ago):
        # <= 7 days
        mock_days_ago.return_value = 3.0
        self.assertEqual(calculate_recency_score("dummy_timestamp"), 15)
        # <= 30 days
        mock_days_ago.return_value = 15.0
        self.assertEqual(calculate_recency_score("dummy_timestamp"), 12)
        # <= 90 days
        mock_days_ago.return_value = 60.0
        self.assertEqual(calculate_recency_score("dummy_timestamp"), 8)
        # > 90 days
        mock_days_ago.return_value = 120.0
        self.assertEqual(calculate_recency_score("dummy_timestamp"), 4)

    @patch("signals.scorer.get_days_ago")
    def test_evaluate_signal_integration(self, mock_days_ago):
        mock_days_ago.return_value = 5.0 # Recency score = 15
        
        doc: IngestedDocument = {
            "text": "HireVue is extremely slow!",
            "source": "reddit", # Source score = 12
            "url": "http://reddit.com/1",
            "timestamp": "2026-05-27T10:00:00Z",
            "author": "hr_user",
            "company": "CompanyX"
        }
        comp_match: CompetitorMatch = {
            "competitor": "HireVue", # Confidence = 25
            "matched_phrase": "HireVue"
        }
        complaint: ComplaintMatch = {
            "pain_point": "speed",
            "matched_keyword": "slow", # Strength = 15 + 3 (exclamation) = 18
            "sentence": "HireVue is extremely slow!",
            "distance": 1, # Distance score = 20
            "negated": False
        }
        
        # Expected Total Score: 25 + 18 + 20 + 12 + 15 = 90
        score, reason = evaluate_signal(doc, comp_match, complaint)
        self.assertEqual(score, 90)
        self.assertIn("high contextual confidence", reason)
        self.assertIn("Score Breakdown (90/100)", reason)
        self.assertIn("Competitor Confidence=25/25", reason)
        self.assertIn("Complaint Strength=18/25", reason)
        self.assertIn("Distance Score=20/20", reason)
        self.assertIn("Source Quality=12/15", reason)
        self.assertIn("Recency=15/15", reason)

if __name__ == "__main__":
    unittest.main()
