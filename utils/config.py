import os
from typing import Dict, List, Any

# Environment Overrides
ENV_PREFIX = "DETECTOR_"

def get_env(key: str, default: Any) -> Any:
    """Helper to fetch env variables with prefix."""
    full_key = f"{ENV_PREFIX}{key}"
    val = os.getenv(full_key)
    if val is None:
        return default
    
    # Cast to type of default
    if isinstance(default, bool):
        return val.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        return int(val)
    if isinstance(default, float):
        return float(val)
    if isinstance(default, list):
        return [v.strip() for v in val.split(",") if v.strip()]
    return val

# Output configurations
OUTPUT_DIR = get_env("OUTPUT_DIR", "sample_outputs")
JSON_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "signals.json")
SQLITE_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "signals.sqlite")

# Competitors dictionary with standard capitalization names and list of variations/aliases
COMPETITORS: Dict[str, List[str]] = {
    "HackerRank": ["hackerrank", "hackerrank.com", "hacker rank"],
    "HireVue": ["hirevue", "hirevue.com", "hire vue"],
    "Codility": ["codility", "codility.com"],
    "Greenhouse": ["greenhouse", "greenhouse.io"],
    "Lever": ["lever", "lever.co", "lever co"]
}

# Typo tolerance threshold: Levenshtein distance relative threshold
# e.g., max edit distance ratio of 0.25 (e.g., 2 edits for an 8 character name)
TYPO_DISTANCE_THRESHOLD = get_env("TYPO_DISTANCE_THRESHOLD", 0.2)

# Pain Point keyword mapping
PAIN_POINT_KEYWORDS: Dict[str, List[str]] = {
    "cost": [
        "expensive", "overpriced", "high cost", "charging too much", "budget", 
        "costly", "pricey", "hidden fees", "licensing cost", "subscription fee"
    ],
    "speed": [
        "slow", "bottleneck", "delay", "lag", "takes too long", "sluggish", 
        "loading time", "timeout", "slow pipeline"
    ],
    "fairness": [
        "bias", "unfair", "biased", "discrimination", "cheating false positive",
        "discriminate", "unjustified", "rigged"
    ],
    "experience": [
        "poor ux", "frustrating", "candidate dropoff", "horrible interface", 
        "bad experience", "clunky", "painful", "nightmare", "bad ux", 
        "confusing", "terrible candidate experience"
    ],
    "reliability": [
        "inaccurate", "broken", "failed", "crash", "bug", "downtime", 
        "glitch", "freeze", "error", "disconnect", "unreliable", "outage"
    ]
}

# Negation words to look for within a short prefix window of a complaint keyword
NEGATION_WORDS: List[str] = [
    "not", "never", "no", "don't", "dont", "cannot", "cant", "isn't", "isnt",
    "wasn't", "wasnt", "haven't", "havent", "hardly", "barely", "neither", "nor"
]

# Source Quality Scoring Weights
SOURCE_QUALITY_WEIGHTS: Dict[str, int] = {
    "g2": 15,
    "trustpilot": 15,
    "reddit": 12,
    "blog": 10,
    "rss": 8,
    "other": 8
}

# Scoring Coefficients (Sum must equal 100)
# Competitor Confidence (25) + Complaint Strength (25) + Distance Score (20) + Source Quality (15) + Recency (15)
SCORE_WEIGHTS: Dict[str, int] = {
    "competitor_confidence": 25,
    "complaint_strength": 25,
    "distance_score": 20,
    "source_quality": 15,
    "recency": 15
}

# Mock data configuration for fallback
ENABLE_MOCK_FALLBACK = get_env("ENABLE_MOCK_FALLBACK", True)
