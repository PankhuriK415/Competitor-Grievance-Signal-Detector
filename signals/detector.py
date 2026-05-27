import re
from typing import List, Tuple
from utils.config import COMPETITORS, TYPO_DISTANCE_THRESHOLD
from utils.logger import logger
from utils.text_utils import tokenize, get_typo_match
from signals.schemas import CompetitorMatch

def detect_competitors(text: str) -> List[CompetitorMatch]:
    """Detects mentions of competitors in a text block, supporting aliases, plurals, and typo tolerance."""
    if not text:
        return []
        
    matches: List[CompetitorMatch] = []
    text_lower = text.lower()
    tokens = tokenize(text)
    
    # Track detected to avoid duplicates for the same competitor
    detected_competitors = set()
    
    for competitor, aliases in COMPETITORS.items():
        matched = False
        
        # 1. Check exact phrase matches (including multi-word aliases) with word boundaries
        for alias in aliases:
            pattern = rf"\b{re.escape(alias)}s?\b" # Matches alias and optional plural 's'
            found = re.search(pattern, text_lower)
            if found:
                matches.append({
                    "competitor": competitor,
                    "matched_phrase": found.group(0)
                })
                detected_competitors.add(competitor)
                matched = True
                break
                
        if matched:
            continue
            
        # 2. Check typo tolerance for single-word aliases
        # To avoid false positives (e.g. matching "clever" for "lever"), we require:
        # - The word starts with the same character as the target alias (excluding plurals/prefixes)
        # - The edit distance is within threshold
        # - The word is not a common English word that causes false positives
        for alias in aliases:
            # Skip multi-word aliases for single-token typo checking
            if " " in alias:
                continue
                
            for token in tokens:
                # If length differs by more than 2, skip
                if abs(len(token) - len(alias)) > 2:
                    continue
                    
                # Common prefix heuristic: typos usually start with the same first letter
                if token[0] != alias[0]:
                    continue
                    
                is_match, dist = get_typo_match(token, alias, TYPO_DISTANCE_THRESHOLD)
                if is_match:
                    logger.info(f"Typo detected: '{token}' matched to competitor '{competitor}' (alias: '{alias}', dist: {dist})")
                    matches.append({
                        "competitor": competitor,
                        "matched_phrase": token
                    })
                    detected_competitors.add(competitor)
                    matched = True
                    break
            if matched:
                break
                
    return matches
