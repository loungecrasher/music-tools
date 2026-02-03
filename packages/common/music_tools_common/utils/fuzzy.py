"""
Unified fuzzy matching utilities for Music Tools.
Consolidates fuzzy matching logic used by library vetter and Serato tools.
"""
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process


def find_best_match(
    query: str,
    candidates: Dict[str, Any],
    threshold: int = 75,
    limit: int = 5,
) -> Tuple[Optional[Any], List[Tuple[Any, int]], int]:
    """Find best matching item using fuzzy matching.

    Args:
        query: Search term (e.g. "artist title")
        candidates: Dict mapping search strings to objects
        threshold: Minimum match score (0-100)
        limit: Maximum number of matches to return

    Returns:
        Tuple of (best_match_object, [(object, score), ...], best_score).
        Returns (None, [], 0) when no match meets the threshold.
    """
    if not candidates:
        return None, [], 0

    candidate_keys = list(candidates.keys())

    matches = process.extract(
        query.lower(),
        candidate_keys,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
    )

    valid = [(candidates[m], int(s)) for m, s, _ in matches if s >= threshold]

    if not valid:
        return None, [], 0

    best_obj, best_score = valid[0]
    return best_obj, valid, best_score


def similarity_score(a: str, b: str) -> int:
    """Return token-sort-ratio similarity between two strings (0-100)."""
    return int(fuzz.token_sort_ratio(a.lower(), b.lower()))
