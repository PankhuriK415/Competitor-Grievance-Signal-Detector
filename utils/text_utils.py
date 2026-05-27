import re
from typing import List, Tuple
from utils.config import NEGATION_WORDS

def split_into_sentences(text: str) -> List[str]:
    """Splits a block of text into individual sentences, preserving delimiters and handling abbreviations.
    
    Avoids using look-behind regex patterns of variable width to maintain Python compatibility.
    """
    if not text:
        return []
        
    # Split on period, question mark, or exclamation mark followed by whitespace or string end.
    # Capture the delimiter to reconstruct later.
    raw_splits = re.split(r"([.!?]+(?:\s+|$))", text)
    sentences = []
    
    current = ""
    abbreviations = {
        "e.g.", "i.e.", "vs.", "corp.", "inc.", "co.", "mr.", "mrs.", "dr.", 
        "st.", "etc.", "rd.", "vol.", "ref."
    }
    
    for i in range(0, len(raw_splits), 2):
        sentence_part = raw_splits[i]
        delimiter = raw_splits[i+1] if i+1 < len(raw_splits) else ""
        
        combined = (current + sentence_part + delimiter).strip()
        if not combined:
            continue
            
        # Check if the combined block ends in an abbreviation
        is_abbr = False
        for abbr in abbreviations:
            if combined.lower().endswith(abbr):
                is_abbr = True
                break
                
        if is_abbr:
            current += sentence_part + delimiter
        else:
            sentences.append(combined)
            current = ""
            
    if current:
        sentences.append(current.strip())
        
    return [s for s in sentences if s]

def tokenize(text: str) -> List[str]:
    """Splits a text into lowercase word tokens, stripping punctuation."""
    return re.findall(r'\b\w+\b', text.lower())

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates the Levenshtein distance between two strings."""
    s1 = s1.lower()
    s2 = s2.lower()
    
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def get_typo_match(word: str, target: str, relative_threshold: float = 0.2) -> Tuple[bool, int]:
    """Checks if a word matches a target string allowing for edit-distance typo tolerance."""
    w_len = len(word)
    t_len = len(target)
    if abs(w_len - t_len) > 2:
        return False, 999
        
    dist = levenshtein_distance(word, target)
    max_allowed = max(1, int(t_len * relative_threshold))
    
    return dist <= max_allowed, dist

def is_negated(sentence: str, keyword: str) -> bool:
    """Checks if a keyword in a sentence is preceded by a negation word within a small window.
    
    Checks up to 3 tokens before the keyword.
    """
    # Find the positions of the keyword in the tokenized sentence
    tokens = tokenize(sentence)
    kw_tokens = tokenize(keyword)
    
    if not tokens or not kw_tokens:
        return False
        
    # Find sequence of tokens matching the keyword
    kw_len = len(kw_tokens)
    for i in range(len(tokens) - kw_len + 1):
        if tokens[i:i+kw_len] == kw_tokens:
            # We found the keyword occurrence, now check the 3 tokens preceding it
            start_check = max(0, i - 3)
            preceding_window = tokens[start_check:i]
            # If any negation word is in the preceding window, return True
            for neg in NEGATION_WORDS:
                if neg in preceding_window:
                    return True
    return False

def get_token_distance(sentence: str, term1: str, term2: str) -> int:
    """Calculates the minimum distance in tokens between term1 and term2 in a sentence.
    
    Returns 999 if either term is not found.
    """
    tokens = tokenize(sentence)
    t1_tokens = tokenize(term1)
    t2_tokens = tokenize(term2)
    
    if not tokens or not t1_tokens or not t2_tokens:
        return 999
        
    # Find all start indices for term1 and term2
    t1_indices = []
    t2_indices = []
    
    t1_len = len(t1_tokens)
    t2_len = len(t2_tokens)
    
    for i in range(len(tokens) - t1_len + 1):
        if tokens[i:i+t1_len] == t1_tokens:
            t1_indices.append(i)
            
    for i in range(len(tokens) - t2_len + 1):
        if tokens[i:i+t2_len] == t2_tokens:
            t2_indices.append(i)
            
    if not t1_indices or not t2_indices:
        return 999
        
    # Calculate minimum distance
    min_dist = 999
    for idx1 in t1_indices:
        for idx2 in t2_indices:
            # Distance is number of tokens between the closest parts of the terms
            if idx1 < idx2:
                dist = idx2 - (idx1 + t1_len)
            else:
                dist = idx1 - (idx2 + t2_len)
            if dist < min_dist:
                min_dist = max(0, dist)
                
    return min_dist
