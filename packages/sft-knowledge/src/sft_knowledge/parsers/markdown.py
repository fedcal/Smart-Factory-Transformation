"""MarkdownParser — parses SOP *.md files with YAML frontmatter into `ParsedDoc`.

Behavior (D-67, D-25, D-72):
    * status: reviewed gate — non-reviewed → returns None (log "sop_skipped_non_reviewed")
    * acl_level default fallback — missing → "internal" (NEVER "restricted"); log WARN
      "sop_missing_acl_level". Never silently defaults to "public" either.
    * Heading state machine — regex `^(#{1,6})\\s+(.+?)(?:\\s+#+)?$` MULTILINE; tracks the
      current heading_path stack and resets deeper levels when a higher-level heading
      appears.
    * Section text = body slice between heading offsets, stripped, heading line excluded.
    * Required-field gate — missing id/title/version/lang → ValueError with file path.

Security:
    * python-frontmatter wraps yaml.safe_load internally (RESEARCH §10) — never call
      yaml.load directly (T-05-01-01 mitigation).
    * source_uri is derived from path relative to the workspace root — not user input
      (T-05-01-03 accepted).
"""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter
import structlog

from sft_knowledge.parsers.base import DocumentParser, ParsedDoc, ParsedSection

logger = structlog.get_logger(__name__)

HEADING_RE: re.Pattern[str] = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$", re.MULTILINE)

# Required frontmatter keys (D-67). Phase 5 enforces; Phase 2 corpus generator guarantees.
_REQUIRED_FIELDS: tuple[str, ...] = ("id", "title", "version", "lang")

# Walk up from packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py to workspace root.
# parents[0]=parsers, parents[1]=sft_knowledge, parents[2]=src, parents[3]=sft-knowledge,
# parents[4]=packages, parents[5]=workspace root.
_WORKSPACE_ROOT: Path = Path(__file__).resolve().parents[5]


def _build_heading_path(content: str) -> list[tuple[int, int, list[str]]]:
    """Scan content and return a list of (heading_end_offset, next_heading_start, heading_path).

    Each entry corresponds to one heading; the heading_path is the full nested chain
    (e.g. ["H1 title", "H2 title", "H3 title"] for an H3 nested under H2 under H1).
    """
    entries: list[tuple[int, int, list[str]]] = []
    matches: list[re.Match[str]] = list(HEADING_RE.finditer(content))
    stack: list[str] = []
    current_levels: list[int] = []  # parallel to stack: pound counts

    for idx, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        # Pop until parent depth strictly less than current level
        while current_levels and current_levels[-1] >= level:
            current_levels.pop()
            stack.pop()
        stack.append(title)
        current_levels.append(level)
        heading_end = m.end()
        next_start = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        entries.append((heading_end, next_start, list(stack)))
    return entries


class MarkdownParser(DocumentParser):
    """Parsa file SOP *.md con YAML frontmatter in `ParsedDoc`.

    Gates:
        - status != "reviewed" → return None (D-25)
        - missing acl_level → default "internal" (D-67/D-72)
        - missing required field → raise ValueError
    """

    def supported_extensions(self) -> set[str]:
        return {".md"}

    async def parse(self, path: Path) -> ParsedDoc | None:
        # 1. Load frontmatter (python-frontmatter uses yaml.safe_load internally).
        post = frontmatter.load(str(path))

        # 2. Status gate (D-25).
        status = post.metadata.get("status")
        if status != "reviewed":
            logger.info(
                "sop_skipped_non_reviewed",
                path=str(path),
                status=status,
            )
            return None

        # 3. ACL default fallback (D-67/D-72) — immutable update.
        if "acl_level" not in post.metadata:
            logger.warning(
                "sop_missing_acl_level",
                path=str(path),
                default="internal",
            )
            metadata: dict = {**post.metadata, "acl_level": "internal"}
        else:
            metadata = dict(post.metadata)

        # 4. Required-fields check.
        missing = [k for k in _REQUIRED_FIELDS if k not in metadata]
        if missing:
            raise ValueError(
                f"{path}: missing required frontmatter field(s): {', '.join(missing)}"
            )

        # 5. Heading state machine → sections.
        entries = _build_heading_path(post.content)
        sections: list[ParsedSection] = []
        for heading_end, next_start, heading_path in entries:
            text = post.content[heading_end:next_start].strip()
            if not text:
                continue
            sections.append(ParsedSection(heading_path=heading_path, text=text))

        # 6. source_uri derived from relative path inside workspace.
        try:
            rel = path.resolve().relative_to(_WORKSPACE_ROOT)
            source_uri = f"corpus://{rel.as_posix()}"
        except ValueError:
            # Path not under workspace root (e.g. tmp_path fixture) — fall back to absolute.
            source_uri = f"corpus://{path.resolve().as_posix().lstrip('/')}"

        return ParsedDoc(
            source_uri=source_uri,
            frontmatter=metadata,
            sections=sections,
            version=str(metadata["version"]),
            lang=metadata["lang"],
        )
