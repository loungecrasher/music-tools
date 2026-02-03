"""
Date parsing and formatting utilities.

This module provides utilities for parsing, validating, and formatting dates
in various formats commonly found in music metadata and APIs.
"""

import logging
from datetime import datetime, date
from typing import Optional, Union, Tuple

logger = logging.getLogger(__name__)


def parse_date(
    date_str: str,
    formats: Optional[list[str]] = None
) -> Tuple[bool, Optional[datetime], str]:
    """
    Parse a date string using multiple format attempts.

    Tries to parse a date string using a list of common formats. Returns
    the first successful parse or an error if none match.

    Args:
        date_str: Date string to parse
        formats: List of datetime format strings to try (default: common formats)

    Returns:
        Tuple of (success, datetime_object, error_message)

    Example:
        >>> success, dt, error = parse_date('2024-03-15')
        >>> if success:
        ...     print(f"Parsed: {dt.strftime('%Y-%m-%d')}")
    """
    if not date_str:
        return False, None, "Date string is empty"

    # Default formats to try
    if formats is None:
        formats = [
            '%Y-%m-%d',           # 2024-03-15
            '%Y/%m/%d',           # 2024/03/15
            '%d-%m-%Y',           # 15-03-2024
            '%d/%m/%Y',           # 15/03/2024
            '%Y-%m-%d %H:%M:%S',  # 2024-03-15 14:30:00
            '%Y-%m-%dT%H:%M:%S',  # 2024-03-15T14:30:00 (ISO 8601)
            '%Y-%m-%dT%H:%M:%SZ', # 2024-03-15T14:30:00Z (ISO 8601 UTC)
            '%Y',                 # 2024 (year only)
            '%Y-%m',              # 2024-03 (year-month)
            '%B %d, %Y',          # March 15, 2024
            '%b %d, %Y',          # Mar 15, 2024
            '%d %B %Y',           # 15 March 2024
            '%d %b %Y',           # 15 Mar 2024
        ]

    # Try each format
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return True, dt, ""
        except ValueError:
            continue

    # Try ISO format parsing (handles fractional seconds)
    try:
        # Remove 'Z' and replace with '+00:00' for UTC
        normalized = date_str.strip().replace('Z', '+00:00')
        dt = datetime.fromisoformat(normalized)
        return True, dt, ""
    except ValueError:
        pass

    error_msg = f"Could not parse date: {date_str}"
    logger.warning(error_msg)
    return False, None, error_msg


def format_date(
    date_obj: Union[datetime, date, str],
    format_str: str = '%Y-%m-%d'
) -> str:
    """
    Format a date object or string to a specific format.

    Args:
        date_obj: Date object, datetime object, or date string to format
        format_str: Output format string (default: '%Y-%m-%d')

    Returns:
        Formatted date string

    Example:
        >>> format_date(datetime(2024, 3, 15))
        '2024-03-15'
        >>> format_date('2024-03-15', '%B %d, %Y')
        'March 15, 2024'
    """
    if isinstance(date_obj, str):
        # Try to parse it first
        success, dt, error = parse_date(date_obj)
        if not success:
            logger.warning(f"Could not parse date for formatting: {date_obj}")
            return date_obj  # Return original if can't parse
        date_obj = dt

    try:
        return date_obj.strftime(format_str)
    except Exception as e:
        logger.warning(f"Error formatting date: {e}")
        return str(date_obj)


def normalize_date(
    date_str: str,
    output_format: str = '%Y-%m-%d'
) -> str:
    """
    Normalize a date string to a consistent format.

    Handles various input formats and normalizes to a standard format.
    Special handling for partial dates (year-only, year-month).

    Args:
        date_str: Date string in various formats
        output_format: Desired output format (default: '%Y-%m-%d')

    Returns:
        Normalized date string, or original if parsing fails

    Example:
        >>> normalize_date('2024')
        '2024-01-01'
        >>> normalize_date('2024-03')
        '2024-03-01'
        >>> normalize_date('15/03/2024')
        '2024-03-15'
    """
    if not date_str:
        return date_str

    date_str = date_str.strip()

    # Handle year-only (4 digits)
    if len(date_str) == 4 and date_str.isdigit():
        try:
            year = int(date_str)
            if 1900 <= year <= 2100:
                return f"{date_str}-01-01"
        except ValueError:
            pass

    # Handle year-month (7 characters: YYYY-MM or YYYY/MM)
    if len(date_str) == 7 and (date_str[4] in ['-', '/']):
        try:
            parts = date_str.replace('/', '-').split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                year = int(parts[0])
                month = int(parts[1])
                if 1900 <= year <= 2100 and 1 <= month <= 12:
                    return f"{parts[0]}-{parts[1]}-01"
        except ValueError:
            pass

    # Try to parse with standard formats
    success, dt, error = parse_date(date_str)
    if success:
        return format_date(dt, output_format)

    # If all else fails, return original
    logger.debug(f"Could not normalize date: {date_str}")
    return date_str


