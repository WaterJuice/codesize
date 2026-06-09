# ----------------------------------------------------------------------------------------
#   output.py
#   ---------
#
#   Output formatting with ASCII box and optional ANSI colour support.
#   Displays per-language breakdown and totals.
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

import json
import sys
from pathlib import Path
from typing import Literal
from codesize.scanner import CodeStats
from codesize.scanner import LangStats

# ----------------------------------------------------------------------------------------
#   Constants
# ----------------------------------------------------------------------------------------

# ANSI colour codes
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"

# Column colours (Files, Size, Lines, Code)
COL_COLOURS = (CYAN, GREEN, YELLOW, MAGENTA)

# Box drawing characters
BOX_TOP_LEFT = "╭"
BOX_TOP_RIGHT = "╮"
BOX_BOTTOM_LEFT = "╰"
BOX_BOTTOM_RIGHT = "╯"
BOX_HORIZONTAL = "─"
BOX_VERTICAL = "│"
BOX_TEE_LEFT = "├"
BOX_TEE_RIGHT = "┤"

# ----------------------------------------------------------------------------------------
#   Functions
# ----------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------
def use_colour() -> bool:
    """Determine if ANSI colour should be used."""
    return sys.stdout.isatty()


# ----------------------------------------------------------------------------------------
def colour(text: str, *codes: str) -> str:
    """Apply ANSI colour codes to text if output is a terminal."""
    if not use_colour():
        return text
    return "".join(codes) + text + RESET


# ----------------------------------------------------------------------------------------
def format_size(kb: float) -> str:
    """Format size with appropriate unit."""
    if kb >= 1024:
        return f"{kb / 1024:.2f} MB"
    return f"{kb:.2f} KB"


# ----------------------------------------------------------------------------------------
def format_number(n: int) -> str:
    """Format number with thousand separators."""
    return f"{n:,}"


# ----------------------------------------------------------------------------------------
def display_stats(
    stats: CodeStats, directory: Path, output_format: Literal["box", "plain", "json"]
) -> None:
    """Display statistics in the specified format."""
    if output_format == "json":
        display_json(stats, directory)
    elif output_format == "plain":
        display_plain(stats, directory)
    else:
        display_box(stats, directory)


# ----------------------------------------------------------------------------------------
def _lang_to_dict(lang: LangStats) -> dict[str, int | float]:
    """Convert language stats to a dictionary for JSON output."""
    return {
        "files": lang.num_files,
        "total_bytes": lang.total_bytes,
        "total_kb": round(lang.total_kb, 2),
        "total_lines": lang.total_lines,
        "code_lines": lang.code_lines,
    }


# ----------------------------------------------------------------------------------------
def display_json(stats: CodeStats, directory: Path) -> None:
    """Display statistics as JSON."""
    data: dict[str, object] = {
        "directory": directory.name,
        "languages": {lang.name: _lang_to_dict(lang) for lang in stats.languages},
    }
    if len(stats.languages) > 1:
        data["total"] = _lang_to_dict(stats.total)
    print(json.dumps(data, indent=2))


# ----------------------------------------------------------------------------------------
def display_plain(stats: CodeStats, directory: Path) -> None:
    """Display statistics as plain text."""
    print(f"Code Stats: {directory.name}")
    if not stats.languages:
        print("No supported code files found.")
        return
    for lang in stats.languages:
        print(
            f"{lang.name}: {format_number(lang.num_files)} files, "
            f"{format_size(lang.total_kb)}, "
            f"{format_number(lang.total_lines)} lines, "
            f"{format_number(lang.code_lines)} code lines"
        )
    if len(stats.languages) > 1:
        total = stats.total
        print(
            f"Total: {format_number(total.num_files)} files, "
            f"{format_size(total.total_kb)}, "
            f"{format_number(total.total_lines)} lines, "
            f"{format_number(total.code_lines)} code lines"
        )


