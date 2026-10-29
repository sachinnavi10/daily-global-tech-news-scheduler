"""Select important articles and build a readable daily briefing."""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from database import save_daily_briefing

CATEGORY_SCORES = {
    "Agentic AI": 6,
    "Quantum Computing": 6,
    "AI": 5,
    "Cybersecurity": 5,
    "Cloud": 4,
    "Developer Tools": 4,
    "Programming": 3,
    "Startups": 3,
    "Technology Companies": 2,
    "Other Technology": 0,
}

IMPORTANT_TERMS = (
    "announces",
    "announced",
    "launches",
    "launched",
    "breakthrough",
    "security breach",
    "ransomware",
    "funding",
    "acquisition",
    "outage",
    "vulnerability",
)

BRIEFING_SECTIONS = {
    "AI": ("AI",),
    "AGENTIC AI": ("Agentic AI",),
    "QUANTUM COMPUTING": ("Quantum Computing",),
    "CLOUD & SOFTWARE": ("Cloud", "Programming", "Developer Tools"),
    "CYBERSECURITY": ("Cybersecurity",),
    "TECHNOLOGY BUSINESS": ("Startups", "Technology Companies", "Other Technology"),
}

WHY_IT_MATTERS = {
    "Agentic AI": "It may change how software handles multi-step tasks and uses tools.",
    "Quantum Computing": "It advances research into computing methods beyond classical systems.",
    "AI": "It can affect products, research, and the way people work with software.",
    "Cybersecurity": "It highlights risks that organizations may need to prevent or respond to.",
    "Cloud": "It can influence how teams build, deploy, and operate software services.",
    "Developer Tools": "It may change how developers write, test, or maintain software.",
    "Programming": "It provides useful context for choosing and using development technologies.",
    "Startups": "It signals changes in technology investment, products, or competition.",
    "Technology Companies": "It may affect products and services used by people and businesses.",
    "Other Technology": "It adds context to the wider technology landscape.",
}

LEARNING_TOPICS = {
    "Agentic AI": "how AI agents plan tasks and use tools",
    "Quantum Computing": "qubits and the basics of quantum circuits",
    "AI": "how machine-learning models are evaluated",
    "Cybersecurity": "basic threat modeling and incident response",
    "Cloud": "cloud architecture and infrastructure basics",
    "Developer Tools": "testing and debugging with modern developer tools",
    "Programming": "the programming language or tool mentioned in the story",
    "Startups": "how technology startups validate products and markets",
    "Technology Companies": "how large technology companies build platform ecosystems",
    "Other Technology": "how to evaluate a new technology trend",
}

CAREER_SKILLS = {
    "Agentic AI": ("Python", "API integration", "AI agent evaluation"),
    "Quantum Computing": ("linear algebra", "quantum circuits", "Qiskit"),
    "AI": ("Python", "machine-learning fundamentals", "model evaluation"),
    "Cybersecurity": ("security fundamentals", "threat modeling", "incident response"),
    "Cloud": ("cloud platforms", "deployment", "infrastructure basics"),
    "Developer Tools": ("Git", "automated testing", "developer workflows"),
    "Programming": ("programming fundamentals", "debugging", "code review"),
    "Startups": ("product analysis", "data literacy", "business communication"),
    "Technology Companies": ("system design", "product thinking", "data literacy"),
    "Other Technology": ("research", "technical communication"),
}

MAX_ARTICLES_PER_CATEGORY = 3


def _as_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def calculate_importance_score(
    article: dict[str, Any], now: Optional[datetime] = None
) -> int:
    """Score an article using topic, recency, and high-impact terms."""
    score = CATEGORY_SCORES.get(article.get("category"), 0)
    current_time = _as_utc(now) if now is not None else datetime.now(timezone.utc)
    published_at = _as_utc(article.get("published_at"))

    if published_at is not None:
        age = current_time - published_at
        if timedelta(0) <= age <= timedelta(days=1):
            score += 2
        elif timedelta(0) <= age <= timedelta(days=3):
            score += 1

    article_text = (
        f"{article.get('title') or ''} {article.get('description') or ''}"
    ).casefold()
    score += sum(term in article_text for term in IMPORTANT_TERMS)
    return score


