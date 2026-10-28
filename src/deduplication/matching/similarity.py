"""String and numeric similarity functions using RapidFuzz."""

from __future__ import annotations

from typing import Optional
from rapidfuzz import distance, fuzz


def string_ratio(a: Optional[str], b: Optional[str]) -> float:
    """Standard Levenshtein ratio scaled between 0.0 and 1.0."""
    if not a or not b:
        return 0.0
    return fuzz.ratio(a, b) / 100.0


def token_sort_ratio(a: Optional[str], b: Optional[str]) -> float:
    """
    Token sort ratio scaled between 0.0 and 1.0.
    Splits into tokens, sorts them alphabetically, and computes ratio.
    Excellent for out-of-order words (e.g. 'Sony Headphones' vs 'Headphones Sony').
    """
    if not a or not b:
        return 0.0
    return fuzz.token_sort_ratio(a, b) / 100.0


def jaro_winkler_similarity(a: Optional[str], b: Optional[str]) -> float:
    """
    Jaro-Winkler similarity scaled between 0.0 and 1.0.
    Gives higher weight to prefixes; ideal for person names and short tokens.
    """
    if not a or not b:
        return 0.0
    return distance.JaroWinkler.similarity(a, b)


def numeric_within_percentage(
    val_a: Optional[float], val_b: Optional[float], tolerance: float = 0.15
) -> bool:
    """Check if two positive numbers are within a specified percentage of each other."""
    if val_a is None or val_b is None:
        return False
    if val_a <= 0.0 or val_b <= 0.0:
        return val_a == val_b
    diff = abs(val_a - val_b)
    average = (val_a + val_b) / 2.0
    return (diff / average) <= tolerance

