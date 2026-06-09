# codesize 1.4.2 - 9 Jun 2026

Restores the solid box border in the default output.

## Fix

- The horizontal box rule is once again a solid line (`─`, U+2500) instead of an
  ASCII hyphen (`-`), which had rendered as a dashed border in 1.4.1. The
  character was inadvertently mangled to a hyphen during an earlier history
  rewrite; the other box-drawing glyphs were unaffected.


# codesize 1.4.1 - 30 May 2026

Moved to new GitHub location: https://github.com/WaterJuice/codesize

# codesize 1.4.0 - 8 May 2026

Adds TypeScript as a supported language.

## New Language

- TypeScript (`.ts`, `.tsx`, `.mts`, `.cts`)

`.d.ts` (and `.d.cts`, `.d.mts`) declaration files are skipped — they're auto-generated and don't represent hand-written code.


# codesize 1.3.0 - 21 Apr 2026

Languages are now sorted by size in the output, with a `--sort` flag to pick
a different field.

## Sorting

- The languages list is sorted **biggest first by code lines** by default
  (previously: definition order).
- New `--sort {code,files,size,lines,name}` flag picks the sort field.
  Numeric fields sort descending; `name` sorts alphabetically ascending.


# codesize 1.2.0 - 20 Apr 2026

Honours `.gitignore` files during directory scans.

## Gitignore Support

- `.gitignore` files found anywhere in the scanned tree are now honoured by default. Both files and directories matched by gitignore patterns are skipped — pruned directories aren't even descended into.
- Subdirectory `.gitignore` files apply only to their own subtree (matching git's semantics).
- Negation patterns (`!foo`), anchored patterns (`/foo`), directory-only patterns (`foo/`), and `**` globs all work.
- Pass `--no-gitignore` to disable and scan everything.

## Vendored Dependency

Gitignore parsing is provided by a vendored copy of [pathspec 1.0.4](https://github.com/cpburnz/python-pathspec) (MPL-2.0), living under `codesize/_vendor/pathspec/`. This keeps the "zero runtime dependencies" guarantee and pins the exact bytes shipped to users — no supply-chain surprises from upstream changes.

The project licence expression is now `Unlicense AND MPL-2.0`; see the top-level `NOTICE` file for details. All codesize-authored files remain Unlicensed (public domain).


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
