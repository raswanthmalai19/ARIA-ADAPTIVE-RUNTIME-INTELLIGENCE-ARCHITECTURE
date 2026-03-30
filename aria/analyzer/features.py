"""
ARIA Feature Extraction

Extracts lightweight features from queries for complexity classification.
All features are computed without any ML model — pure heuristics for speed.
"""

from __future__ import annotations

import re
import math
from dataclasses import dataclass, field


# ─────────────────────────────────────────────
# Domain keyword sets (compiled once at import)
# ─────────────────────────────────────────────

_REASONING_KEYWORDS = frozenset({
    "why", "how", "explain", "analyze", "compare", "contrast", "evaluate",
    "assess", "argue", "justify", "critique", "debate", "discuss",
    "implications", "consequences", "trade-offs", "tradeoffs", "pros and cons",
    "advantages", "disadvantages", "relationship", "cause", "effect",
    "difference", "similarities", "impact", "significance",
})

_CODE_KEYWORDS = frozenset({
    "code", "function", "class", "implement", "algorithm", "debug",
    "program", "script", "api", "database", "sql", "python", "javascript",
    "typescript", "rust", "java", "c++", "html", "css", "react", "flask",
    "django", "fastapi", "decorator", "async", "await", "lambda",
    "recursion", "loop", "array", "hashmap", "binary", "tree", "graph",
    "sort", "search", "regex", "json", "xml", "yaml", "docker",
    "kubernetes", "git", "terminal", "bash", "shell", "pip", "npm",
    "def ", "class ", "import ", "return ", "print(",
})

_MATH_KEYWORDS = frozenset({
    "calculate", "compute", "solve", "equation", "formula", "integral",
    "derivative", "matrix", "vector", "probability", "statistics",
    "theorem", "proof", "mathematical", "algebra", "geometry",
    "trigonometry", "calculus", "logarithm", "factorial", "permutation",
    "combination", "average", "median", "variance", "sigma",
})

_CREATIVE_KEYWORDS = frozenset({
    "write", "story", "poem", "creative", "imagine", "fiction",
    "essay", "narrative", "compose", "craft", "design", "invent",
    "brainstorm", "generate ideas", "song", "lyrics", "screenplay",
    "dialogue", "character", "plot", "metaphor", "describe",
})

_SIMPLE_PATTERNS = [
    re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay|yes|no|bye|goodbye)\b", re.IGNORECASE),
    re.compile(r"^what (is|are|was|were) (the |a |an )?\w+\??$", re.IGNORECASE),
    re.compile(r"^(who|when|where) (is|are|was|were) ", re.IGNORECASE),
    re.compile(r"^(define|meaning of) ", re.IGNORECASE),
    re.compile(r"^(translate|convert) ", re.IGNORECASE),
]

_COMPLEXITY_MARKERS = frozenset({
    "step by step", "step-by-step", "in detail", "detailed",
    "comprehensive", "thorough", "exhaustive", "elaborate",
    "with examples", "production-ready", "enterprise",
    "scalable", "optimized", "best practices",
    "architecture", "design pattern", "system design",
    "from scratch", "full implementation",
})

_MULTI_PART_MARKERS = [
    re.compile(r"\b(also|additionally|furthermore|moreover|then|next|finally)\b", re.IGNORECASE),
    re.compile(r"\b(first|second|third|1\.|2\.|3\.)\b", re.IGNORECASE),
    re.compile(r"\band\b.*\band\b", re.IGNORECASE),
]


# ─────────────────────────────────────────────
# Feature Dataclass
# ─────────────────────────────────────────────

