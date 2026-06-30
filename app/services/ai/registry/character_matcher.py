"""
Character Matching and Record Reuse Engine.
"""

import logging
from typing import List, Tuple, Optional
from app.models.character import Character
from app.services.ai.registry.character_normalizer import CharacterNormalizer

logger = logging.getLogger("ai_studio")


class CharacterMatcher:
    """Matches candidate names against existing database Character records to reuse profiles."""

    def __init__(self, normalizer: CharacterNormalizer) -> None:
        self.normalizer = normalizer

    def find_best_match(
        self, candidate_name: str, existing_characters: List[Character]
    ) -> Tuple[Optional[Character], float]:
        """Find the best matching Character model and calculate match confidence.

        Args:
            candidate_name: Name of the candidate character.
            existing_characters: List of already registered Character records in DB.

        Returns:
            Tuple of (Best Matching Character or None, Confidence Score from 0.0 to 1.0).
        """
        candidate_canonical = self.normalizer.resolve_canonical(candidate_name)
        candidate_lower = candidate_canonical.lower()

        best_match = None
        best_score = 0.0

        for char in existing_characters:
            char_canonical = self.normalizer.resolve_canonical(char.name)
            char_lower = char_canonical.lower()

            # 1. Exact Match on canonicalized name
            if candidate_lower == char_lower:
                return char, 1.0

            # 2. Check within aliases
            if char.aliases:
                # Split aliases by comma or semicolon
                aliases_list = [
                    self.normalizer.resolve_canonical(a).lower()
                    for a in char.aliases.replace(";", ",").split(",")
                    if a.strip()
                ]
                if candidate_lower in aliases_list:
                    return char, 1.0

            # 3. Substring matching / word subset match
            candidate_words = set(candidate_lower.split())
            char_words = set(char_lower.split())

            # Intersection of words
            intersection = candidate_words.intersection(char_words)
            if intersection:
                # Calculate overlap ratio
                overlap = len(intersection) / max(len(candidate_words), len(char_words))
                score = min(overlap * 0.8, 0.8)
                if score > best_score:
                    best_score = score
                    best_match = char

        return best_match, best_score
