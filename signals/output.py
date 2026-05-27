import json
import os
import sqlite3
from typing import List
from utils.logger import logger
from utils.config import JSON_OUTPUT_PATH, SQLITE_OUTPUT_PATH
from signals.schemas import SignalRecord

def ensure_output_directory(filepath: str) -> None:
    """Ensures the parent directory of a file path exists."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def save_to_json(records: List[SignalRecord]) -> None:
    """Saves or appends records to the JSON file, preventing duplicates based on URL and pain point."""
    if not records:
        return
        
    ensure_output_directory(JSON_OUTPUT_PATH)
    
    existing_records: List[SignalRecord] = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    existing_records = data
        except Exception as e:
            logger.warning(f"Failed to read existing JSON output file, creating fresh file: {e}")
            
    # Deduplicate: Create set of keys for existing items
    # Key is (source_url, pain_point)
    existing_keys = {
        (rec.get("source_url"), rec.get("pain_point"))
        for rec in existing_records
    }
    
    new_added = 0
    for rec in records:
        key = (rec["source_url"], rec["pain_point"])
        if key not in existing_keys:
            existing_records.append(rec)
            existing_keys.add(key)
            new_added += 1
            
    try:
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_records, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {new_added} new signals to JSON file at: {JSON_OUTPUT_PATH} (Total: {len(existing_records)})")
    except Exception as e:
        logger.error(f"Failed to write signals to JSON: {e}")

def save_to_sqlite(records: List[SignalRecord]) -> None:
    """Saves records to the SQLite database, using INSERT OR REPLACE to update changes and avoid duplicates."""
    if not records:
        return
        
    ensure_output_directory(SQLITE_OUTPUT_PATH)
    
    conn = None
    try:
        conn = sqlite3.connect(SQLITE_OUTPUT_PATH)
        cursor = conn.cursor()
        
        # Create table with unique constraint on url and pain point
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                matched_keywords TEXT NOT NULL, -- Stored as JSON string
                pain_point TEXT NOT NULL,
                signal_score INTEGER NOT NULL,
                detected_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                UNIQUE(source_url, pain_point)
            )
        """)
        
        new_inserted = 0
        for rec in records:
            # Check if matching unique constraint already exists to count new insertions
            cursor.execute(
                "SELECT 1 FROM signals WHERE source_url = ? AND pain_point = ?", 
                (rec["source_url"], rec["pain_point"])
            )
            exists = cursor.fetchone()
            if not exists:
                new_inserted += 1
                
            cursor.execute("""
                INSERT OR REPLACE INTO signals (
                    company, signal_type, source_url, matched_keywords, 
                    pain_point, signal_score, detected_at, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec["company"],
                rec["signal_type"],
                rec["source_url"],
                json.dumps(rec["matched_keywords"]),
                rec["pain_point"],
                rec["signal_score"],
                rec["detected_at"],
                rec["reason"]
            ))
            
        conn.commit()
        logger.info(f"SQLite Sync: Inserted {new_inserted} new and updated/replaced total {len(records)} records in SQLite at: {SQLITE_OUTPUT_PATH}")
    except Exception as e:
        logger.error(f"Failed to save signals to SQLite: {e}")
    finally:
        if conn:
            conn.close()

def save_signals(records: List[SignalRecord]) -> None:
    """Main function to save signals to all registered outputs."""
    save_to_json(records)
    save_to_sqlite(records)
