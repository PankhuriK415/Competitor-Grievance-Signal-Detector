from typing import Dict, Any, Tuple
from utils.config import SCORE_WEIGHTS, SOURCE_QUALITY_WEIGHTS
from utils.logger import logger
from utils.date_utils import get_days_ago
from utils.text_utils import levenshtein_distance
from signals.schemas import CompetitorMatch, ComplaintMatch, IngestedDocument

# Strong keywords indicating severe dissatisfaction
STRONG_COMPLAINTS = {
    "horrible", "awful", "terrible", "nightmare", "broken", "failed", "unfair", 
    "bias", "overpriced", "useless", "downtime", "outage", "failed to load", 
    "charging too much", "hate", "scam", "crashed", "buggy"
}

def calculate_competitor_confidence(competitor: str, matched_phrase: str) -> int:
    """Calculates competitor confidence score (max 25) based on edit distance."""
    # If the match is case-insensitive exact, full points
    if matched_phrase.lower() == competitor.lower():
        return 25
        
    dist = levenshtein_distance(matched_phrase, competitor)
    if dist == 0:
        return 25
    elif dist == 1:
        return 18
    elif dist == 2:
        return 12
    else:
        return 8

def calculate_complaint_strength(keyword: str, sentence: str) -> int:
    """Calculates complaint strength (max 25) based on keyword intensity and emphasis (caps/exclamations)."""
    base_score = 15
    kw_lower = keyword.lower()
    
    # Check if keyword is classified as strong
    if kw_lower in STRONG_COMPLAINTS or any(skw in kw_lower for skw in STRONG_COMPLAINTS):
        base_score = 20
        
    # Check for emphasis in the sentence:
    # 1. Exclamation mark
    if "!" in sentence:
        base_score += 3
        
    # 2. Capitalization check (capitalized word that is not the competitor name or start of sentence)
    words = sentence.split()
    has_caps = False
    for i, w in enumerate(words):
        if w.isupper() and len(w) >= 3 and i > 0:
            has_caps = True
            break
    if has_caps:
        base_score += 2
        
    return min(25, base_score)

def calculate_distance_score(distance: int) -> int:
    """Calculates distance score (max 20) based on token proximity inside the sentence."""
    if distance <= 3:
        return 20
    elif distance <= 8:
        return 15
    elif distance <= 15:
        return 10
    else:
        return 5

def calculate_source_score(source: str) -> int:
    """Calculates source quality score (max 15) using config weights."""
    return SOURCE_QUALITY_WEIGHTS.get(source.lower(), 8)

def calculate_recency_score(timestamp: str) -> int:
    """Calculates recency score (max 15) based on document age in days."""
    days_ago = get_days_ago(timestamp)
    if days_ago <= 7.0:
        return 15
    elif days_ago <= 30.0:
        return 12
    elif days_ago <= 90.0:
        return 8
    else:
        return 4

def evaluate_signal(
    doc: IngestedDocument, 
    comp_match: CompetitorMatch, 
    complaint_match: ComplaintMatch
) -> Tuple[int, str]:
    """Evaluates the 5-factor confidence score for a signal.
    
    Returns a tuple of (total_score, reason_explanation).
    """
    comp_conf = calculate_competitor_confidence(comp_match["competitor"], comp_match["matched_phrase"])
    complaint_strength = calculate_complaint_strength(complaint_match["matched_keyword"], complaint_match["sentence"])
    dist_score = calculate_distance_score(complaint_match["distance"])
    source_score = calculate_source_score(doc["source"])
    recency_score = calculate_recency_score(doc["timestamp"])
    
    total_score = comp_conf + complaint_strength + dist_score + source_score + recency_score
    
    confidence_label = "low"
    if total_score >= 80:
        confidence_label = "high"
    elif total_score >= 60:
        confidence_label = "moderate"
        
    reason = (
        f"Detected complaint tied to {comp_match['competitor']} with {confidence_label} contextual confidence. "
        f"Score Breakdown ({total_score}/100): "
        f"Competitor Confidence={comp_conf}/25, "
        f"Complaint Strength={complaint_strength}/25, "
        f"Distance Score={dist_score}/20, "
        f"Source Quality={source_score}/15, "
        f"Recency={recency_score}/15."
    )
    
    logger.info(f"Scored signal for {comp_match['competitor']} on {doc['source']}: {total_score} points. Reason: {reason}")
    return total_score, reason
