import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from signals.fetcher import (
    fetch_reddit, 
    fetch_g2_reviews, 
    fetch_trustpilot, 
    fetch_public_blog_comments,
    fetch_with_retry
)

class TestFetcher(unittest.TestCase):
    
    @patch("signals.fetcher.MOCK_DOCUMENTS", [{"source": "reddit", "text": "mock_reddit"}])
    def test_fetch_reddit_mock(self):
        # With live=False, it should return mock data
        results = fetch_reddit(live=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "mock_reddit")
        
    @patch("signals.fetcher.MOCK_DOCUMENTS", [{"source": "g2", "text": "mock_g2"}])
    def test_fetch_g2_mock(self):
        # G2 always returns mock data
        results = fetch_g2_reviews(live=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "mock_g2")

    @patch("signals.fetcher.MOCK_DOCUMENTS", [{"source": "trustpilot", "text": "mock_tp"}])
    def test_fetch_trustpilot_mock(self):
        # Trustpilot always returns mock data
        results = fetch_trustpilot(live=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "mock_tp")

    @patch("signals.fetcher.fetch_with_retry")
    def test_fetch_reddit_live_success(self, mock_fetch):
        # Simulate successful JSON response from Reddit API
        mock_json = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "HireVue issue",
                            "selftext": "Candidate dropoff is high",
                            "permalink": "/r/recruiting/comments/xyz",
                            "created_utc": 1700000000.0,
                            "author": "hr_manager"
                        }
                    }
                ]
            }
        }
        import json
        mock_fetch.return_value = json.dumps(mock_json).encode("utf-8")
        
        results = fetch_reddit(live=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "HireVue issue\nCandidate dropoff is high")
        self.assertEqual(results[0]["source"], "reddit")
        self.assertEqual(results[0]["author"], "hr_manager")
        
    @patch("signals.fetcher.fetch_with_retry")
    @patch("signals.fetcher.ENABLE_MOCK_FALLBACK", True)
    @patch("signals.fetcher.MOCK_DOCUMENTS", [{"source": "reddit", "text": "fallback_reddit"}])
    def test_fetch_reddit_live_failure_fallback(self, mock_fetch):
        # Simulate network error
        mock_fetch.side_effect = Exception("Network Down")
        
        # Should fallback to mock data
        results = fetch_reddit(live=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "fallback_reddit")

    @patch("urllib.request.urlopen")
    def test_fetch_with_retry_logic(self, mock_urlopen):
        # Simulate HTTPError 429 once, then success
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.read.return_value = b"success_content"
        
        # Side effect: first call raises 429, second succeeds
        mock_urlopen.side_effect = [
            urllib.error.HTTPError("http://test.com", 429, "Too Many Requests", {}, None),
            mock_response
        ]
        
        with patch("time.sleep") as mock_sleep:
            content = fetch_with_retry("http://test.com", retries=2, backoff=0.01)
            self.assertEqual(content, b"success_content")
            self.assertEqual(mock_sleep.call_count, 1)

if __name__ == "__main__":
    unittest.main()
