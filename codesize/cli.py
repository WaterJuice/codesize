# ----------------------------------------------------------------------------------------
#   cli.py
#   ------
#
#   Command-line interface entry point for codesize. Supports Python, Go,
#   Rust, Elixir, JavaScript, C, and Objective-C.
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

import sys
import traceback
from pathlib import Path
from codesize.output import display_stats
from codesize.scanner import scan_directory
from codesize.version import VERSION_STR
from .argbuilder import ArgsParser
from .argbuilder import Namespace

# ----------------------------------------------------------------------------------------
#   Constants
# ----------------------------------------------------------------------------------------

LICENSE_TEXT = """\
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org>"""

# ----------------------------------------------------------------------------------------
#   Functions
# ----------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------
def parse_args(argv: list[str]) -> Namespace:
    """Parse command-line arguments."""
    p = ArgsParser(
        prog="codesize",
        description=(
            f"codesize: {VERSION_STR}\n"
            "(c) 2026 WaterJuice. Unlicense.\n\n"
            "Analyse code statistics in a directory.\n"
            "Supports Python, Go, Rust, Elixir, JavaScript, C, and Objective-C."
        ),
        version=f"codesize: {VERSION_STR}\npython: {sys.version.split()[0]}",
    )
    p.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    p.add_argument(
        "--license",
        action="version",
        version=LICENSE_TEXT,
        help="show license and exit",
    )
    p.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Don't honour .gitignore files found in the tree",
    )

    # Output format options (mutually exclusive)
    format_group = p.add_mutex_group()
    format_group.add_argument(
        "--plain",
        action="store_true",
        help="Plain text output (no box or colours)",
    )
    format_group.add_argument(
        "--json",
        action="store_true",
        help="JSON output",
    )

    return p.parse(argv)


# ----------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for the codesize CLI.

    Parameters:
        argv: Command line arguments (without program name). If None, uses sys.argv[1:].

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if argv is None:
        argv = sys.argv[1:]

    try:
        return _main_inner(argv)
    except KeyboardInterrupt:
        print()
        print("---- Manually Terminated ----")
        print()
        return 1
    except SystemExit:
        raise
    except BaseException as e:
        t = "-----------------------------------------------------------------------------\n"
        t += "UNHANDLED EXCEPTION OCCURRED!!\n"
        t += "\n"
        t += traceback.format_exc()
        t += "\n"
        t += f"EXCEPTION: {type(e)} {e}\n"
        t += "-----------------------------------------------------------------------------\n"
        t += "\n"
        print(t, file=sys.stderr)
        return 1


# ----------------------------------------------------------------------------------------
def _main_inner(argv: list[str]) -> int:
    """Inner main function that does the actual work."""
    args = parse_args(argv)
    directory = Path(args.directory).resolve()

    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist.", file=sys.stderr)
        return 1

    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.", file=sys.stderr)
        return 1

    # Determine output format
    if args.json:
        output_format = "json"
    elif args.plain:
        output_format = "plain"
    else:
        output_format = "box"

    stats = scan_directory(directory, respect_gitignore=not args.no_gitignore)
    display_stats(stats, directory, output_format)
    return 0
