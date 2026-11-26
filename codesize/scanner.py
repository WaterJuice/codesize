# ----------------------------------------------------------------------------------------
#   scanner.py
#   ----------
#
#   Scans directories for code files and collects statistics.
#   Supports Python, Go, Rust, Elixir, JavaScript, TypeScript, Swift, C, and
#   Objective-C.
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
import re
import stat
import sys
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from dataclasses import dataclass
from dataclasses import field
from functools import cache
from pathlib import Path
from typing import Literal
from typing import get_args
from codesize._vendor.pathspec import GitIgnoreSpec
from codesize._vendor.pathspec.patterns.gitignore import GitIgnorePatternError
from codesize._vendor.pathspec.patterns.gitignore.spec import GitIgnoreSpecPattern

# ----------------------------------------------------------------------------------------
#   Types
# ----------------------------------------------------------------------------------------

SortKey = Literal["code", "files", "size", "lines", "name"]
SORT_KEYS: tuple[str, ...] = get_args(SortKey)

# ----------------------------------------------------------------------------------------
#   Language Definitions
# ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Language:
    """Configuration for a supported programming language.

    The string settings let the line counter step over string literals, so a comment
    or docstring marker inside a string isn't mistaken for a real one.
    """

    name: str
    extensions: tuple[str, ...]
    line_comment: str
    block_comment_start: str | None = None
    block_comment_end: str | None = None
    docstring_markers: tuple[str, ...] = ()
    # A docstring is a string that starts a statement: its marker is the first thing on
    # its line bar what this regex matches (string prefixes, doc attributes), and no
    # bracket or backslash continuation is open. A marker anywhere else starts an
    # ordinary string, which is code.
    docstring_prefix: str = ""
    # Docstrings are heredocs: they open at the end of a line and close at the start
    # of a later one.
    docstring_heredoc: bool = False
    # Quotes of strings that end on the line they start on (backslash escapes).
    quotes: tuple[str, ...] = ('"', "'")
    # Quotes of strings that may run over several lines, with and without escapes.
    multiline_quotes: tuple[str, ...] = ()
    raw_multiline_quotes: tuple[str, ...] = ()
    # Rust literals: 'c' is a char but a lone ' is a lifetime; r#"..."# raw strings.
    rust_literals: bool = False
    # JavaScript-style /regex/ literals.
    regex_literals: bool = False


