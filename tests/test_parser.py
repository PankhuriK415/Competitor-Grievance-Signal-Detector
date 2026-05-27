import unittest
from signals.parser import parse_and_normalize, extract_company_from_text

class TestParser(unittest.TestCase):
    
    def test_extract_company_from_text(self):
        self.assertEqual(extract_company_from_text("We at Google use various tools."), "Google")
        self.assertEqual(extract_company_from_text("Our team at Microsoft is struggling."), "Microsoft")
        self.assertEqual(extract_company_from_text("I work at OpenAI and it's fast."), "OpenAI")
        self.assertEqual(extract_company_from_text("This is an anonymous post."), "Unknown")
        # Cleans trailing verbs
        self.assertEqual(extract_company_from_text("Our company, AcmeCorp uses HireVue."), "AcmeCorp")

    def test_deduplication_and_whitespace_cleaning(self):
        raw_docs = [
            {
                "text": "  HireVue  is   slow. ",
                "source": "reddit",
                "url": "http://reddit.com/1",
                "timestamp": "2026-05-27T10:00:00Z",
                "author": "user1",
                "company": "CompanyA"
            },
            # Exact duplicate text and url, should be filtered out
            {
                "text": "HireVue is slow.",
                "source": "reddit",
                "url": "http://reddit.com/1",
                "timestamp": "2026-05-27T10:05:00Z",
                "author": "user2",
                "company": "CompanyB"
            },
            # Same text, different url is allowed (cross-posting)
            {
                "text": "HireVue is slow.",
                "source": "reddit",
                "url": "http://reddit.com/2",
                "timestamp": "2026-05-27T10:05:00Z",
                "author": "user2",
                "company": "CompanyB"
            }
        ]
        
        normalized = parse_and_normalize(raw_docs)
        self.assertEqual(len(normalized), 2)
        # Verify text cleaning (spaces normalized)
        self.assertEqual(normalized[0]["text"], "HireVue is slow.")
        
    def test_timestamp_fallback(self):
        raw_docs = [
            {
                "text": "HackerRank is expensive.",
                "source": "blog",
                "url": "http://blog.com/1",
                "timestamp": "invalid-date-format",
                "author": "writer",
                "company": "Unknown"
            }
        ]
        normalized = parse_and_normalize(raw_docs)
        self.assertEqual(len(normalized), 1)
        # Should parse to a valid ISO format from datetime fallback
        self.assertTrue(normalized[0]["timestamp"].startswith("2026-")) # Current year is 2026 in metadata!

if __name__ == "__main__":
    unittest.main()
