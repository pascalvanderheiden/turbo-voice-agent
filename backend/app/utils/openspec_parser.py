"""OpenSpec project folder parser.

Parses an uploaded OpenSpec project structure into typed data for import
into the app's spec system. Understands the standard layout:

    project.md                     — project context (optional)
    specs/<name>/spec.md           — capability specifications
    changes/<name>/proposal.md     — change proposals (optional)
    changes/<name>/design.md       — change designs (optional)
    changes/<name>/tasks.md        — change task lists (optional)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)


@dataclass
class ParsedSpec:
    """A single capability spec extracted from specs/<name>/spec.md."""

    name: str
    content: str


@dataclass
class ParsedChange:
    """A single change extracted from changes/<name>/."""

    name: str
    proposal: str = ""
    design: str = ""
    tasks: str = ""


@dataclass
class ParsedOpenSpecProject:
    """Complete parsed result from an OpenSpec project folder."""

    folder_name: str
    project_context: str = ""
    specs: list[ParsedSpec] = field(default_factory=list)
    changes: list[ParsedChange] = field(default_factory=list)


def parse_openspec_folder(
    files: dict[str, str],
    folder_name: str = "imported-project",
) -> ParsedOpenSpecProject:
    """Parse an OpenSpec folder structure from a flat file map.

    Args:
        files: Mapping of relative paths to file contents.
            Paths use forward slashes (e.g. "specs/auth/spec.md").
        folder_name: Name of the root folder (for the foundation title).

    Returns:
        ParsedOpenSpecProject with extracted data.

    Raises:
        ValueError: If no specs/ directory is found with at least one spec.md.
    """
    result = ParsedOpenSpecProject(folder_name=folder_name)

    # Normalize paths: strip leading slashes, collapse duplicates
    normalized: dict[str, str] = {}
    for path, content in files.items():
        clean = PurePosixPath(path).as_posix().lstrip("/")
        normalized[clean] = content

    # Extract project.md
    for key in ("project.md", "openspec/project.md"):
        if key in normalized:
            result.project_context = normalized[key]
            break

    # Extract specs/<name>/spec.md
    spec_pattern = re.compile(r"^(?:openspec/)?specs/([^/]+)/spec\.md$")
    for path, content in normalized.items():
        m = spec_pattern.match(path)
        if m:
            result.specs.append(ParsedSpec(name=m.group(1), content=content))

    if not result.specs:
        raise ValueError(
            "No specs/ directory found in the selected folder. "
            "Expected at least one specs/<name>/spec.md file."
        )

    # Sort specs alphabetically for deterministic ordering
    result.specs.sort(key=lambda s: s.name)

    # Extract changes/<name>/{proposal,design,tasks}.md
    change_pattern = re.compile(
        r"^(?:openspec/)?changes/([^/]+)/(proposal|design|tasks)\.md$"
    )
    changes_map: dict[str, ParsedChange] = {}
    for path, content in normalized.items():
        m = change_pattern.match(path)
        if m:
            name, artifact = m.group(1), m.group(2)
            if name not in changes_map:
                changes_map[name] = ParsedChange(name=name)
            setattr(changes_map[name], artifact, content)

    result.changes = sorted(changes_map.values(), key=lambda c: c.name)

    logger.info(
        "Parsed OpenSpec project '%s': %d specs, %d changes, project.md=%s",
        folder_name,
        len(result.specs),
        len(result.changes),
        bool(result.project_context),
    )

    return result


def synthesize_change_history(changes: list[ParsedChange]) -> str:
    """Concatenate change proposals/designs into a readable history section."""
    if not changes:
        return ""

    parts = ["## Change History\n"]
    for change in changes:
        parts.append(f"### {change.name}\n")
        if change.proposal:
            parts.append(f"**Proposal:**\n{change.proposal.strip()}\n")
        if change.design:
            parts.append(f"**Design:**\n{change.design.strip()}\n")
        parts.append("")

    return "\n".join(parts)
