# ----------------------------------------------------------------------------------------
#   scanner.py
#   ----------
#
#   Scans directories for code files and collects statistics.
#   Supports Python, Go, Rust, and Elixir.
#
#   (c) 2026 WaterJuice — Unlicense; see LICENSE in the project root.
#
#   Version History
#   ---------------
#   Mar 2026 - Created
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
#   Imports
# ----------------------------------------------------------------------------------------

import os
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

# ----------------------------------------------------------------------------------------
#   Language Definitions
# ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Language:
    """Configuration for a supported programming language."""

    name: str
    extensions: tuple[str, ...]
    line_comment: str
    block_comment_start: str | None = None
    block_comment_end: str | None = None
    docstring_markers: tuple[str, ...] = ()


LANGUAGES: tuple[Language, ...] = (
    Language("Python", (".py",), "#", docstring_markers=('"""', "'''")),
    Language("Go", (".go",), "//", block_comment_start="/*", block_comment_end="*/"),
    Language("Rust", (".rs",), "//", block_comment_start="/*", block_comment_end="*/"),
    Language("Elixir", (".ex", ".exs"), "#", docstring_markers=('"""',)),
)

# ----------------------------------------------------------------------------------------
#   Data Classes
# ----------------------------------------------------------------------------------------


@dataclass
class LangStats:
    """Statistics for files of a single language."""

    name: str
    num_files: int = 0
    total_bytes: int = 0
    total_lines: int = 0
    code_lines: int = 0

    @property
    def total_kb(self) -> float:
        """Return total size in kilobytes."""
        return self.total_bytes / 1024


@dataclass
class CodeStats:
    """Statistics for all code files in a directory."""

    languages: list[LangStats] = field(default_factory=lambda: list[LangStats]())

    @property
    def total(self) -> LangStats:
        """Return combined statistics across all languages."""
        return LangStats(
            name="Total",
            num_files=sum(lang.num_files for lang in self.languages),
            total_bytes=sum(lang.total_bytes for lang in self.languages),
            total_lines=sum(lang.total_lines for lang in self.languages),
            code_lines=sum(lang.code_lines for lang in self.languages),
        )


# ----------------------------------------------------------------------------------------
#   Functions
# ----------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------
def _is_code_line(stripped: str, comment_prefix: str) -> bool:
    """Determine if a line is a code line (not blank or decorative comment)."""
    if not stripped:
        return False
    if stripped.startswith(comment_prefix):
        # Count comments with meaningful content, but not bare markers or separator lines
        comment_body = stripped[len(comment_prefix) :]
        return any(ch.isalnum() for ch in comment_body)
    return True


# ----------------------------------------------------------------------------------------
def count_lines(filepath: Path, lang: Language) -> tuple[int, int]:
    """
    Count total lines and code lines in a file.

    Handles single-line comments, block comments, and docstrings/heredocs
    according to the language configuration.

    Returns:
        Tuple of (total_lines, code_lines).
    """
    total_lines = 0
    code_lines = 0
    in_block_comment = False
    block_end: str | None = None
    in_docstring = False
    docstring_marker: str | None = None

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0

    for line in content.splitlines():
        total_lines += 1
        stripped = line.strip()

        # Inside a block comment (/* ... */)
        if in_block_comment:
            if block_end and block_end in stripped:
                in_block_comment = False
                block_end = None
            continue

        # Inside a docstring/heredoc
        if in_docstring:
            if docstring_marker and docstring_marker in stripped:
                in_docstring = False
                docstring_marker = None
            continue

        # Check for start of block comment
        if lang.block_comment_start and stripped.startswith(lang.block_comment_start):
            rest = stripped[len(lang.block_comment_start) :]
            if lang.block_comment_end and lang.block_comment_end not in rest:
                in_block_comment = True
                block_end = lang.block_comment_end
            continue

        # Check for docstring/heredoc markers (Python: starts with """, Elixir: ends with """)
        found_marker = False
        for marker in lang.docstring_markers:
            starts = stripped.startswith(marker)
            ends = stripped.endswith(marker)
            if starts or ends:
                if starts:
                    rest = stripped[len(marker) :]
                else:
                    rest = stripped[: -len(marker)]
                if marker not in rest:
                    in_docstring = True
                    docstring_marker = marker
                found_marker = True
                break
        if found_marker:
            continue

        if _is_code_line(stripped, lang.line_comment):
            code_lines += 1

    return total_lines, code_lines


# ----------------------------------------------------------------------------------------
def scan_directory(directory: Path) -> CodeStats:
    """
    Scan a directory recursively for code files and collect statistics.

    Uses os.walk with hidden-directory pruning for fast traversal. Skips
    directories starting with a dot (e.g. .venv, .git). Only includes
    languages that have at least one file.

    Args:
        directory: The directory to scan.

    Returns:
        CodeStats object containing per-language and total statistics.
    """
    # Build extension lookup
    extension_map: dict[str, Language] = {}
    for lang in LANGUAGES:
        for ext in lang.extensions:
            extension_map[ext] = lang

    # Walk once, pruning hidden dirs, collecting and processing files
    lang_stats: dict[str, LangStats] = {}

    for dirpath, dirnames, filenames in os.walk(directory):
        # Prune hidden directories in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            lang = extension_map.get(ext)
            if lang is None:
                continue

            filepath = Path(dirpath, filename)

            if lang.name not in lang_stats:
                lang_stats[lang.name] = LangStats(name=lang.name)
            stats = lang_stats[lang.name]
            stats.num_files += 1

            try:
                stats.total_bytes += filepath.stat().st_size
            except OSError:
                pass

            lines, code = count_lines(filepath, lang)
            stats.total_lines += lines
            stats.code_lines += code

    # Preserve language ordering from LANGUAGES
    languages: list[LangStats] = []
    for lang in LANGUAGES:
        if lang.name in lang_stats:
            languages.append(lang_stats[lang.name])

    return CodeStats(languages=languages)
