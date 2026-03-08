"""Skills management service — install, uninstall, search, list, and read skill content."""

import asyncio
import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".agents" / "skills"


def _parse_skill_md(skill_dir: Path) -> dict:
    """Parse SKILL.md frontmatter into metadata dict."""
    skill_file = skill_dir / "SKILL.md"
    meta = {"name": skill_dir.name, "description": "", "version": "", "source": "local"}
    # Check for .source marker written at install time
    source_file = skill_dir / ".source"
    if source_file.exists():
        meta["source"] = source_file.read_text(errors="ignore").strip() or "local"
    if not skill_file.exists():
        return meta
    content = skill_file.read_text(errors="ignore")
    # Parse YAML-like frontmatter between --- delimiters
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            line = line.strip()
            if line.startswith("description:"):
                meta["description"] = line.split(":", 1)[1].strip().strip('"').strip("|").strip()
            elif line.startswith("version:"):
                meta["version"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("name:"):
                meta["name"] = line.split(":", 1)[1].strip().strip('"')
    else:
        # Fallback: parse loose key: value at top of file
        for line in content.split("\n")[:20]:
            line = line.strip()
            if line.startswith("description:"):
                meta["description"] = line.split(":", 1)[1].strip().strip('"').strip("|").strip()
            elif line.startswith("version:"):
                meta["version"] = line.split(":", 1)[1].strip().strip('"')
    # Count reference files
    refs_dir = skill_dir / "references"
    meta["fileCount"] = len(list(refs_dir.iterdir())) if refs_dir.exists() else 0
    return meta


class SkillsService:
    """Manages agent skills lifecycle."""

    def __init__(self, skills_dir: Path | None = None):
        self._dir = skills_dir or SKILLS_DIR

    # ── List ──────────────────────────────────────────────────────────

    def list_installed(self) -> list[dict]:
        """Scan .agents/skills/ and return installed skills with metadata."""
        if not self._dir.exists():
            return []
        skills = []
        for entry in sorted(self._dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                skills.append(_parse_skill_md(entry))
        return skills

    # ── Install from marketplace ──────────────────────────────────────

    async def install_from_marketplace(self, repo: str, skill_name: str) -> dict:
        """Download skill files from GitHub repo directly (no npx required)."""
        import aiohttp

        install_name = skill_name or repo.split("/")[-1]
        logger.info("Installing marketplace skill: %s from %s", install_name, repo)
        try:
            async with aiohttp.ClientSession() as session:
                # Get the repo's default branch and file tree
                tree_url = f"https://api.github.com/repos/{repo}/git/trees/main?recursive=1"
                async with session.get(tree_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 404:
                        # Try 'master' branch
                        tree_url = f"https://api.github.com/repos/{repo}/git/trees/master?recursive=1"
                        resp = await session.get(tree_url, timeout=aiohttp.ClientTimeout(total=30))
                    if resp.status != 200:
                        return {"name": install_name, "status": "failed", "error": f"GitHub API returned {resp.status}"}
                    tree_data = await resp.json()

                # Find the skill directory — look for SKILL.md
                tree = tree_data.get("tree", [])
                skill_prefix = ""
                for item in tree:
                    path = item["path"]
                    if item["type"] == "blob" and path.endswith("SKILL.md"):
                        # Check if this matches the requested skill
                        parent = path.rsplit("/", 1)[0] if "/" in path else ""
                        dir_name = parent.rsplit("/", 1)[-1] if parent else ""
                        if not skill_name or dir_name == skill_name or parent == "":
                            skill_prefix = (parent + "/") if parent else ""
                            break

                if not skill_prefix and not any(i["path"] == "SKILL.md" for i in tree):
                    return {"name": install_name, "status": "failed", "error": "No SKILL.md found in repository"}

                # Download all files under the skill prefix
                skill_dir = self._dir / install_name
                skill_dir.mkdir(parents=True, exist_ok=True)
                branch = "main"  # already resolved above
                count = 0
                for item in tree:
                    if item["type"] != "blob":
                        continue
                    path = item["path"]
                    if not path.startswith(skill_prefix):
                        continue
                    rel_path = path[len(skill_prefix):]
                    if not rel_path:
                        continue
                    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
                    async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=30)) as dl:
                        if dl.status == 200:
                            content = await dl.read()
                            dest = skill_dir / rel_path
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(content)
                            count += 1

                if count == 0:
                    return {"name": install_name, "status": "failed", "error": "No files downloaded"}

                (skill_dir / ".source").write_text("skills.sh")
                logger.info("Installed skill %s (%d files) from GitHub", install_name, count)
                return {**_parse_skill_md(skill_dir), "status": "installed"}

        except asyncio.TimeoutError:
            logger.error("Timeout installing skill %s", install_name)
            return {"name": install_name, "status": "failed", "error": "Installation timed out"}
        except Exception as exc:
            logger.exception("Failed to install skill %s", install_name)
            return {"name": install_name, "status": "failed", "error": str(exc)}

    # ── Install from local path ───────────────────────────────────────

    def install_from_local(self, source_path: str, name: str) -> dict:
        """Copy a local skill directory into .agents/skills/<name>/."""
        src = Path(source_path).expanduser().resolve()
        if not src.exists() or not src.is_dir():
            return {"name": name, "status": "failed", "error": f"Source path not found: {source_path}"}
        skill_md = src / "SKILL.md"
        if not skill_md.exists():
            return {"name": name, "status": "failed", "error": "No SKILL.md found in source directory"}
        dest = self._dir / name
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, dirs_exist_ok=True)
        logger.info("Installed local skill %s from %s", name, source_path)
        return {**_parse_skill_md(dest), "status": "installed"}

    # ── Install from uploaded files ────────────────────────────────────

    def install_from_upload(self, name: str, files: dict[str, bytes]) -> dict:
        """Install a skill from uploaded file contents. files is {relative_path: bytes}."""
        if not files:
            return {"name": name, "status": "failed", "error": "No files provided"}
        has_skill_md = any(p == "SKILL.md" or p.endswith("/SKILL.md") for p in files)
        if not has_skill_md:
            return {"name": name, "status": "failed", "error": "No SKILL.md found in uploaded files"}
        dest = self._dir / name
        dest.mkdir(parents=True, exist_ok=True)
        for rel_path, content in files.items():
            file_dest = dest / rel_path
            file_dest.parent.mkdir(parents=True, exist_ok=True)
            file_dest.write_bytes(content)
        logger.info("Installed uploaded skill %s (%d files)", name, len(files))
        return {**_parse_skill_md(dest), "status": "installed"}

    # ── Uninstall ─────────────────────────────────────────────────────

    def uninstall(self, name: str) -> dict:
        """Remove a skill directory."""
        skill_path = self._dir / name
        if not skill_path.exists():
            return {"name": name, "success": False, "error": "Skill not found"}
        shutil.rmtree(skill_path)
        logger.info("Uninstalled skill %s", name)
        return {"name": name, "success": True}

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

    # ── Read skill content for prompt injection ────────────────────────

    def get_skill_content(self, name: str, max_tokens: int = 2000) -> str | None:
        """Read SKILL.md + key reference files, truncated to token budget."""
        skill_path = self._dir / name
        if not skill_path.exists():
            return None
        parts = []
        # Read SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            parts.append(skill_md.read_text(errors="ignore"))
        # Read reference files (sorted, skip binary)
        refs_dir = skill_path / "references"
        if refs_dir.exists():
            for ref_file in sorted(refs_dir.iterdir()):
                if ref_file.is_file() and ref_file.suffix in (".md", ".txt", ".yaml", ".yml", ".json"):
                    parts.append(f"\n--- {ref_file.name} ---\n")
                    parts.append(ref_file.read_text(errors="ignore"))
        content = "\n".join(parts)
        # Rough token estimate: ~4 chars per token
        char_limit = max_tokens * 4
        if len(content) > char_limit:
            content = content[:char_limit] + "\n\n[... truncated to fit token budget ...]"
        return content

    # ── Auto-suggest skills for a spec ────────────────────────────────

    def suggest_skills_for_content(self, content: str, top_n: int = 3) -> list[str]:
        """Match spec content keywords against installed skill descriptions.
        Returns top-N skill names sorted by relevance score.
        """
        installed = self.list_installed()
        if not installed:
            return []

        content_lower = content.lower()
        scored = []
        for skill in installed:
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
