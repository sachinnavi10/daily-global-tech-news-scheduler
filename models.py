"""News categories and basic article classification."""

import re
from typing import Optional

CATEGORY_KEYWORDS = {
    "Agentic AI": ("agentic ai", "ai agent", "ai agents", "autonomous agent"),
    "Quantum Computing": ("quantum computing", "quantum", "qubit"),
    "Cybersecurity": (
        "cybersecurity",
        "cyber attack",
        "ransomware",
        "data breach",
        "security vulnerability",
    ),
    "AI": (
        "artificial intelligence",
        "generative ai",
        "machine learning",
        "large language model",
        "llm",
        "ai",
    ),
    "Cloud": ("cloud computing", "cloud", "aws", "azure", "google cloud"),
    "Developer Tools": (
        "developer tools",
        "ide",
        "code editor",
        "github copilot",
        "visual studio code",
        "compiler",
    ),
    "Programming": (
        "programming language",
        "programming",
        "python",
        "javascript",
        "rust",
        "typescript",
    ),
    "Startups": ("startup", "start-up", "venture capital", "funding", "ipo"),
    "Technology Companies": (
        "apple",
        "microsoft",
        "google",
        "amazon",
        "meta",
        "nvidia",
        "openai",
    ),
}


def categorize_news(title: Optional[str], description: Optional[str] = None) -> str:
    """Choose the first matching category using the title and description."""
    text = f"{title or ''} {description or ''}".casefold()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text):
                return category

    return "Other Technology"