def select_top_news(
    news_documents: list[dict[str, Any]],
    limit: int = 18,
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Rank stories and keep the result varied across news categories."""
    if limit <= 0:
        return []

    current_time = _as_utc(now) if now is not None else datetime.now(timezone.utc)
    unique_articles = []
    seen_urls = set()

    for article in news_documents:
        url = article.get("url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        published_at = _as_utc(article.get("published_at"))
        if published_at is not None and current_time - published_at > timedelta(days=7):
            continue
        unique_articles.append(article)

    ranked_articles = sorted(
        unique_articles,
        key=lambda article: (
            calculate_importance_score(article, current_time),
            _as_utc(article.get("published_at"))
            or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    selected_articles = []
    category_counts = {}
    for article in ranked_articles:
        category = article.get("category", "Other Technology")
        if category_counts.get(category, 0) >= MAX_ARTICLES_PER_CATEGORY:
            continue

        selected_articles.append(article)
        category_counts[category] = category_counts.get(category, 0) + 1
        if len(selected_articles) >= limit:
            break

    return selected_articles


def _make_briefing_item(article: dict[str, Any], now: datetime) -> dict[str, Any]:
    category = article.get("category", "Other Technology")
    description = article.get("description")

    return {
        "title": article.get("title", "Untitled article"),
        "summary": description or "The source did not provide a description.",
        "why_it_matters": WHY_IT_MATTERS.get(
            category, WHY_IT_MATTERS["Other Technology"]
        ),
        "source": article.get("source", "Unknown"),
        "url": article.get("url"),
        "category": category,
        "importance_score": calculate_importance_score(article, now),
    }


def generate_daily_briefing(
    news_documents: list[dict[str, Any]],
    briefing_day: Optional[date] = None,
) -> dict[str, Any]:
    """Build the briefing document from collected articles."""
    now = datetime.now(timezone.utc)
    selected_articles = select_top_news(news_documents, now=now)
    sections = {section: [] for section in BRIEFING_SECTIONS}

    for article in selected_articles:
        category = article.get("category", "Other Technology")
        for section, section_categories in BRIEFING_SECTIONS.items():
            if category in section_categories:
                sections[section].append(_make_briefing_item(article, now))
                break

    if selected_articles:
        lead_category = selected_articles[0].get("category", "Other Technology")
        learning_of_day = (
            f"Explore {LEARNING_TOPICS.get(lead_category, LEARNING_TOPICS['Other Technology'])} "
            f"based on today's top story: {selected_articles[0].get('title', 'the top story')}."
        )
    else:
        learning_of_day = (
            "Practice reading a news API response and checking its article fields."
        )

    relevant_skills = []
    for article in selected_articles:
        category = article.get("category", "Other Technology")
        for skill in CAREER_SKILLS.get(
            category, CAREER_SKILLS["Other Technology"]
        ):
            if skill not in relevant_skills:
                relevant_skills.append(skill)

    career_opportunity = (
        f"Relevant skills today: {', '.join(relevant_skills[:6])}."
        if relevant_skills
        else "No clear career skills stood out in the collected news."
    )

    current_day = briefing_day or date.today()
    return {
        "briefing_date": current_day.isoformat(),
        "generated_at": now,
        "total_news": len(news_documents),
        "categories": sections,
        "top_news": [
            _make_briefing_item(article, now) for article in selected_articles
        ],
        "learning_of_the_day": learning_of_day,
        "career_opportunity": career_opportunity,
        "created_at": now,
    }


def format_briefing(briefing: dict[str, Any]) -> str:
    """Format a briefing document for display in the terminal."""
    lines = [
        "DAILY GLOBAL TECH BRIEFING",
        f"Date: {briefing['briefing_date']}",
        "",
    ]

    for number, (section, _) in enumerate(BRIEFING_SECTIONS.items(), start=1):
        lines.append(f"{number}. {section}")
        stories = briefing["categories"].get(section, [])
        if not stories:
            lines.append("- No major stories found.")
        for story in stories:
            lines.extend(
                [
                    f"- {story['title']}",
                    f"  Summary: {story['summary']}",
                    f"  Why it matters: {story['why_it_matters']}",
                    f"  Source: {story['source']}",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "7. LEARNING OF THE DAY",
            briefing["learning_of_the_day"],
            "",
            "8. CAREER OPPORTUNITY",
            briefing["career_opportunity"],
        ]
    )
    return "\n".join(lines)


def save_briefing(briefing: dict[str, Any]) -> None:
    """Persist a briefing, updating the existing document for that date."""
    save_daily_briefing(briefing)
