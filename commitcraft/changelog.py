"""Changelog generation from Git commit history."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .git_service import GitCommit, GitService


CHANGELOG_FILE_NAME = "CHANGELOG.md"
LAST_COMMIT_MARKER = "commitcraft:last-commit="
ENTRY_MARKER = "commitcraft:entry="
SECTION_ORDER = (
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Documentation",
    "Tests",
    "Build",
    "Chore",
)
TYPE_SECTIONS = {
    "feat": "Added",
    "fix": "Fixed",
    "docs": "Documentation",
    "style": "Changed",
    "refactor": "Changed",
    "perf": "Changed",
    "test": "Tests",
    "build": "Build",
    "ci": "Build",
    "chore": "Chore",
    "revert": "Changed",
}


@dataclass(frozen=True)
class ChangelogUpdateResult:
    """Result of a changelog update operation."""

    path: Path
    added_count: int
    latest_commit: str | None


@dataclass(frozen=True)
class ChangelogEntry:
    """One categorized changelog entry derived from a Git commit."""

    commit_hash: str
    section: str
    text: str


class ChangelogGenerator:
    """Create and incrementally update a Keep a Changelog-style file."""

    def __init__(self, git: GitService, version: str) -> None:
        self.git = git
        self.version = version

    def update(self) -> ChangelogUpdateResult:
        """Append new commit entries after the last recorded changelog point."""

        changelog_path = self.git.repository_path() / CHANGELOG_FILE_NAME
        existing_content = self._read_existing_content(changelog_path)
        last_recorded_commit = self._last_recorded_commit(existing_content)
        recorded_hashes = self._recorded_entry_hashes(existing_content)
        commits = self.git.commits_after(last_recorded_commit)
        entries = [
            self._entry_from_commit(commit)
            for commit in commits
            if (
                commit.full_hash not in recorded_hashes
                and commit.short_hash not in recorded_hashes
            )
        ]
        if not entries:
            return ChangelogUpdateResult(changelog_path, 0, last_recorded_commit)

        updated_content = self._render_updated_content(existing_content, entries)
        changelog_path.write_text(updated_content, encoding="utf-8")
        return ChangelogUpdateResult(changelog_path, len(entries), commits[-1].full_hash)

    def _read_existing_content(self, changelog_path: Path) -> str:
        """Return the current changelog text or a standard empty changelog."""

        if changelog_path.exists():
            return changelog_path.read_text(encoding="utf-8")
        return self._initial_content()

    def _initial_content(self) -> str:
        """Return a Keep a Changelog-compatible starter document."""

        return (
            "# Changelog\n\n"
            "All notable changes to this project will be documented in this file.\n\n"
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
            "and this project adheres to "
            "[Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
        )

    def _last_recorded_commit(self, content: str) -> str | None:
        """Return the latest CommitCraft marker from an existing changelog."""

        matches = re.findall(
            rf"<!--\s*{re.escape(LAST_COMMIT_MARKER)}([0-9a-f]+)\s*-->",
            content,
        )
        return matches[-1] if matches else None

    def _recorded_entry_hashes(self, content: str) -> set[str]:
        """Return commit hashes already represented by changelog entries."""

        hidden_hashes = re.findall(
            rf"<!--\s*{re.escape(ENTRY_MARKER)}([0-9a-f]+)\s*-->",
            content,
        )
        visible_hashes = re.findall(r"\(`([0-9a-f]{7,40})`\)", content)
        return set(hidden_hashes + visible_hashes)

    def _entry_from_commit(self, commit: GitCommit) -> ChangelogEntry:
        """Convert one Git commit into a categorized changelog entry."""

        commit_type, description = self._parse_conventional_subject(commit.subject)
        section = TYPE_SECTIONS.get(commit_type, "Chore")
        lowered_description = description.lower()
        if lowered_description.startswith(("remove ", "delete ", "drop ")):
            section = "Removed"
        if "security" in lowered_description or commit_type == "security":
            section = "Security"
        return ChangelogEntry(
            commit_hash=commit.full_hash,
            section=section,
            text=f"- {self._sentence_case(description)} (`{commit.short_hash}`)",
        )

    def _parse_conventional_subject(self, subject: str) -> tuple[str, str]:
        """Extract Conventional Commit type and readable description when present."""

        match = re.match(r"^(?P<type>[a-z]+)(?:\([^)]+\))?(?:!)?:\s*(?P<text>.+)$", subject)
        if match is None:
            return "chore", subject.strip()
        return match.group("type"), match.group("text").strip()

    def _sentence_case(self, value: str) -> str:
        """Normalize a commit subject for display as a changelog bullet."""

        cleaned = value.strip().rstrip(".")
        if not cleaned:
            return "Update project"
        return f"{cleaned[0].upper()}{cleaned[1:]}"

    def _render_updated_content(self, content: str, entries: list[ChangelogEntry]) -> str:
        """Merge new entries into the current version section without duplicating old entries."""

        normalized_content = self._strip_last_commit_marker(content).rstrip() + "\n"
        existing_heading = self._existing_version_heading(normalized_content)
        section_heading = existing_heading or self._version_heading()
        if existing_heading is None:
            insertion_point = self._first_version_heading_index(normalized_content)
            new_section = f"\n{section_heading}\n{self._render_entries(entries)}"
            if insertion_point is None:
                normalized_content = f"{normalized_content}{new_section}"
            else:
                normalized_content = (
                    normalized_content[:insertion_point]
                    + new_section
                    + "\n"
                    + normalized_content[insertion_point:]
                )
        else:
            normalized_content = self._append_to_existing_version(
                normalized_content,
                section_heading,
                entries,
            )
        return self._replace_last_commit_marker(normalized_content, entries[-1].commit_hash)

    def _version_heading(self) -> str:
        """Return the dated SemVer heading for the current application version."""

        return f"## [{self.version}] - {date.today().isoformat()}"

    def _existing_version_heading(self, content: str) -> str | None:
        """Return the existing heading for the current version regardless of date."""

        match = re.search(
            rf"^## \[{re.escape(self.version)}\](?:\s+-\s+\d{{4}}-\d{{2}}-\d{{2}})?$",
            content,
            flags=re.MULTILINE,
        )
        return match.group(0) if match else None

    def _first_version_heading_index(self, content: str) -> int | None:
        """Return where generated version sections should start."""

        match = re.search(r"^## \[", content, flags=re.MULTILINE)
        return match.start() if match else None

    def _render_entries(self, entries: list[ChangelogEntry]) -> str:
        """Render grouped changelog entries using recognized category headings."""

        lines: list[str] = []
        for section in SECTION_ORDER:
            section_entries = [entry for entry in entries if entry.section == section]
            if not section_entries:
                continue
            lines.append(f"\n### {section}")
            for entry in section_entries:
                lines.append(f"{entry.text} <!-- {ENTRY_MARKER}{entry.commit_hash} -->")
        return "\n".join(lines).strip() + "\n"

    def _append_to_existing_version(
        self,
        content: str,
        section_heading: str,
        entries: list[ChangelogEntry],
    ) -> str:
        """Append entries inside an existing version section in category order."""

        lines = content.splitlines()
        start = lines.index(section_heading)
        end = self._version_section_end(lines, start + 1)
        section_lines = lines[start:end]
        for section in SECTION_ORDER:
            section_entries = [entry for entry in entries if entry.section == section]
            if not section_entries:
                continue
            section_lines = self._append_entries_to_category(
                section_lines,
                section,
                section_entries,
            )
        return "\n".join(lines[:start] + section_lines + lines[end:]).rstrip() + "\n"

    def _version_section_end(self, lines: list[str], start: int) -> int:
        """Return the exclusive line index for the current version section."""

        for index in range(start, len(lines)):
            if lines[index].startswith("## ["):
                return index
        return len(lines)

    def _append_entries_to_category(
        self,
        section_lines: list[str],
        category: str,
        entries: list[ChangelogEntry],
    ) -> list[str]:
        """Append entries to a category or create that category in the right order."""

        rendered_entries = [
            f"{entry.text} <!-- {ENTRY_MARKER}{entry.commit_hash} -->"
            for entry in entries
        ]
        category_heading = f"### {category}"
        if category_heading in section_lines:
            insert_at = section_lines.index(category_heading) + 1
            while insert_at < len(section_lines) and section_lines[insert_at].startswith("- "):
                insert_at += 1
            return section_lines[:insert_at] + rendered_entries + section_lines[insert_at:]

        insert_at = self._category_insert_index(section_lines, category)
        prefix = [""] if insert_at > 0 and section_lines[insert_at - 1] else []
        suffix = [""] if insert_at < len(section_lines) and section_lines[insert_at] else []
        return (
            section_lines[:insert_at]
            + prefix
            + [category_heading]
            + rendered_entries
            + suffix
            + section_lines[insert_at:]
        )

    def _category_insert_index(self, section_lines: list[str], category: str) -> int:
        """Return where a missing category should be inserted to keep standard order."""

        target_order = SECTION_ORDER.index(category)
        for index, line in enumerate(section_lines):
            if not line.startswith("### "):
                continue
            existing_category = line.removeprefix("### ")
            if (
                existing_category in SECTION_ORDER
                and SECTION_ORDER.index(existing_category) > target_order
            ):
                return index
        return len(section_lines)

    def _replace_last_commit_marker(self, content: str, commit_hash: str) -> str:
        """Store the latest generated commit marker as hidden metadata."""

        marker = f"<!-- {LAST_COMMIT_MARKER}{commit_hash} -->"
        content_without_old_marker = self._strip_last_commit_marker(content).rstrip()
        return f"{content_without_old_marker}\n\n{marker}\n"

    def _strip_last_commit_marker(self, content: str) -> str:
        """Remove the hidden latest-commit marker before rewriting generated content."""

        pattern = rf"<!--\s*{re.escape(LAST_COMMIT_MARKER)}[0-9a-f]+\s*-->"
        return re.sub(pattern, "", content)