@dataclass
class QueryFeatures:
    """Extracted features from a query string."""
    # Lexical features
    char_count: int = 0
    word_count: int = 0
    token_estimate: int = 0           # rough: words * 1.3
    sentence_count: int = 0
    avg_word_length: float = 0.0
    vocabulary_richness: float = 0.0  # unique_words / total_words

    # Structural features
    has_question_mark: bool = False
    has_code_block: bool = False
    has_list_structure: bool = False
    has_multiple_sentences: bool = False
    is_greeting: bool = False

    # Domain keyword matches
    reasoning_keyword_count: int = 0
    code_keyword_count: int = 0
    math_keyword_count: int = 0
    creative_keyword_count: int = 0
    complexity_marker_count: int = 0
    multi_part_count: int = 0

    # Derived scores
    domain_score: float = 0.0
    structural_complexity: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "char_count": self.char_count,
            "word_count": self.word_count,
            "token_estimate": self.token_estimate,
            "sentence_count": self.sentence_count,
            "avg_word_length": self.avg_word_length,
            "vocabulary_richness": self.vocabulary_richness,
            "has_question_mark": self.has_question_mark,
            "has_code_block": self.has_code_block,
            "has_list_structure": self.has_list_structure,
            "is_greeting": self.is_greeting,
            "reasoning_keywords": self.reasoning_keyword_count,
            "code_keywords": self.code_keyword_count,
            "math_keywords": self.math_keyword_count,
            "creative_keywords": self.creative_keyword_count,
            "complexity_markers": self.complexity_marker_count,
            "multi_part_count": self.multi_part_count,
        }


# ─────────────────────────────────────────────
# Feature Extractor
# ─────────────────────────────────────────────

def extract_features(query: str) -> QueryFeatures:
    """
    Extract all classification features from a query string.

    This is the core feature extraction pipeline. It runs in <1ms
    and produces a rich feature set for the classifier.
    """
    query_stripped = query.strip()
    query_lower = query_stripped.lower()

    if not query_stripped:
        return QueryFeatures()

    features = QueryFeatures()

    # ── Lexical Features ──
    features.char_count = len(query_stripped)

    words = query_stripped.split()
    features.word_count = len(words)
    features.token_estimate = int(len(words) * 1.3)

    # Sentence splitting (approximate)
    sentences = re.split(r'[.!?]+', query_stripped)
    features.sentence_count = len([s for s in sentences if s.strip()])
    features.has_multiple_sentences = features.sentence_count > 1

    if words:
        word_lengths = [len(w) for w in words]
        features.avg_word_length = sum(word_lengths) / len(word_lengths)

        unique_words = set(w.lower() for w in words)
        features.vocabulary_richness = len(unique_words) / len(words)

    # ── Structural Features ──
    features.has_question_mark = "?" in query_stripped
    features.has_code_block = "```" in query_stripped or "def " in query_stripped
    features.has_list_structure = bool(
        re.search(r'(^|\n)\s*[-*•]\s', query_stripped) or
        re.search(r'(^|\n)\s*\d+[.)]\s', query_stripped)
    )

    # Greeting detection
    features.is_greeting = any(
        pattern.search(query_stripped) for pattern in _SIMPLE_PATTERNS
    )

    # ── Domain Keyword Matching ──
    query_words_set = set(query_lower.split())

    features.reasoning_keyword_count = len(query_words_set & _REASONING_KEYWORDS)
    features.code_keyword_count = len(query_words_set & _CODE_KEYWORDS)
    # Also check for multi-word code patterns in the full string
    for kw in _CODE_KEYWORDS:
        if " " in kw or "(" in kw:
            if kw in query_lower:
                features.code_keyword_count += 1

    features.math_keyword_count = len(query_words_set & _MATH_KEYWORDS)
    features.creative_keyword_count = len(query_words_set & _CREATIVE_KEYWORDS)

    # Complexity markers (multi-word, must check in full string)
    for marker in _COMPLEXITY_MARKERS:
        if marker in query_lower:
            features.complexity_marker_count += 1

    # Multi-part request detection
    for pattern in _MULTI_PART_MARKERS:
        if pattern.search(query_stripped):
            features.multi_part_count += 1

    # ── Derived Scores ──
    # Domain score: how domain-specific/technical is the query
    total_domain_hits = (
        features.reasoning_keyword_count +
        features.code_keyword_count +
        features.math_keyword_count +
        features.creative_keyword_count
    )
    features.domain_score = min(total_domain_hits / max(features.word_count * 0.3, 1), 1.0)

    # Structural complexity: combines length, structure, and depth signals
    length_score = min(features.word_count / 50.0, 1.0)  # 50+ words = max
    structure_score = (
        (0.2 if features.has_multiple_sentences else 0.0) +
        (0.3 if features.has_code_block else 0.0) +
        (0.2 if features.has_list_structure else 0.0) +
        (0.1 * min(features.multi_part_count, 3) / 3.0) +
        (0.2 * min(features.complexity_marker_count, 3) / 3.0)
    )
    features.structural_complexity = min(
        0.4 * length_score + 0.6 * structure_score, 1.0
    )

    return features
