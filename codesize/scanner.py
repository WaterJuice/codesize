# ----------------------------------------------------------------------------------------
#   scanner.py
#   ----------
#
#   Scans directories for code files and collects statistics.
#   Supports Python, Go, Rust, Elixir, JavaScript, C, and Objective-C.
#
#   .h files are auto-detected as C or Objective-C based on content markers.
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


PYTHON_LANG = Language("Python", (".py",), "#", docstring_markers=('"""', "'''"))
GO_LANG = Language(
    "Go", (".go",), "//", block_comment_start="/*", block_comment_end="*/"
)
RUST_LANG = Language(
    "Rust", (".rs",), "//", block_comment_start="/*", block_comment_end="*/"
)
ELIXIR_LANG = Language("Elixir", (".ex", ".exs"), "#", docstring_markers=('"""',))
JAVASCRIPT_LANG = Language(
    "JavaScript",
    (".js", ".mjs", ".cjs"),
    "//",
    block_comment_start="/*",
    block_comment_end="*/",
)
# C and Objective-C share .h files — those are disambiguated by content (see scan_directory)
C_LANG = Language("C", (".c",), "//", block_comment_start="/*", block_comment_end="*/")
OBJC_LANG = Language(
    "Objective-C",
    (".m", ".mm"),
    "//",
    block_comment_start="/*",
    block_comment_end="*/",
)

LANGUAGES: tuple[Language, ...] = (
    PYTHON_LANG,
    GO_LANG,
    RUST_LANG,
    ELIXIR_LANG,
    JAVASCRIPT_LANG,
    C_LANG,
    OBJC_LANG,
)

# Tokens that strongly indicate Objective-C (used to disambiguate .h files)
OBJC_MARKERS = ("@interface", "@protocol", "@class", "@property", "@end", "#import")
# Objective-C markers appear near the top of a header (imports/declarations);
# scanning only the prefix avoids O(file_size) substring work on large pure-C headers.
OBJC_MARKER_SCAN_BYTES = 20_000

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
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    return _count_lines_from_content(content, lang)


# ----------------------------------------------------------------------------------------
def _count_lines_from_content(content: str, lang: Language) -> tuple[int, int]:
    """Count total and code lines from a content string (file already read)."""
    total_lines = 0
    code_lines = 0
    in_block_comment = False
    block_end: str | None = None
    in_docstring = False
    docstring_marker: str | None = None

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
def _record_file(
    filepath: Path,
    lang: Language,
    lang_stats: dict[str, LangStats],
    content: str | None = None,
) -> None:
    """Record statistics for a single file into lang_stats."""
    if lang.name not in lang_stats:
        lang_stats[lang.name] = LangStats(name=lang.name)
    stats = lang_stats[lang.name]
    stats.num_files += 1

    try:
        stats.total_bytes += filepath.stat().st_size
    except OSError:
        pass

    if content is not None:
        lines, code = _count_lines_from_content(content, lang)
    else:
        lines, code = count_lines(filepath, lang)
    stats.total_lines += lines
    stats.code_lines += code


# ----------------------------------------------------------------------------------------
def scan_directory(directory: Path) -> CodeStats:
    """
    Scan a directory recursively for code files and collect statistics.

    Uses os.walk with hidden-directory pruning for fast traversal. Skips
    directories starting with a dot (e.g. .venv, .git). Only includes
    languages that have at least one file.

    .h files are disambiguated as C or Objective-C using these signals
    (in priority order):
      1. Content tokens (e.g. @interface, #import) → Objective-C
      2. Companion .m or .mm in same dir with same basename → Objective-C
      3. Companion .c in same dir with same basename → C
      4. Any .m/.mm in the scanned tree → Objective-C
      5. Otherwise → C

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
    deferred_h_files: list[tuple[Path, str]] = []
    # (dir, basename) -> language of the companion source file (C_LANG or OBJC_LANG)
    companion_langs: dict[tuple[Path, str], Language] = {}

    for dirpath, dirnames, filenames in os.walk(directory):
        # Prune hidden directories in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for filename in filenames:
            filepath = Path(dirpath, filename)
            ext = filepath.suffix

            if ext == ".h":
                # Defer until we've seen all companions
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                deferred_h_files.append((filepath, content))
                continue

            lang = extension_map.get(ext)
            if lang is None:
                continue

            if lang is OBJC_LANG:
                # .m/.mm wins over .c if both somehow exist for same basename
                companion_langs[(filepath.parent, filepath.stem)] = OBJC_LANG
            elif lang is C_LANG:
                companion_langs.setdefault((filepath.parent, filepath.stem), C_LANG)

            _record_file(filepath, lang, lang_stats)

    # Now process .h files with full project knowledge
    has_objc_impl = any(v is OBJC_LANG for v in companion_langs.values())
    for filepath, content in deferred_h_files:
        head = content[:OBJC_MARKER_SCAN_BYTES]
        if any(marker in head for marker in OBJC_MARKERS):
            lang = OBJC_LANG
        else:
            companion = companion_langs.get((filepath.parent, filepath.stem))
            if companion is OBJC_LANG:
                lang = OBJC_LANG
            elif companion is C_LANG:
                lang = C_LANG
            elif has_objc_impl:
                lang = OBJC_LANG
            else:
                lang = C_LANG
        _record_file(filepath, lang, lang_stats, content=content)

    # Preserve language ordering from LANGUAGES
    languages: list[LangStats] = []
    for lang in LANGUAGES:
        if lang.name in lang_stats:
            languages.append(lang_stats[lang.name])

    return CodeStats(languages=languages)
