import hashlib
import re
from typing import List, Dict, Any, Set
from utils.logger import logger
from utils.date_utils import parse_iso_timestamp
from signals.schemas import IngestedDocument

def generate_document_hash(text: str, url: str) -> str:
    """Generates an MD5 hash from text and url to serve as a unique fingerprint."""
    hasher = hashlib.md5()
    # Normalize text to avoid whitespace differences affecting the hash
    normalized_text = "".join(text.split()).lower()
    hasher.update(normalized_text.encode("utf-8"))
    if url:
        hasher.update(url.encode("utf-8"))
    return hasher.hexdigest()

def extract_company_from_text(text: str) -> str:
    """Attempts to extract a company name from the text using basic NLP heuristics."""
    # Look for patterns like "our team at [Company]", "we at [Company]", "working at [Company]"
    patterns = [
        r"\b(?:our team|we|us|recruiting|hiring)\s+at\s+([A-Z][a-zA-Z0-9_\s]{1,19})\b",
        r"\b(?:work|working)\s+at\s+([A-Z][a-zA-Z0-9_\s]{1,19})\b",
        r"\b(?:my company|our company),\s+([A-Z][a-zA-Z0-9_\s]{1,19})\b"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            # Clean up trailing words like "uses", "use", "has", "switched"
            clean_match = re.split(r'\s+(?:uses|used|use|has|had|switched|is|was|are|to|for|with|and|but)\b', extracted, flags=re.IGNORECASE)
            result = clean_match[0].strip()
            if len(result) > 2: # Keep only realistic length names
                return result
                
    return "Unknown"

def parse_and_normalize(raw_documents: List[Dict[str, Any]]) -> List[IngestedDocument]:
    """Parses raw document feeds, normalizes their schemas, and filters out duplicates."""
    seen_hashes: Set[str] = set()
    normalized_docs: List[IngestedDocument] = []
    
    for raw in raw_documents:
        text = raw.get("text", "").strip()
        source = raw.get("source", "").lower()
        url = raw.get("url", "").strip()
        timestamp = raw.get("timestamp", "").strip()
        author = raw.get("author", "anonymous").strip()
        metadata_company = raw.get("company", "Unknown").strip()
        
        if not text:
            logger.warning(f"Skipping empty document from source: {source}")
            continue
            
        doc_hash = generate_document_hash(text, url)
        if doc_hash in seen_hashes:
            logger.info(f"Filtering duplicate document from: {url or source}")
            continue
            
        seen_hashes.add(doc_hash)
        
        # Clean and normalize whitespace
        clean_text = re.sub(r'\s+', ' ', text).strip()
        
        # Standardize timestamp (ensures it is a valid format)
        dt = parse_iso_timestamp(timestamp)
        iso_timestamp = dt.isoformat()
        
        # Determine company name: use metadata if valid, otherwise try extracting, otherwise fallback
        company = metadata_company
        if not company or company == "Unknown":
            company = extract_company_from_text(clean_text)
            
        normalized_docs.append({
            "text": clean_text,
            "source": source,
            "url": url,
            "timestamp": iso_timestamp,
            "author": author,
            "company": company
        })
        
    logger.info(f"Normalized {len(normalized_docs)} documents (Deduplicated {len(raw_documents) - len(normalized_docs)} documents).")
    return normalized_docs
