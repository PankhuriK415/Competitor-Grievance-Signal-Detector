#!/usr/bin/env python3
import argparse
import sys
from typing import List

from utils.logger import setup_logger
from utils.date_utils import get_current_iso
from signals.fetcher import fetch_reddit, fetch_g2_reviews, fetch_trustpilot, fetch_public_blog_comments
from signals.parser import parse_and_normalize
from signals.detector import detect_competitors
from signals.classifier import classify_complaints
from signals.scorer import evaluate_signal
from signals.output import save_signals
from signals.schemas import SignalRecord

def parse_args() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Competitor Grievance Signal Detector Pipeline CLI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--source",
        choices=["all", "reddit", "g2", "trustpilot", "blog"],
        default="all",
        help="Target ingestion data source."
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=40,
        help="Minimum signal score threshold (0-100). Records below this score are discarded."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enforce live HTTP fetching. If false, simulated mock data will be used."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging output."
    )
    return parser.parse_args()

def run_pipeline(source: str, threshold: int, live: bool) -> List[SignalRecord]:
    """Runs the ingestion, detection, scoring, classification, and saving pipeline."""
    # 1. Ingestion Phase
    raw_documents = []
    
    if source in ("all", "reddit"):
        raw_documents.extend(fetch_reddit(live=live))
    if source in ("all", "g2"):
        raw_documents.extend(fetch_g2_reviews(live=live))
    if source in ("all", "trustpilot"):
        raw_documents.extend(fetch_trustpilot(live=live))
    if source in ("all", "blog"):
        raw_documents.extend(fetch_public_blog_comments(live=live))
        
    # 2. Parsing & Normalization
    normalized_docs = parse_and_normalize(raw_documents)
    
    detected_signals: List[SignalRecord] = []
    
    # 3. Processing each document
    for doc in normalized_docs:
        # Detect Competitor Mentions
        comp_matches = detect_competitors(doc["text"])
        if not comp_matches:
            continue
            
        # Classify Grievances / Pain Points
        complaints_by_category = classify_complaints(doc["text"], comp_matches)
        
        # Evaluate matches per category and competitor
        # Note: A single document can mention multiple competitors or pain points.
        # We output a separate target signal record per competitor and pain point for precise outreach routing.
        for category, complaints in complaints_by_category.items():
            for complaint in complaints:
                # Find matching competitor info for this complaint
                comp_match = None
                for cm in comp_matches:
                    if cm["matched_phrase"].lower() in complaint["sentence"].lower():
                        comp_match = cm
                        break
                        
                if not comp_match:
                    # Fallback to the first competitor found in the doc if not sentence-specific
                    comp_match = comp_matches[0]
                    
                # 4. Scoring Engine
                score, reason = evaluate_signal(doc, comp_match, complaint)
                
                # Filter based on threshold (and global minimum threshold of 40)
                effective_threshold = max(40, threshold)
                if score < effective_threshold:
                    continue
                    
                signal_record: SignalRecord = {
                    "company": doc["company"],
                    "signal_type": "competitor_grievance",
                    "source_url": doc["url"],
                    "matched_keywords": [comp_match["competitor"], complaint["matched_keyword"]],
                    "pain_point": category,
                    "signal_score": score,
                    "detected_at": get_current_iso(),
                    "reason": reason
                }
                
                # Check for duplicates in memory before adding
                if signal_record not in detected_signals:
                    detected_signals.append(signal_record)
                    
    # 5. Output Sync
    if detected_signals:
        save_signals(detected_signals)
        
    return detected_signals

def main() -> None:
    args = parse_args()
    
    # Configure logging
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=log_level)
    
    print("=" * 70)
    print(" COMPETITOR GRIEVANCE SIGNAL DETECTOR ".center(70, "="))
    print("=" * 70)
    print(f"Source:    {args.source}")
    print(f"Threshold: {args.threshold} (Global Min: 40)")
    print(f"Fetch Mode: {'Live Network' if args.live else 'Cached / Mock Simulator'}")
    print("-" * 70)
    
    try:
        signals = run_pipeline(args.source, args.threshold, args.live)
        
        print("-" * 70)
        print(f"Pipeline execution completed successfully.")
        print(f"Ingested & Deduplicated Documents processed.")
        print(f"Extracted Signals matching criteria: {len(signals)}")
        print("-" * 70)
        
        if signals:
            print("\nDETECTIONS FOUND:\n")
            for i, sig in enumerate(signals, 1):
                print(f"[{i}] Company:       {sig['company']}")
                print(f"    Competitor:    {sig['matched_keywords'][0]}")
                # Matched keyword might be the second item in matched_keywords
                print(f"    Keyword:       '{sig['matched_keywords'][1]}'")
                print(f"    Pain Point:    {sig['pain_point'].upper()}")
                print(f"    Score:         {sig['signal_score']}/100")
                print(f"    Source URL:    {sig['source_url']}")
                print(f"    Reason:        {sig['reason']}")
                print("-" * 60)
            
            print("\nOutputs Synced:")
            print(f" - JSON:   sample_outputs/signals.json")
            print(f" - SQLite: sample_outputs/signals.sqlite\n")
        else:
            print("\nNo signals matching the criteria were detected in this run.\n")
            
    except Exception as e:
        print(f"\n[FATAL ERROR] Pipeline run failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
