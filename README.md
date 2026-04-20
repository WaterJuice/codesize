# codesize

A simple CLI tool that scans directories for code files and displays statistics.
Supports Python, Go, Rust, Elixir, JavaScript, C, and Objective-C.

`.h` files are auto-detected as C or Objective-C based on their content.

## Features

- Recursively scans directories for supported code files
- Reports per-language breakdown:
  - Number of files
  - Total size (KB/MB)
  - Total lines
  - Code lines (excluding blank lines, docstrings, and decorative comments)
- Combined totals when multiple languages are present
- Only shows languages that have files — no clutter
- Beautiful ASCII box output with ANSI colours (when running in a terminal)
- Plain text and JSON output formats available

## Installation

```bash
# Using uv
uv pip install codesize

# Using pip
pip install codesize
```

## Usage

```bash
# Scan current directory
codesize

# Scan a specific directory
codesize /path/to/project

# Plain text output (no box)
codesize --plain

# JSON output
codesize --json
```

### Example Output

```
╭──────────────────────────────────────────────╮
│          Code Stats: my-project              │
│──────────────────────────────────────────────│
│              Files     Size    Lines     Code │
│  Python        42  128.50 KB   3,847    2,691 │
│  Go            18   65.20 KB   1,523    1,210 │
│  Rust           7   22.00 KB     580      445 │
│──────────────────────────────────────────────│
│  Total         67  215.70 KB   5,950    4,346 │
╰──────────────────────────────────────────────╯
```

## Development

```bash
# Set up development environment
make dev

# Run linting and type checks
make check

# Format code
make format

# Build wheel and docs
make build
```

## Publishing

Publishing requires `cal-publish-python` configuration.

```bash
# Build first
make build

# Publish wheel to PyPI and docs to GitLab Pages
make publish
```

## Licence

Unlicense — public domain. See [LICENSE](LICENSE).
