import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from signals.output import save_to_json, save_to_sqlite
from signals.schemas import SignalRecord

class TestOutput(unittest.TestCase):
    
    def setUp(self):
        # Create temp files for output paths to isolate test writes
        self.temp_dir = tempfile.TemporaryDirectory()
        self.json_path = os.path.join(self.temp_dir.name, "signals.json")
        self.sqlite_path = os.path.join(self.temp_dir.name, "signals.sqlite")
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_json_save_and_append_deduplication(self):
        records: List[SignalRecord] = [
            {
                "company": "Company A",
                "signal_type": "competitor_grievance",
                "source_url": "http://example.com/1",
                "matched_keywords": ["Greenhouse", "slow"],
                "pain_point": "speed",
                "signal_score": 85,
                "detected_at": "2026-05-27T10:00:00Z",
                "reason": "Test reason"
            }
        ]
        
        with patch("signals.output.JSON_OUTPUT_PATH", self.json_path):
            # Save first record
            save_to_json(records)
            
            self.assertTrue(os.path.exists(self.json_path))
            with open(self.json_path, "r") as f:
                data = json.load(f)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]["company"], "Company A")
                
            # Attempt to append the same record (duplicate check on url and pain point)
            save_to_json(records)
            with open(self.json_path, "r") as f:
                data = json.load(f)
                self.assertEqual(len(data), 1) # Size remains 1 due to deduplication!
                
            # Append new record (different url/pain point)
            new_record = records[0].copy()
            new_record["source_url"] = "http://example.com/2"
            new_record["company"] = "Company B"
            save_to_json([new_record])
            
            with open(self.json_path, "r") as f:
                data = json.load(f)
                self.assertEqual(len(data), 2)
                self.assertEqual(data[1]["company"], "Company B")

    def test_sqlite_save_and_upsert(self):
        records: List[SignalRecord] = [
            {
                "company": "Company X",
                "signal_type": "competitor_grievance",
                "source_url": "http://example.com/x",
                "matched_keywords": ["HireVue", "expensive"],
                "pain_point": "cost",
                "signal_score": 75,
                "detected_at": "2026-05-27T10:00:00Z",
                "reason": "Test cost reason"
            }
        ]
        
        with patch("signals.output.SQLITE_OUTPUT_PATH", self.sqlite_path):
            save_to_sqlite(records)
            
            self.assertTrue(os.path.exists(self.sqlite_path))
            
            # Query and verify sqlite table creation and row insertion
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT company, pain_point, signal_score, matched_keywords FROM signals")
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "Company X")
            self.assertEqual(rows[0][1], "cost")
            self.assertEqual(rows[0][2], 75)
            self.assertEqual(json.loads(rows[0][3]), ["HireVue", "expensive"])
            
            # Test Upsert: Insert with same url & pain_point, but update score/company
            updated_record = records[0].copy()
            updated_record["company"] = "Company X Updated"
            updated_record["signal_score"] = 92
            
            save_to_sqlite([updated_record])
            
            cursor.execute("SELECT company, signal_score FROM signals")
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 1) # Size still 1
            self.assertEqual(rows[0][0], "Company X Updated") # Updated!
            self.assertEqual(rows[0][1], 92) # Score updated!
            conn.close()

if __name__ == "__main__":
    unittest.main()
