import re
from typing import List, Dict, Set
from utils.config import PAIN_POINT_KEYWORDS
from utils.logger import logger
from utils.text_utils import split_into_sentences, is_negated, get_token_distance, tokenize
from signals.schemas import ComplaintMatch, CompetitorMatch

# Standard patterns for false positives
FALSE_POSITIVE_PATTERNS = [
    # Competitor is making the claim about others
    r"\b(claims|claims that|argues|says|stated|believes)\b.*\b(expensive|slow|unfair|broken|bias)\b",
    # Hypothesizing or hearsay rather than direct experience
    r"\b(if|might|should be)\b.*\b(expensive|slow|unfair|broken|bias)\b"
]

def is_false_positive_sentence(sentence: str, competitor_phrase: str) -> bool:
    """Uses pattern heuristics to check if the sentence is a false positive match."""
    sent_lower = sentence.lower()
    comp_lower = competitor_phrase.lower()
    
    # Check if the sentence has the competitor name
    if comp_lower not in sent_lower:
        return False
        
    # Check if competitor is part of a "claims" pattern
    # e.g., "HireVue claims competitors are expensive"
    for pattern in FALSE_POSITIVE_PATTERNS:
        match = re.search(pattern, sent_lower)
        if match:
            # Check if the competitor comes before the verb (claims/says)
            comp_idx = sent_lower.find(comp_lower)
            verb_idx = sent_lower.find(match.group(1))
            if comp_idx < verb_idx:
                logger.info(f"Rejected false positive (claims/claims pattern): '{sentence}'")
                return True
                
    # Check for direct positive attributes that negate a complaint
    # e.g. "We switched to Lever which is fast and not slow" - negation handler will filter "not slow",
    # but what if it says "Greenhouse is great, very fast" and we have a cost keyword elsewhere?
    # Proximity constraints will handle this.
    
    return False

def classify_complaints(text: str, competitor_matches: List[CompetitorMatch]) -> Dict[str, List[ComplaintMatch]]:
    """Scans the text for complaints tied to the detected competitors.
    
    Supports a sentence window of 1, checking the same sentence as the competitor 
    mention as well as the immediately preceding and succeeding sentences.
    """
    results: Dict[str, List[ComplaintMatch]] = {
        "cost": [],
        "speed": [],
        "fairness": [],
        "experience": [],
        "reliability": []
    }
    
    if not text or not competitor_matches:
        return results
        
    sentences = split_into_sentences(text)
    
    for comp in competitor_matches:
        comp_phrase = comp["matched_phrase"]
        
        # Scan through all sentences to find competitor mentions
        for s_idx, sent in enumerate(sentences):
            if comp_phrase.lower() not in sent.lower():
                continue
                
            # Define window: preceding sentence, same sentence, and succeeding sentence
            for target_idx in (s_idx - 1, s_idx, s_idx + 1):
                if target_idx < 0 or target_idx >= len(sentences):
                    continue
                    
                target_sent = sentences[target_idx]
                target_sent_lower = target_sent.lower()
                
                # Check false positive patterns only in the sentence containing the competitor
                if target_idx == s_idx and is_false_positive_sentence(target_sent, comp_phrase):
                    continue
                    
                for category, keywords in PAIN_POINT_KEYWORDS.items():
                    for kw in keywords:
                        # Exact word boundary check for keywords
                        pattern = rf"\b{re.escape(kw)}\b"
                        if re.search(pattern, target_sent_lower):
                            # Negation check on the sentence containing the keyword
                            if is_negated(target_sent, kw):
                                logger.info(f"Ignored negated keyword '{kw}' in sentence: '{target_sent}'")
                                continue
                                
                            # Calculate distance
                            if target_idx == s_idx:
                                # Same sentence distance
                                dist = get_token_distance(target_sent, comp_phrase, kw)
                            else:
                                # Adjacent sentence distance penalty
                                dist = 12
                                
                            # Build the complaint match
                            complaint_match: ComplaintMatch = {
                                "pain_point": category,
                                "matched_keyword": kw,
                                "sentence": target_sent,
                                "distance": dist,
                                "negated": False
                            }
                            
                            # Avoid appending exact duplicate (same sentence, same keyword)
                            if not any(
                                r["sentence"] == target_sent and r["matched_keyword"] == kw 
                                for r in results[category]
                            ):
                                results[category].append(complaint_match)
                                logger.info(f"Detected complaint match [{category}]: '{kw}' near '{comp_phrase}' in sentence: '{target_sent}' (distance: {dist})")
                                
    return results
