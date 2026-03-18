"""Skills service — marketplace search and skill suggestion utilities."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SkillsService:
    """Stateless utilities for marketplace search and skill suggestion."""

    # ── Search marketplace ────────────────────────────────────────────

    async def search_marketplace(self, query: str) -> list[dict]:
        """Search skills.sh marketplace via their public JSON API."""
        import aiohttp

        url = f"https://skills.sh/api/search?q={query}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.warning("skills.sh API returned %d", resp.status)
                        return []
                    data = await resp.json()
                    skills = data.get("skills", [])
                    return [
                        {
                            "name": s.get("name", s.get("skillId", "")),
                            "repo": s.get("source", ""),
                            "skillDir": s.get("skillId", s.get("name", "")),
                            "url": f"https://skills.sh/{s.get('id', '')}",
                            "description": "",
                            "installs": s.get("installs", 0),
                        }
                        for s in skills[:20]
                        if s.get("name")
                    ]
        except Exception as e:
            logger.warning("skills.sh search failed: %s", e)
            return []

    # ── Auto-suggest skills for content ───────────────────────────────

    def suggest_skills_for_content(
        self,
        content: str,
        installed_skills: list[dict],
        top_n: int = 3,
    ) -> list[str]:
        """Match content keywords against provided skill descriptions.

        *installed_skills* is a list of dicts each containing at least
        ``name`` and ``description`` keys (as returned by
        ``CosmosSkillsService.list_activated``).

        Returns the top-*n* skill names sorted by relevance score.
        """
        if not installed_skills:
            return []

        content_lower = content.lower()
        scored: list[tuple[str, int]] = []
        for skill in installed_skills:
            score = 0
            # Check skill name words in content
            for word in skill["name"].replace("-", " ").split():
                if len(word) > 2 and word.lower() in content_lower:
                    score += 3
            # Check description words in content
            desc_words = skill.get("description", "").lower().split()
            for word in desc_words:
                if len(word) > 3 and word in content_lower:
                    score += 1
            if score > 0:
                scored.append((skill["name"], score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:top_n]]
