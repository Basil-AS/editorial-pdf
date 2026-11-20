# Editorial PDF Codex plugin

This Codex marketplace plugin bundles two skills:

- `editorial-pdf` for creating and reviewing polished PDF reports from Markdown.
- `gost-rf-pdf` for GOST source lookup, edition-status tracking and the GOST 7.32 PDF profile.

The skill sources live in the repository root and `variants/gost-rf-pdf`. Run `python scripts/sync_codex_marketplace.py` from the repository root to refresh this checked-in package. CI checks that the bundled skill files remain synchronized.

The PDF builders use the Python packages in each skill's `requirements.txt`; PDF output also requires the documented Pandoc, XeLaTeX, fonts and Poppler tools.
