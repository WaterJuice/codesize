# codesize 1.1.0 - 20 Apr 2026

Adds support for more languages and smarter header-file classification.

## New Languages

- JavaScript (`.js`, `.mjs`, `.cjs`)
- C (`.c`, `.h`)
- Objective-C (`.m`, `.mm`, `.h`)

## `.h` File Disambiguation

`.h` files are auto-classified as C or Objective-C using these signals, in priority order:

1. Content tokens (`@interface`, `@protocol`, `@class`, `@property`, `@end`, `#import`) → Objective-C
2. Companion `.m` or `.mm` in same directory with same basename → Objective-C
3. Companion `.c` in same directory with same basename → C
4. Any `.m`/`.mm` present anywhere in the scanned tree → Objective-C
5. Otherwise → C

Only the first ~20 KB of a header is scanned for Objective-C tokens, so large pure-C headers are not penalised.

## Internal

- Faster directory traversal: `os.walk` with in-place hidden-directory pruning replaces `rglob` (avoids descending into `.venv`, `.git`, etc.)
- Header content is read only once — reused for both classification and line counting


# codesize 1.0.0 - 9 Apr 2026

First stable release.

A simple CLI tool to analyse code statistics in a directory.

## Features

- Recursive scanning for Python, Go, Rust, and Elixir files
- Per-language breakdown with file count, total size, total lines, and code lines
- Combined totals when multiple languages are present
- Only shows languages that have files
- Three output formats: ASCII box (default), plain text (`--plain`), and JSON (`--json`)
- Zero external dependencies — Python 3.12+ stdlib only
