# codesize

A CLI tool to analyse code statistics in a directory. Supports Python, Go, Rust, and Elixir.

## Features

- Recursively scans directories for supported code files
- Per-language breakdown of file count, total size, total lines, and code lines
- Combined totals when multiple languages are present
- Only shows languages that have files
- Beautiful ASCII box output with ANSI colours (when in a terminal)
- Plain text and JSON output formats available

## Installation

```bash
pip install codesize
```

## Quick Start

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

## Output Formats

### Default (ASCII Box)

When running in a terminal, output is displayed in a coloured ASCII box:

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

### Plain Text

Use `--plain` for simple text output without formatting:

```
Code Stats: my-project
Python: 42 files, 128.50 KB, 3,847 lines, 2,691 code lines
Go: 18 files, 65.20 KB, 1,523 lines, 1,210 code lines
Rust: 7 files, 22.00 KB, 580 lines, 445 code lines
Total: 67 files, 215.70 KB, 5,950 lines, 4,346 code lines
```

### JSON

Use `--json` for machine-readable output:

```json
{
  "directory": "my-project",
  "languages": {
    "Python": {
      "files": 42,
      "total_bytes": 131584,
      "total_kb": 128.5,
      "total_lines": 3847,
      "code_lines": 2691
    },
    "Go": {
      "files": 18,
      "total_bytes": 66765,
      "total_kb": 65.2,
      "total_lines": 1523,
      "code_lines": 1210
    },
    "Rust": {
      "files": 7,
      "total_bytes": 22528,
      "total_kb": 22.0,
      "total_lines": 580,
      "code_lines": 445
    }
  },
  "total": {
    "files": 67,
    "total_bytes": 220877,
    "total_kb": 215.7,
    "total_lines": 5950,
    "code_lines": 4346
  }
}
```

## CLI Reference

```
--8<-- "_generated_command_line_help.txt"
```
