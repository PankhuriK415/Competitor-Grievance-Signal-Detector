from datetime import datetime, timezone
import re
from utils.logger import logger

def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parses an ISO 8601 timestamp string into a timezone-aware datetime object.
    
    If the format is invalid, falls back to the current datetime in UTC.
    """
    if not timestamp_str:
        return datetime.now(timezone.utc)
        
    # Replace suffix 'Z' with +00:00 for compatibility with older Python fromisoformat
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'
        
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError as e:
        logger.warning(f"Could not parse timestamp '{timestamp_str}' as ISO format: {e}. Using current time.")
        return datetime.now(timezone.utc)

def get_days_ago(timestamp_str: str) -> float:
    """Calculates the age of a timestamp in days compared to the current system time."""
    dt = parse_iso_timestamp(timestamp_str)
    now = datetime.now(dt.tzinfo or timezone.utc)
    diff = now - dt
    # Keep it non-negative
    return max(0.0, diff.total_seconds() / (24 * 3600))

def get_current_iso() -> str:
    """Returns the current UTC time formatted as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