# ----------------------------------------------------------------------------------------
def display_box(stats: CodeStats, directory: Path) -> None:
    """Display statistics in a formatted ASCII box with per-language breakdown."""
    if not stats.languages:
        print()
        print("No supported code files found.")
        print()
        return

    title = f" Code Stats: {directory.name} "
    show_total = len(stats.languages) > 1

    # Build data rows: (label, files, size, lines, code)
    headers = ("", "Files", "Size", "Lines", "Code")
    rows: list[tuple[str, ...]] = []
    for lang in stats.languages:
        rows.append(
            (
                lang.name,
                format_number(lang.num_files),
                format_size(lang.total_kb),
                format_number(lang.total_lines),
                format_number(lang.code_lines),
            )
        )

    total = stats.total
    total_row = (
        "Total",
        format_number(total.num_files),
        format_size(total.total_kb),
        format_number(total.total_lines),
        format_number(total.code_lines),
    )

    all_rows = list(rows)
    if show_total:
        all_rows.append(total_row)

    # Calculate column widths
    num_cols = len(headers)
    col_widths: list[int] = []
    for i in range(num_cols):
        w = len(headers[i])
        for r in all_rows:
            w = max(w, len(r[i]))
        col_widths.append(w)

    # Format a content line (plain text, no borders or colours)
    def make_line(row: tuple[str, ...]) -> str:
        parts = [f"  {row[0].ljust(col_widths[0])}"]
        for i in range(1, num_cols):
            parts.append(f"  {row[i].rjust(col_widths[i])}")
        parts.append("  ")
        return "".join(parts)

    # Calculate inner width (between vertical bars)
    all_lines = [make_line(r) for r in all_rows] + [make_line(headers)]
    inner_width = max(len(title), max(len(s) for s in all_lines))

    # Box parts
    top_border = BOX_TOP_LEFT + BOX_HORIZONTAL * inner_width + BOX_TOP_RIGHT
    bottom_border = BOX_BOTTOM_LEFT + BOX_HORIZONTAL * inner_width + BOX_BOTTOM_RIGHT
    separator = BOX_TEE_LEFT + BOX_HORIZONTAL * inner_width + BOX_TEE_RIGHT

    # Print header
    print()
    print(colour(top_border, BOLD))

    # Title line
    title_padded = title.center(inner_width)
    print(
        colour(BOX_VERTICAL, BOLD)
        + colour(title_padded, BOLD, CYAN)
        + colour(BOX_VERTICAL, BOLD)
    )

    # Separator
    print(colour(separator, BOLD))

    # Header row
    header_line = make_line(headers).ljust(inner_width)
    if use_colour():
        print(
            colour(BOX_VERTICAL, BOLD)
            + colour(header_line, BOLD)
            + colour(BOX_VERTICAL, BOLD)
        )
    else:
        print(BOX_VERTICAL + header_line + BOX_VERTICAL)

    # Data rows (language rows + optional total)
    def print_data_row(row: tuple[str, ...], bold_label: bool = False) -> None:
        plain = make_line(row)
        padded = plain.ljust(inner_width)
        if use_colour():
            # Label column
            label = row[0].ljust(col_widths[0])
            if bold_label:
                label = colour(label, BOLD)
            # Value columns — each gets its own colour
            values = ""
            for i in range(1, num_cols):
                col_colour = COL_COLOURS[(i - 1) % len(COL_COLOURS)]
                values += "  " + colour(row[i].rjust(col_widths[i]), BOLD, col_colour)
            values += "  "
            # Trailing padding to match inner_width
            visible_len = (
                2
                + col_widths[0]
                + sum(2 + col_widths[i] for i in range(1, num_cols))
                + 2
            )
            padding = " " * max(0, inner_width - visible_len)
            print(
                colour(BOX_VERTICAL, BOLD)
                + f"  {label}{values}{padding}"
                + colour(BOX_VERTICAL, BOLD)
            )
        else:
            print(BOX_VERTICAL + padded + BOX_VERTICAL)

    for row in rows:
        print_data_row(row)

    # Total row (only if multiple languages)
    if show_total:
        print(colour(separator, BOLD))
        print_data_row(total_row, bold_label=True)

    # Footer
    print(colour(bottom_border, BOLD))
    print()
