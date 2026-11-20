# Markdown builder

Use Python 3.10+ with `markdown-it-py`, `beautifulsoup4`, `playwright>=1.42`, and `pypdf>=6`. Reuse available dependencies. If needed, install in a virtual environment and provision Chromium.

```bash
python -m pip install markdown-it-py beautifulsoup4 'playwright>=1.42' 'pypdf>=6'
python -m playwright install chromium
```

Use `--channel msedge` for a compatible installed Edge channel or `--browser-executable /path/to/chromium` for a compatible local Chromium. On Linux, install the Playwright OS dependencies if launch reports missing libraries. For reproducible output, keep the browser version and local fonts consistent. Install Noto or DejaVu families for Cyrillic as needed. Set `--lang ru` for Russian callout labels and running page numbers. Other languages use English labels by default.

- CommonMark and pipe tables are supported. Raw HTML is printed as text. Use GitHub callouts with `> [!NOTE]`, `TIP`, `IMPORTANT`, `WARNING`, or `CAUTION` on a marker line followed by quoted Markdown.
- Use standard Markdown image syntax with paths relative to the Markdown file. An optional `--diagrams-dir` provides a second root and preserves subdirectories. Supported assets include SVG, PNG, JPEG, WebP and GIF. A local HTML image must contain exactly one static SVG. Export self-contained SVGs with a viewBox and embedded or outlined assets as needed. Use a short adjacent paragraph for visible captions.
- Use explicit Markdown links for HTTP(S), mail, or headings. Heading anchors lowercase the text, replace spaces with hyphens, and strip punctuation except hyphens and underscores. Duplicate headings get `-2`, `-3`, and so on. Use `--companion-root` pointing to the output directory to opt into links to existing companion files there. Ship the same folder layout and test links in the recipient's viewer. Local image assets are embedded and need no companion files.
- Use `--paper Letter` when required. Use `--title` for metadata and `--header ""` to suppress the running title. Use `--css` for a complete replacement stylesheet with local fonts. Page sizes and margins come from the print settings.
- Use Poppler `pdftoppm`, `pdftotext -layout`, and `pdfinfo` to check the printed result. If a row or figure is taller than the printable area, redesign it, split it logically, or use a larger page. Validate required font coverage, vector fidelity and readability in the rendered result.
