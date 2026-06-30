"""
Character Name Normalizer.
"""

import re
from typing import Dict, List, Optional


class CharacterNormalizer:
    """Handles string normalization, casing, alias resolution, and canonical naming."""

    def __init__(self, alias_mappings: Optional[Dict[str, str]] = None) -> None:
        """Initialize the normalizer.

        Args:
            alias_mappings: Dictionary mapping alternative names/aliases to canonical name.
        """
        # Map lowercased alias to canonical capitalized name
        self.alias_mappings = {}
        if alias_mappings:
            for k, v in alias_mappings.items():
                self.alias_mappings[self.normalize_basic(k).lower()] = self.normalize_basic(v)

    def normalize_basic(self, name: str) -> str:
        """Strip whitespace, normalize case, and sanitize special characters.

        Args:
            name: Raw character name.

        Returns:
            Basic normalized name string (capitalized).
        """
        if not name:
            return ""
        # 1. Strip whitespace
        cleaned = name.strip()
        # 2. Case normalization (Title Case)
        cleaned = cleaned.title()

        # 3. Clean multiple internal whitespaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    def resolve_canonical(self, name: str) -> str:
        """Resolve a name to its canonical form using alias mappings.

        Args:
            name: Raw or partially normalized character name.

        Returns:
            Canonical name.
        """
        basic = self.normalize_basic(name)
        lookup = basic.lower()
        if lookup in self.alias_mappings:
            return self.alias_mappings[lookup]
        return basic

    def add_alias(self, alias_name: str, canonical_name: str) -> None:
        """Register a new alias mapping.

        Args:
            alias_name: Alternative name.
            canonical_name: Canonical target name.
        """
        norm_alias = self.normalize_basic(alias_name).lower()
        norm_canonical = self.normalize_basic(canonical_name)
        if norm_alias and norm_canonical:
            self.alias_mappings[norm_alias] = norm_canonical

    def detect_duplicates(self, names: List[str]) -> List[str]:
        """Detect and return list of unique canonical names from a list of raw names.

        Args:
            names: List of raw character names.

        Returns:
            List of unique canonicalized names.
        """
        unique_canonical = set()
        for name in names:
            canonical = self.resolve_canonical(name)
            if canonical:
                unique_canonical.add(canonical)
        return sorted(list(unique_canonical))

    def hook_multilingual_normalization(self, name: str, locale: str = "en") -> str:
        """Future hook for multilingual normalization.

        Args:
            name: Character name.
            locale: Language locale.

        Returns:
            Locale-specific normalized name.
        """
        return name
