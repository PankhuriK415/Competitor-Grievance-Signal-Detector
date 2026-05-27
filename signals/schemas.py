from typing import TypedDict, List, Optional

class IngestedDocument(TypedDict):
    """Schema for parsed raw ingestion document."""
    text: str
    source: str
    url: str
    timestamp: str
    author: str
    company: str  # The company name of the reviewer or target company, if extractable

class CompetitorMatch(TypedDict):
    """Result of competitor detection."""
    competitor: str
    matched_phrase: str

class ComplaintMatch(TypedDict):
    """Result of individual keyword/context complaint match."""
    pain_point: str  # cost, speed, fairness, experience, reliability
    matched_keyword: str
    sentence: str
    distance: int  # Token distance from competitor mention
    negated: bool

class SignalRecord(TypedDict):
    """The final structured signal output schema from Step 6."""
    company: str
    signal_type: str  # "competitor_grievance"
    source_url: str
    matched_keywords: List[str]
    pain_point: str  # E.g. "speed", or "cost"
    signal_score: int
    detected_at: str  # ISO timestamp
    reason: str
