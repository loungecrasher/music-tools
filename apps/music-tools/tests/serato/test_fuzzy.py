"""Tests for the unified fuzzy matching utilities in music_tools_common."""

import sys
from pathlib import Path

import pytest

# Add packages/common to sys.path
common_root = Path(__file__).parent.parent.parent.parent.parent / "packages" / "common"
sys.path.insert(0, str(common_root))

from music_tools_common.utils.fuzzy import find_best_match, similarity_score


class TestFindBestMatch:
    """Tests for the find_best_match function."""

    def test_find_best_match_exact(self):
        """An exact match scores 100."""
        candidates = {
            "massive attack teardrop": {"id": 1, "name": "Teardrop"},
            "portishead glory box": {"id": 2, "name": "Glory Box"},
        }
        best, matches, score = find_best_match("massive attack teardrop", candidates)
        assert best is not None
        assert best["id"] == 1
        assert score == 100

    def test_find_best_match_fuzzy(self):
        """A close but imperfect match is returned above threshold."""
        candidates = {
            "massive attack teardrop": {"id": 1},
            "portishead glory box": {"id": 2},
            "boards of canada roygbiv": {"id": 3},
        }
        # Slightly misspelled query
        best, matches, score = find_best_match("masive atack teardrop", candidates, threshold=60)
        assert best is not None
        assert best["id"] == 1
        assert score >= 60

    def test_find_best_match_below_threshold(self):
        """Returns (None, [], 0) when no candidate meets the threshold."""
        candidates = {
            "massive attack teardrop": {"id": 1},
            "portishead glory box": {"id": 2},
        }
        best, matches, score = find_best_match(
            "completely unrelated query xyz", candidates, threshold=90
        )
        assert best is None
        assert matches == []
        assert score == 0

    def test_find_best_match_empty_candidates(self):
        """Empty candidates dict returns (None, [], 0)."""
        best, matches, score = find_best_match("any query", {})
        assert best is None
        assert matches == []
        assert score == 0

    def test_find_best_match_respects_limit(self):
        """The limit parameter caps the number of returned matches."""
        candidates = {f"artist song {i}": {"id": i} for i in range(20)}
        best, matches, score = find_best_match("artist song", candidates, threshold=30, limit=3)
        assert len(matches) <= 3


class TestSimilarityScore:
    """Tests for the similarity_score function."""

    def test_similarity_score_identical(self):
        """Identical strings return a score of 100."""
        assert similarity_score("hello world", "hello world") == 100

    def test_similarity_score_case_insensitive(self):
        """Score is case-insensitive (both lowered internally)."""
        assert similarity_score("Hello World", "hello world") == 100

    def test_similarity_score_different(self):
        """Totally different strings return a low score."""
        score = similarity_score("abcdef", "zyxwvu")
        assert score < 30

    def test_similarity_score_partial(self):
        """Partially overlapping strings return a mid-range score."""
        score = similarity_score("massive attack", "massive attack teardrop")
        assert 50 < score < 100

    def test_similarity_score_empty_strings(self):
        """Two empty strings return 100 per rapidfuzz token_sort_ratio."""
        score = similarity_score("", "")
        assert score == 100