PYTHON_LANG = Language(
    "Python",
    (".py",),
    "#",
    docstring_markers=('"""', "'''"),
    docstring_prefix=r"[rRbBuUfFtT]{0,2}",
)
GO_LANG = Language(
    "Go",
    (".go",),
    "//",
    block_comment_start="/*",
    block_comment_end="*/",
    raw_multiline_quotes=("`",),
)
RUST_LANG = Language(
    "Rust",
    (".rs",),
    "//",
    block_comment_start="/*",
    block_comment_end="*/",
    quotes=(),
    multiline_quotes=('"',),
    rust_literals=True,
)
ELIXIR_LANG = Language(
    "Elixir",
    (".ex", ".exs"),
    "#",
    docstring_markers=('"""',),
    # Only a heredoc given to a documentation attribute is documentation.
    docstring_prefix=r"@(?:moduledoc|doc|typedoc|shortdoc)(?:\s*~[A-Za-z]\w*)?",
    docstring_heredoc=True,
)
JAVASCRIPT_LANG = Language(
    "JavaScript",
    (".js", ".mjs", ".cjs"),
    "//",
    block_comment_start="/*",
    block_comment_end="*/",
    multiline_quotes=("`",),
    regex_literals=True,
)
TYPESCRIPT_LANG = Language(
    "TypeScript",
    (".ts", ".tsx", ".mts", ".cts"),
    "//",
    block_comment_start="/*",
    block_comment_end="*/",
    multiline_quotes=("`",),
    regex_literals=True,
)
SWIFT_LANG = Language(
    "Swift",
    (".swift",),
    "//",
    block_comment_start="/*",
    block_comment_end="*/",
    quotes=('"',),
    multiline_quotes=('"""',),
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
    TYPESCRIPT_LANG,
    SWIFT_LANG,
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
#   Line Classification
# ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Span:
    """A comment or string literal, which may run on past the line it starts on.

    *end* finds the terminator in its group "end"; other matches (escapes) are skipped.
    """

    end: re.Pattern[str]
    is_code: bool


@dataclass
class _ScanState:
    """What carries over from one line of a file to the next."""

    open_span: _Span | None = None  # the comment or string still open
    depth: int = 0  # brackets still open (tracked where docstrings need it)
    continued: bool = False  # the line before ended with a backslash continuation


# Keywords after which a "/" starts a regex literal rather than a division.
_REGEX_KEYWORDS = frozenset(
    "return typeof instanceof in of new delete void throw case do else yield await".split()
)
# The rest of a regex literal after its opening "/": escapes, [classes], other text.
# No part of it runs past an unescaped "/" (not even a class, where JavaScript allows
# one), so each attempt stops at the next slash and a minified file (one huge line,
# many slashes) still scans in linear time. A regex such as /[/]/ is then just read
# as ordinary code.
_REGEX_BODY = re.compile(r"(?:\\.|\[(?:\\.|[^\]\\/])*\]|[^/\\\[])+/")
_TRAILING_WORD = re.compile(r"[\w$]+$")
# How much of the line before a "/" to look at: enough for the longest keyword above.
_REGEX_LOOKBEHIND = 40


# ----------------------------------------------------------------------------------------
def _starts_regex(line: str, slash: int) -> bool:
    """Whether the "/" at index slash of line starts a regex literal, not a division.

    The usual heuristic: a regex goes where an operand can, so after an operator,
    punctuation, a keyword such as `return`, or at the start of a line; a division
    follows an operand (a name, a number, a closing bracket or quote).
    """
    before = line[max(0, slash - _REGEX_LOOKBEHIND) : slash].rstrip()
    if not before:
        return True
    word = _TRAILING_WORD.search(before)
    if word is not None:
        return word.group() in _REGEX_KEYWORDS
    return before[-1] not in ")]}'\"`" and not before.endswith(("++", "--"))


# ----------------------------------------------------------------------------------------
def _escapable_end(delimiter: str) -> re.Pattern[str]:
    """Match a closing delimiter, stepping over backslash escapes such as \\" first."""
    return re.compile(r"(?P<esc>\\.)|(?P<end>" + re.escape(delimiter) + ")")


# ----------------------------------------------------------------------------------------
def _plain_end(delimiter: str) -> re.Pattern[str]:
    """Match a closing delimiter that a backslash can't escape."""
    return re.compile("(?P<end>" + re.escape(delimiter) + ")")


# ----------------------------------------------------------------------------------------
def _span_end(span: _Span, line: str, pos: int) -> int:
    """Return the index just past the span's terminator in line, or -1 if it isn't there."""
    for match in span.end.finditer(line, pos):
        if match.group("end") is not None:
            return match.end()
    return -1


# ----------------------------------------------------------------------------------------
class _LineClassifier:
    """Decides which lines of a file count as code, for one language.

    Each line is scanned left to right for the start of a comment or string, so markers
    are found anywhere on a line, not only at its start or end. String literals are
    stepped over as code, so a comment or docstring marker inside one isn't taken for a
    real one. A line counts as code when anything outside comments and docstrings is on
    it, or when it holds a line comment with words in it (a separator comment such as
    "# ------" doesn't count). Block comments and docstrings never count.
    """

    # ------------------------------------------------------------------------------------
    def __init__(self, lang: Language) -> None:
        self._spans: dict[str, dict[str, _Span]] = {
            "block_comment": {},
            "docstring": {},
            "code_string": {},
            "multiline_string": {},
        }
        self._raw_strings: dict[str, _Span] = {}
        self._docstring_prefix = re.compile(lang.docstring_prefix)
        # The token kind each named group of the token pattern stands for.
        self._kinds: dict[str, str] = {}
        alternatives: list[str] = []

        def add(kind: str, literal: str, rest: str = "") -> None:
            # Every alternative starts with a plain character, which lets the regex
            # engine skip straight to where a token could begin. Alternatives sharing
            # a first character are added longest first (""" before ").
            name = f"t{len(self._kinds)}"
            self._kinds[name] = kind
            head, tail = re.escape(literal[0]), re.escape(literal[1:])
            alternatives.append(f"{head}(?P<{name}>{tail}{rest})")

        add("line_comment", lang.line_comment)
        # Outside a string, a backslash escapes the next character: in a JavaScript
        # regex literal such as /\/*$/ the "/*" isn't a comment.
        add("escape", "\\", ".")

        if lang.block_comment_start and lang.block_comment_end:
            add("block_comment", lang.block_comment_start)
            span = _Span(_plain_end(lang.block_comment_end), is_code=False)
            self._spans["block_comment"][lang.block_comment_start] = span

        for marker in lang.docstring_markers:
            if lang.docstring_heredoc:
                add("docstring", marker, r"(?=\s*$)")
                end = re.compile(r"^\s*(?P<end>" + re.escape(marker) + ")")
            else:
                add("docstring", marker)
                end = _escapable_end(marker)
            self._spans["docstring"][marker] = _Span(end, is_code=False)
            # The same marker out of docstring position starts an ordinary string.
            self._spans["code_string"][marker] = _Span(end, is_code=True)

        if lang.rust_literals:
            for prefix in ("r", "br", "cr"):
                add("raw_string", prefix, '#*"')
            add(
                "char",
                "'",
                r"(?:[^\\']|\\(?:x[0-9A-Fa-f]{2}|u\{[0-9A-Fa-f]{1,6}\}|.))'",
            )

        multiline = self._spans["multiline_string"]
        for q in lang.multiline_quotes:
            multiline[q] = _Span(_escapable_end(q), is_code=True)
        for q in lang.raw_multiline_quotes:
            multiline[q] = _Span(_plain_end(q), is_code=True)
        for q in sorted(multiline, key=len, reverse=True):
            add("multiline_string", q)

        # An ordinary string ends on its own line (or with it, if unterminated), so
        # the token takes in the whole literal.
        for q in lang.quotes:
            eq = re.escape(q)
            add("string", q, f"(?:[^{eq}\\\\]|\\\\.)*(?:{eq}|\\\\?$)")

        if lang.regex_literals:
            add("regex", "/")  # after "//" and "/*", which stay comments

        self._token = re.compile("|".join(alternatives))
        # Python docstrings must be statements, so brackets and continuations matter.
        self._track_depth = bool(lang.docstring_markers) and not lang.docstring_heredoc

    # ------------------------------------------------------------------------------------
    def code_flags(self, lines: Iterable[str]) -> Iterator[bool]:
        """Yield, for each line of a file in turn, whether it counts as code."""
        state = _ScanState()
        for line in lines:
            yield self._scan_line(line, state)

    # ------------------------------------------------------------------------------------
    def _scan_line(self, line: str, state: _ScanState) -> bool:
        """Classify one line, updating the state carried on to the next line.

        Returns whether the line counts as code.
        """
        has_code = False
        pos = 0
        span = state.open_span
        if span is not None:
            end = _span_end(span, line, 0)
            inside = line if end < 0 else line[:end]
            has_code = span.is_code and bool(inside.strip())
            if end < 0:
                return has_code
            pos = end
            state.open_span = None

        # A docstring can only be the first thing on a line that starts a statement.
        docstring_position = span is None and state.depth == 0 and not state.continued
        state.continued = False
        track_depth = self._track_depth
        while True:
            match = self._token.search(line, pos)
            segment = line[pos : len(line) if match is None else match.start()]
            if track_depth and segment:
                # Brackets in code text; those in strings and comments don't count.
                state.depth += (
                    segment.count("(")
                    + segment.count("[")
                    + segment.count("{")
                    - segment.count(")")
                    - segment.count("]")
                    - segment.count("}")
                )
                if state.depth < 0:
                    state.depth = 0
            if match is None:
                if track_depth:
                    state.continued = line.rstrip().endswith("\\")
                return has_code or bool(segment.strip())

            kind = self._kinds[match.lastgroup or ""]
            before = segment.strip()
            if kind == "docstring" and not (
                docstring_position and self._docstring_prefix.fullmatch(before)
            ):
                # Not where a docstring goes (e.g. `x = """...`): an ordinary string.
                kind = "code_string"
            if before and kind != "docstring":
                has_code = True
            docstring_position = False

            if kind == "line_comment":
                comment = line[match.end() :]
                return has_code or any(ch.isalnum() for ch in comment)
            if kind in ("string", "escape", "char", "regex"):
                has_code = True
                pos = match.end()
                if kind == "regex" and _starts_regex(line, match.start()):
                    body = _REGEX_BODY.match(line, pos)
                    if body is not None:
                        pos = body.end()
                continue

            # A block comment, docstring or multi-line string: it may end on this line,
            # or carry on into the next.
            span = self._span(kind, match.group())
            has_code = has_code or span.is_code
            end = _span_end(span, line, match.end())
            if end < 0:
                state.open_span = span
                return has_code
            pos = end

    # ------------------------------------------------------------------------------------
    def _span(self, kind: str, delimiter: str) -> _Span:
        """Return the span a token of this kind starts."""
        if kind != "raw_string":
            return self._spans[kind][delimiter]
        # Rust raw string: r#"..."# ends with a quote and the same number of hashes.
        terminator = '"' + "#" * delimiter.count("#")
        span = self._raw_strings.get(terminator)
        if span is None:
            span = _Span(_plain_end(terminator), is_code=True)
            self._raw_strings[terminator] = span
        return span


# ----------------------------------------------------------------------------------------
@cache
def _classifier(lang: Language) -> _LineClassifier:
    """Return the line classifier for a language, building it on first use."""
    return _LineClassifier(lang)


# ----------------------------------------------------------------------------------------
#   Functions
# ----------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------
def _warn(message: str) -> None:
    """Print a warning to stderr."""
    print(f"codesize: warning: {message}", file=sys.stderr)


# ----------------------------------------------------------------------------------------
def _warn_unreadable_dir(error: OSError) -> None:
    """os.walk error handler: report a directory that can't be listed, then carry on."""
    _warn(f"could not read {error.filename}: {error.strerror or error}")


# ----------------------------------------------------------------------------------------
def _read_regular_file(filepath: Path) -> tuple[str, int] | None:
    """Return a file's text and size in bytes, or None if it is to be skipped.

    Symlinks are followed. Anything that isn't a regular file (a FIFO, socket or
    device) is skipped without being opened: reading one can block forever or never
    reach the end. A file that can't be read is skipped with a warning, rather than
    quietly counted as empty.
    """
    try:
        st = filepath.stat()
        if not stat.S_ISREG(st.st_mode):
            return None
        return filepath.read_text(encoding="utf-8", errors="replace"), st.st_size
    except FileNotFoundError:
        return None  # a dangling symlink, or removed since the directory was listed
    except OSError as e:
        _warn(f"could not read {filepath}: {e.strerror or e}")
        return None


# ----------------------------------------------------------------------------------------
def count_lines(filepath: Path, lang: Language) -> tuple[int, int]:
    """
    Count total lines and code lines in a file.

    Handles single-line comments, block comments, docstrings/heredocs and string
    literals according to the language configuration. A file that isn't a regular
    file, or can't be read, counts as empty.

    Returns:
        Tuple of (total_lines, code_lines).
    """
    source = _read_regular_file(filepath)
    if source is None:
        return 0, 0
    return _count_lines_from_content(source[0], lang)


# ----------------------------------------------------------------------------------------
def _count_lines_from_content(content: str, lang: Language) -> tuple[int, int]:
    """Count total and code lines from a content string (file already read).

    Lines end at "\\n" only. Files are read with universal newlines, so "\\r\\n" and "\\r"
    endings arrive as "\\n"; characters such as form feeds and U+2028, which
    str.splitlines() would also break on, stay part of their line, as in wc -l.
    """
    lines = content.split("\n")
    if lines[-1] == "":
        lines.pop()  # the newline that ends the last line doesn't start another
    return len(lines), sum(_classifier(lang).code_flags(lines))


# ----------------------------------------------------------------------------------------
def _record_file(
    lang: Language, lang_stats: dict[str, LangStats], content: str, size: int
) -> None:
    """Record statistics for a single file into lang_stats."""
    if lang.name not in lang_stats:
        lang_stats[lang.name] = LangStats(name=lang.name)
    stats = lang_stats[lang.name]
    lines, code = _count_lines_from_content(content, lang)
    stats.num_files += 1
    stats.total_bytes += size
    stats.total_lines += lines
    stats.code_lines += code


# ----------------------------------------------------------------------------------------
def _load_gitignore(gitignore_path: Path) -> GitIgnoreSpec | None:
    """Load and compile a .gitignore file. Returns None if it can't be read.

    A line that isn't a valid pattern (a lone "!", say) is skipped with a warning
    rather than failing the scan; git itself treats such a line as matching nothing.
    """
    source = _read_regular_file(gitignore_path)
    if source is None:
        return None
    patterns: list[GitIgnoreSpecPattern] = []
    # Like git, split on newlines only (see _count_lines_from_content)
    for line_number, line in enumerate(source[0].split("\n"), start=1):
        if not line:
            continue
        try:
            patterns.append(GitIgnoreSpecPattern(line))
        except GitIgnorePatternError:
            _warn(
                f"ignoring invalid pattern on line {line_number} of "
                f"{gitignore_path}: {line!r}"
            )
    return GitIgnoreSpec(patterns)


# ----------------------------------------------------------------------------------------
def _is_ignored(
    name: str,
    specs: list[tuple[GitIgnoreSpec, str]],
    *,
    is_dir: bool,
) -> bool:
    """Return True if name (relative to its parent dir) is ignored by the specs.

    *specs* is a list of (spec, rel_prefix) pairs, outermost .gitignore first, where
    rel_prefix is the posix-style relative path from the spec's base directory to the
    current directory (empty string if same, otherwise ends with "/"). Callers
    precompute this once per directory to avoid repeating `relative_to` work per file.

    As in git, the deepest .gitignore with a pattern matching the path decides, so a
    negation there (`!important.py`) re-includes a file an outer .gitignore ignores.
    Within one file, the last matching pattern wins.
    """
    suffix = "/" if is_dir else ""
    for spec, prefix in reversed(specs):
        include = spec.check_file(prefix + name + suffix).include
        if include is not None:
            return include
    return False


# ----------------------------------------------------------------------------------------
def scan_directory(
    directory: Path,
    *,
    respect_gitignore: bool = True,
    sort_by: SortKey = "code",
) -> CodeStats:
    """
    Scan a directory recursively for code files and collect statistics.

    Uses os.walk with hidden-directory pruning for fast traversal. Skips
    directories starting with a dot (e.g. .venv, .git). Only includes
    languages that have at least one file.

    When respect_gitignore is True (default), .gitignore files found in
    the tree are applied; ignored files and directories are skipped.

    Only regular files are read (FIFOs, sockets and devices are skipped).
    A directory or file that can't be read is reported on stderr and left
    out, so the totals cover everything else.

    .h files are disambiguated as C or Objective-C using these signals
    (in priority order):
      1. Content tokens (e.g. @interface, #import) → Objective-C
      2. Companion .m or .mm in same dir with same basename → Objective-C
      3. Companion .c in same dir with same basename → C
      4. Any .m/.mm in the scanned tree → Objective-C
      5. Otherwise → C

    Args:
        directory: The directory to scan.
        respect_gitignore: If True, honour .gitignore files found in the tree.

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
    # (path, content, size) of each .h file, classified once the walk is done
    deferred_h_files: list[tuple[Path, str, int]] = []
    # (dir, basename) -> language of the companion source file (C_LANG or OBJC_LANG)
    companion_langs: dict[tuple[Path, str], Language] = {}
    active_specs: list[tuple[Path, GitIgnoreSpec]] = []

    for dirpath, dirnames, filenames in os.walk(
        directory, onerror=_warn_unreadable_dir
    ):
        current = Path(dirpath)

        current_specs: list[tuple[GitIgnoreSpec, str]] = []
        if respect_gitignore:
            # Drop specs whose base is no longer an ancestor (os.walk may have
            # jumped to a sibling branch).
            active_specs = [
                (base, spec)
                for base, spec in active_specs
                if base == current or base in current.parents
            ]
            if ".gitignore" in filenames:
                spec = _load_gitignore(current / ".gitignore")
                if spec is not None:
                    active_specs.append((current, spec))
            # Precompute relative prefixes once per (dir, spec) so _is_ignored
            # only has to concat basenames.
            for base, spec in active_specs:
                if base == current:
                    current_specs.append((spec, ""))
                else:
                    current_specs.append(
                        (spec, current.relative_to(base).as_posix() + "/")
                    )

        # Prune hidden directories in-place so os.walk doesn't descend into them
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".") and not _is_ignored(d, current_specs, is_dir=True)
        ]

        for filename in filenames:
            if _is_ignored(filename, current_specs, is_dir=False):
                continue

            filepath = Path(dirpath, filename)
            ext = filepath.suffix

            if ext == ".h":
                # Defer until we've seen all companions
                source = _read_regular_file(filepath)
                if source is not None:
                    deferred_h_files.append((filepath, *source))
                continue

            lang = extension_map.get(ext)
            if lang is None:
                continue

            # Skip TypeScript declaration files — auto-generated, not hand-written code.
            if lang is TYPESCRIPT_LANG and filename.endswith(
                (".d.ts", ".d.cts", ".d.mts")
            ):
                continue

            if lang is OBJC_LANG:
                # .m/.mm wins over .c if both somehow exist for same basename
                companion_langs[(filepath.parent, filepath.stem)] = OBJC_LANG
            elif lang is C_LANG:
                companion_langs.setdefault((filepath.parent, filepath.stem), C_LANG)

            source = _read_regular_file(filepath)
            if source is not None:
                _record_file(lang, lang_stats, *source)

    # Now process .h files with full project knowledge
    has_objc_impl = any(v is OBJC_LANG for v in companion_langs.values())
    for filepath, content, size in deferred_h_files:
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
        _record_file(lang, lang_stats, content, size)

    return CodeStats(languages=_sort_languages(lang_stats.values(), sort_by))


# ----------------------------------------------------------------------------------------
def _sort_languages(stats: Iterable[LangStats], sort_by: SortKey) -> list[LangStats]:
    """Sort a collection of LangStats. Numeric keys descend; name ascends."""
    if sort_by == "name":
        return sorted(stats, key=lambda s: s.name)
    numeric_keys: dict[SortKey, Callable[[LangStats], int]] = {
        "code": lambda s: s.code_lines,
        "files": lambda s: s.num_files,
        "size": lambda s: s.total_bytes,
        "lines": lambda s: s.total_lines,
    }
    return sorted(stats, key=numeric_keys[sort_by], reverse=True)
