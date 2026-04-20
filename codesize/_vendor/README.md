# Vendored packages

## pathspec

- Upstream: https://github.com/cpburnz/python-pathspec
- Version: 1.0.4
- Licence: Mozilla Public License 2.0 (see `pathspec/LICENSE`)

Used for parsing `.gitignore` files during directory scans.

### Modifications

The following changes were made to the vendored copy (per MPL 2.0 section 3.3):

- **Imports rewritten from absolute to relative.** Upstream uses `from pathspec
  import util` / `from pathspec.X import ...`. These were converted to relative
  imports (`from . import util`, `from .X import ...`, etc.) so that the
  vendored copy is self-contained and does not fall through to any
  site-installed `pathspec` package.

No other changes were made. The vendored files retain their original MPL 2.0
licence; the surrounding codesize project is otherwise Unlicensed (public
domain).
