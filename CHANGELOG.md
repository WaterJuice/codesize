# codesize 1.0.0 Beta 1 — 28 Mar 2026

First stable release.

A simple CLI tool to analyse code statistics in a directory.

## Features

- Recursive scanning for Python, Go, Rust, and Elixir files
- Per-language breakdown with file count, total size, total lines, and code lines
- Combined totals when multiple languages are present
- Only shows languages that have files
- Three output formats: ASCII box (default), plain text (`--plain`), and JSON (`--json`)

- Zero external dependencies — Python 3.12+ stdlib only
