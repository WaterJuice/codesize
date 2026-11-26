# codesize 1.6.0 - 26 Nov 2026

Code-line counts are more accurate, and scans no longer hang, crash or go quiet on unusual
trees. Counts for the same code will differ from 1.5.x, mostly upwards for Python.

## Line Counting

Comment and docstring markers are now found anywhere on a line, not just at its start or
end, and string literals are skipped over so a marker inside a string no longer counts.

- A block comment opened after code (`x = 1; /* note`) no longer makes the lines inside
  it count as code, and code after a comment closes (`/* note */ x = 1;`, `*/ y();`) now
  counts.
- Python: a string opened mid-line (`text = """first`) no longer makes its closing line
  look like a new docstring that swallows the code after it, sometimes the rest of the
  file. One-line `x = """abc"""` assignments, raw `r"""` docstrings, escaped quotes, and
  markers inside comments or strings are all handled.
- Python: only docstrings are excluded, as documented — a triple-quoted string that
  starts a statement. Other multi-line strings (`SQL = """...`, `dedent("""...""")`) are
  code, and every non-blank line in them counts.
- Elixir: only `@moduledoc`, `@doc`, `@typedoc` and `@shortdoc` heredocs are excluded.
  Other heredocs, `~H"""` templates included, count as code.
- Comment markers inside strings, such as CSS comments in a JavaScript template literal or
  a Go raw string, are string content and count as code.
- String syntax is recognised per language: JavaScript/TypeScript regex and template
  literals, Go raw strings, Rust raw strings, chars and lifetimes, and Swift multi-line
  strings.
- Total lines count newlines only, as `wc -l` does. Form feeds, vertical tabs and Unicode
  line separators no longer add lines.

## Scanning

- A negation in a nested `.gitignore` (`!important.py`) now re-includes a file that an
  outer `.gitignore` ignores: the deepest matching `.gitignore` decides, as in git.
- An invalid `.gitignore` line (a lone `!`, say) is skipped with a warning instead of
  aborting the scan with a traceback.
- Only regular files are read. A FIFO, socket or symlink to a device (such as
  `/dev/zero`) with a code extension is skipped; previously the scan hung on it.
- A directory or file that can't be read is reported on stderr and left out of the
  totals. Unreadable directories were skipped silently, and unreadable files were counted
  as empty. Dangling symlinks are skipped.
- Writing to a closed pipe (`codesize | true`) exits with status 1 and no message, instead
  of status 120 with a `BrokenPipeError` message.

## Performance

Line counting does more work per line, so scans take about 10% longer on Python-heavy
trees.

## Internal

Fixes to the bundled argument parser (`argbuilder.py`), none of which affect codesize's
own command line:

- An option's value equal to a command name is no longer taken for the command, and
  nothing after `--` is a command.
- Top-level options placed before a command are kept there, rather than moved after it.
- Help and version requests are recognised from the parser's registered actions,
  replacing a hard-coded `--license` check. `--help-all` is left alone when the
  application defines its own.
- A common collection created after commands were added now applies to those commands too.
- Ungrouped commands get their own heading in `--help`.

# codesize 1.5.1 - 13 Sep 2026

Publishing instructions no longer refer to GitLab Pages; documentation is published to
https://docs.waterjuice.org.

# codesize 1.5.0 - 2 Sep 2026

Adds Swift as a supported language.

## New Language

- Swift (`.swift`)

Swift is handled like the other C-family languages: `//` line comments (`///` doc comments
included) and `/* ... */` block comments are recognised, so blank lines and decorative
comment rules don't count towards the code-line total.

# codesize 1.4.2 - 9 Jun 2026

Restores the solid box border in the default output.

## Fix

- The horizontal box rule is once again a solid line (`─`, U+2500) instead of an ASCII
  hyphen (`-`), which had rendered as a dashed border in 1.4.1. The character was
  inadvertently mangled to a hyphen during an earlier history rewrite; the other
  box-drawing glyphs were unaffected.

# codesize 1.4.1 - 30 May 2026

Moved to new GitHub location: https://github.com/WaterJuice/codesize

# codesize 1.4.0 - 8 May 2026

Adds TypeScript as a supported language.

## New Language

- TypeScript (`.ts`, `.tsx`, `.mts`, `.cts`)

`.d.ts` (and `.d.cts`, `.d.mts`) declaration files are skipped — they're auto-generated
and don't represent hand-written code.

# codesize 1.3.0 - 21 Apr 2026

Languages are now sorted by size in the output, with a `--sort` flag to pick a different
field.

## Sorting

- The languages list is sorted **biggest first by code lines** by default (previously:
  definition order).
- New `--sort {code,files,size,lines,name}` flag picks the sort field. Numeric fields sort
  descending; `name` sorts alphabetically ascending.

# codesize 1.2.0 - 20 Apr 2026

Honours `.gitignore` files during directory scans.

## Gitignore Support

- `.gitignore` files found anywhere in the scanned tree are now honoured by default. Both
  files and directories matched by gitignore patterns are skipped — pruned directories
  aren't even descended into.
- Subdirectory `.gitignore` files apply only to their own subtree (matching git's
  semantics).
- Negation patterns (`!foo`), anchored patterns (`/foo`), directory-only patterns
  (`foo/`), and `**` globs all work.
- Pass `--no-gitignore` to disable and scan everything.

## Vendored Dependency

Gitignore parsing is provided by a vendored copy of
[pathspec 1.0.4](https://github.com/cpburnz/python-pathspec) (MPL-2.0), living under
`codesize/_vendor/pathspec/`. This keeps the "zero runtime dependencies" guarantee and
pins the exact bytes shipped to users — no supply-chain surprises from upstream changes.

The project licence expression is now `Unlicense AND MPL-2.0`; see the top-level `NOTICE`
file for details. All codesize-authored files remain Unlicensed (public domain).

# codesize 1.1.0 - 20 Apr 2026

Adds support for more languages and smarter header-file classification.

## New Languages

- JavaScript (`.js`, `.mjs`, `.cjs`)
- C (`.c`, `.h`)
- Objective-C (`.m`, `.mm`, `.h`)

## `.h` File Disambiguation

`.h` files are auto-classified as C or Objective-C using these signals, in priority order:

1. Content tokens (`@interface`, `@protocol`, `@class`, `@property`, `@end`, `#import`) →
   Objective-C
2. Companion `.m` or `.mm` in same directory with same basename → Objective-C
3. Companion `.c` in same directory with same basename → C
4. Any `.m`/`.mm` present anywhere in the scanned tree → Objective-C
5. Otherwise → C

Only the first ~20 KB of a header is scanned for Objective-C tokens, so large pure-C
headers are not penalised.

## Internal

- Faster directory traversal: `os.walk` with in-place hidden-directory pruning replaces
  `rglob` (avoids descending into `.venv`, `.git`, etc.)
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
