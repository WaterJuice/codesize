# ----------------------------------------------------------------------------------------
#   __init__.py
#   -----------
#
#   codesize package initialisation.
#
#   (c) 2026 WaterJuice — Unlicense; see LICENSE in the project root.
#
#   Version History
#   ---------------
#   Mar 2026 - Created
# ----------------------------------------------------------------------------------------

"""codesize: A CLI tool to analyse code statistics in a directory.

Supports Python, Go, Rust, Elixir, JavaScript, TypeScript, C, and Objective-C.
Honours .gitignore files by default.
"""

from codesize.version import VERSION_STR

__all__ = ["__version__"]

__version__ = VERSION_STR