def get_year_from_date(date_str: str) -> Optional[int]:
    """
    Extract year from a date string.

    Args:
        date_str: Date string in various formats

    Returns:
        Year as integer, or None if extraction fails

    Example:
        >>> get_year_from_date('2024-03-15')
        2024
        >>> get_year_from_date('March 15, 2024')
        2024
    """
    if not date_str:
        return None

    # Try to parse the date
    success, dt, error = parse_date(date_str)
    if success:
        return dt.year

    # If parsing fails, try to extract 4-digit year
    import re
    match = re.search(r'\b(19|20)\d{2}\b', date_str)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            pass

    return None


def is_valid_date(
    date_str: str,
    min_year: int = 1900,
    max_year: Optional[int] = None
) -> bool:
    """
    Check if a date string is valid and within a reasonable range.

    Args:
        date_str: Date string to validate
        min_year: Minimum allowed year (default: 1900)
        max_year: Maximum allowed year (default: current year + 1)

    Returns:
        True if the date is valid and in range, False otherwise

    Example:
        >>> is_valid_date('2024-03-15')
        True
        >>> is_valid_date('1800-01-01')
        False
        >>> is_valid_date('invalid')
        False
    """
    if not date_str:
        return False

    # Set default max year
    if max_year is None:
        max_year = datetime.now().year + 1

    # Try to parse the date
    success, dt, error = parse_date(date_str)
    if not success:
        return False

    # Check year range
    if dt.year < min_year or dt.year > max_year:
        logger.warning(f"Date year {dt.year} outside valid range {min_year}-{max_year}")
        return False

    return True


def format_duration(seconds: Union[int, float]) -> str:
    """
    Format duration in seconds to MM:SS or HH:MM:SS format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(125)
        '2:05'
        >>> format_duration(3725)
        '1:02:05'
        >>> format_duration(45.7)
        '0:45'
    """
    if seconds < 0:
        return "0:00"

    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse a duration string to seconds.

    Supports formats like:
    - MM:SS (e.g., "3:45" = 225 seconds)
    - HH:MM:SS (e.g., "1:23:45" = 5025 seconds)
    - Seconds only (e.g., "180" = 180 seconds)

    Args:
        duration_str: Duration string to parse

    Returns:
        Duration in seconds, or None if parsing fails

    Example:
        >>> parse_duration('3:45')
        225
        >>> parse_duration('1:23:45')
        5025
        >>> parse_duration('180')
        180
    """
    if not duration_str:
        return None

    try:
        # Try to parse as plain number (seconds)
        return int(float(duration_str))
    except ValueError:
        pass

    # Try to parse as time format
    parts = duration_str.split(':')

    try:
        if len(parts) == 2:
            # MM:SS format
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:
            # HH:MM:SS format
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        pass

    logger.warning(f"Could not parse duration: {duration_str}")
    return None


def get_relative_time(dt: datetime) -> str:
    """
    Get a human-readable relative time string.

    Args:
        dt: Datetime to compare to now

    Returns:
        Relative time string (e.g., "2 hours ago", "in 3 days")

    Example:
        >>> from datetime import timedelta
        >>> past = datetime.now() - timedelta(hours=2)
        >>> get_relative_time(past)
        '2 hours ago'
    """
    now = datetime.now()

    # Handle timezone-aware datetimes
    if dt.tzinfo is not None and now.tzinfo is None:
        from datetime import timezone
        now = now.replace(tzinfo=timezone.utc)
    elif dt.tzinfo is None and now.tzinfo is not None:
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 0:
        # Future time
        seconds = abs(seconds)
        suffix = "from now"
    else:
        suffix = "ago"

    # Calculate time units
    intervals = [
        ('year', 31536000),    # 365 days
        ('month', 2592000),    # 30 days
        ('week', 604800),      # 7 days
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1),
    ]

    for name, count in intervals:
        value = int(seconds // count)
        if value > 0:
            plural = 's' if value > 1 else ''
            return f"{value} {name}{plural} {suffix}"

    return "just now"


def is_recent_date(
    date_obj: Union[datetime, date, str],
    days: int = 30
) -> bool:
    """
    Check if a date is within the last N days.

    Args:
        date_obj: Date object, datetime, or date string
        days: Number of days to consider as recent (default: 30)

    Returns:
        True if the date is within the last N days, False otherwise

    Example:
        >>> is_recent_date('2024-03-15', days=30)
        True  # if today is within 30 days of 2024-03-15
    """
    # Parse if string
    if isinstance(date_obj, str):
        success, dt, error = parse_date(date_obj)
        if not success:
            return False
        date_obj = dt

    # Convert to datetime if date
    if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
        date_obj = datetime.combine(date_obj, datetime.min.time())

    # Compare
    now = datetime.now()
    if date_obj.tzinfo is not None and now.tzinfo is None:
        from datetime import timezone
        now = now.replace(tzinfo=timezone.utc)

    delta = now - date_obj
    return 0 <= delta.days <= days
