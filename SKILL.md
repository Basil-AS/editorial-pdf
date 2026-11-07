---
name: editorial-pdf
description: Use when creating print-quality, structured, and self-contained PDF documents, technical reports, or whitepapers from Markdown, requiring hierarchical PDF bookmarks/outlines, relative link sanitization, inline SVG diagrams, or anti-monolithic formatting.
---

# Editorial PDF

Produce publication-grade, self-contained technical reports and whitepapers from Markdown with clean typographic hierarchy, inline vector diagrams, automated PDF bookmark outlines, and strict relative link sanitization.

## Overview

A technical PDF should look like a professionally typeset publication, not a raw Markdown dump or web page printout. It must be:
- **Paced and readable:** Deconstructed into rhythmic, anti-monolithic blocks (paragraphs ≤ 4–5 lines, comparison tables, alert callouts, inline diagrams).
- **Self-contained:** Zero broken links, zero external CSS/script runtimes, and zero sensitive host/user path leaks (`file:///C:/Users/...`).
- **Navigable:** Features a full hierarchical PDF bookmark tree (Table of Contents outline) matching document chapters and sections.
- **Crisp and vector-sharp:** Diagrams are embedded as inline SVG with responsive viewports, never rasterized to blurry PNGs.

---

## When to Use

Use this skill whenever generating or polishing PDFs for engineering reports, architecture dossiers, executive summaries, or customer-facing documentation:
- When turning detailed Markdown specifications into finalized PDF deliverables.
- When PDF reports require visual diagrams matching the document styling (`diagram-design`).
- When links in the PDF must point relatively to accompanying files (e.g. standalone diagram HTMLs).
- When PDF readers must show a structured chapter tree in the sidebar.
- When documents suffer from dense, monolithic walls of text that cause reader fatigue.

**When NOT to use:**
- Quick raw console logs or receipt generation.
- Interactive slide decks (use `slides`).
- Standalone single diagrams (use `diagram-design`).

---

## The 6 Golden Rules of Editorial PDFs

```
                    ┌───────────────────────────────┐
                    │       Raw Markdown (.md)      │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
       1. Anti-Monolith Formatting (Max 4-5 lines, Tables, Callouts)
       2. Alert Card Conversion (> [!NOTE], > [!TIP], > [!WARNING])
       3. Vector SVG Inlining (Replaces <img> with native inline SVG)
       4. Single-Pass Heading Promotion (h2->h1, h3->h2 for Outlines)
                                    │
                                    ▼
       5. Headless Chromium / Edge Print-to-PDF (A4, tagged=True, outline=True)
                                    │
                                    ▼
       6. pypdf Post-Processing:
          ├─ PdfWriter(clone_from=reader)  --> Preserves Outline Bookmarks
          └─ Rewrite /URI           --> file:///... converted to ./...
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    Publication-Ready PDF      │
                    └───────────────────────────────┘
```

### 1. Anti-Monolithic Content Structure
Technical prose must never form walls of text:
- **Maximum paragraph length:** 4–5 lines. If a thought is longer, break it with a bulleted list, an alert box, or a summary table.
- **Rhythmic cadence:** Rotate element types: Prose → Key Specs (Table) → Alert Callout → Inline Diagram → Code Snippet.
- **Page-Break Discipline:** Never let tables, callout cards, code snippets, or diagrams split across page boundaries (`page-break-inside: avoid;`).

### 2. GitHub-Style Visual Alerts
Transform markdown blockquotes into high-contrast editorial callout cards:
- `> [!NOTE]` — Blue (`#0969da`), architectural clarifications and background context.
- `> [!TIP]` — Emerald (`#1a7f37`), practical recommendations and best practices.
- `> [!IMPORTANT]` — Violet (`#8250df`), essential system behaviors and mandatory steps.
- `> [!WARNING]` — Amber (`#9a6700`), potential security or operational hazards.
- `> [!CAUTION]` — Crimson (`#cf222e`), destructive operations or critical vulnerabilities.

> **CRITICAL SYNTAX NOTE:** Always append double newlines `\n\n` after closing `</div>` callouts before Markdown rendering. Otherwise, Markdown parsers treat subsequent elements as raw HTML and drop images/links!

### 3. Native Inline Vector Diagrams
Never insert diagrams as bitmap screenshots or external PNGs:
- Extract SVG markup directly from `.svg` files or standalone `.html` diagram containers (e.g. from `diagram-design`).
- Inject SVG directly into the DOM inside an `<div class="editorial-diagram">` wrapper.
- Ensure the SVG has a flexible `viewBox` and responsive CSS (`width: 100% !important; max-height: 480px !important; height: auto !important;`).
- Set horizontal orientations for complex architectures with multiple nodes to maintain legibility without awkward zoom.

### 4. Single-Pass Heading Promotion for PDF Bookmarks
PDF reader sidebars (Adobe Acrobat, Edge, Chrome, Apple Preview) build their bookmarks outline from the HTML heading tree (`h1`, `h2`, `h3`):
- The document main title is converted from `h1` into `<div class="doc-main-title">`.
- Major chapters (`## Chapter`) are promoted to `h1`.
- Sections (`### Section`) are promoted to `h2`.
- **MUST USE SINGLE PASS REGEX:** Never run consecutive `re.sub('h2', 'h1', ...)` followed by `re.sub('h3', 'h2', ...)`. That collapses all headings into `h1`! A single regex using a tag dictionary lookup must be used.

### 5. Link Sanitization & Zero Leaks
When Chromium prints an HTML file containing relative links like `<a href="diagram.html">`, it expands them into host-absolute URLs: `file:///path/to/diagram.html`.
- This leaks developer machine usernames, drive paths, and breaks portability when the PDF is shared.
- Post-process the PDF with `pypdf` to scan all `/Annots` dictionaries and rewrite any `file://` URI to strictly relative `./<filename>` links.

### 6. Outline Preservation in Post-Processing
When modifying a PDF in `pypdf`:
- **DO NOT** use `for page in reader.pages: writer.add_page(page)`. This silently discards the entire PDF table of contents bookmarks outline (`/Outlines`)!
- **ALWAYS** use `PdfWriter(clone_from=reader)`. This clones the document catalog and retains the outline.

---

## Quick Reference CLI Commands

The skill provides two production-ready scripts in `scripts/`:

### 1. Building a Publication-Grade PDF

```bash
# Basic build (auto-detects diagrams in document folder, applies default styles)
python scripts/build_pdf.py report.md -o report.pdf

# Advanced build with custom header and diagrams directory
python scripts/build_pdf.py report.md \
    -o report.pdf \
    --diagrams-dir ./diagrams \
    --header "Confidential Technical Audit · 2026" \
    --channel msedge
```

**Options:**
- `input`: Path to input Markdown file (required).
- `-o`, `--output`: Path to generated PDF (defaults to `<input>.pdf`).
- `--diagrams-dir`: Folder containing SVG or HTML diagrams to inline (defaults to input dir).
- `--css`: Custom CSS stylesheet path (defaults to bundled `assets/editorial.css`).
- `--header`: Custom running header title.
- `--channel`: Browser channel (`msedge` on Windows, or `chromium`).
- `--no-heading-shift`: Disable heading level promotion.
- `--no-link-sanitize`: Disable URI rewriting.
- `--keep-temp`: Keep intermediate HTML render file for inspection.

### 2. Auditing PDF Quality and Security

```bash
python scripts/verify_pdf.py report.pdf --forbidden "example-user,internal.example"
```

**What it verifies:**
1. Hierarchical bookmarks outline (displays full chapter tree and entry count).
2. Link annotations: strictly verifies that 100% of links are relative and flags any `file:///` or drive paths.
3. Text layer leak detection: scans extracted PDF text for forbidden usernames, paths, or IPs.
4. Returns exit code `0` on complete pass, `1` on failure.

---

## Common Mistakes & Troubleshooting

| Anti-Pattern / Symptom | Root Cause | Editorial PDF Solution |
| :--- | :--- | :--- |
| **PDF bookmarks outline is flat (all items on Level 1)** | Headings shifted using sequential `re.sub('h2', 'h1')` then `re.sub('h3', 'h2')`. | Use single-pass regex replacement: `re.sub(r'<(h[2-4])([^>]*)>(.*?)</\1>', shift_heading, html)`. |
| **PDF bookmarks disappear after editing with `pypdf`** | Using `writer.add_page(p)` loop. | Use `PdfWriter(clone_from=reader)` to keep `/Outlines` intact. |
| **Subsequent markdown images disappear after callout** | Missing newlines after raw `<div>` callout block. | Always append `\n\n` after the closing `</div>` in the regex alert replacer. |
| **Links point to `file:///C:/Users/name/...`** | Chromium default print-to-PDF resolves relative URLs. | Sanitize `/Annots` in `pypdf` rewriting URI targets to `./<basename>`. |
| **Diagrams blurry or pixelated** | Embedded raster PNGs. | Inline native vector SVGs directly into HTML markup. |
| **Tables or cards cut in half between pages** | Missing CSS break-inside properties. | Apply `page-break-inside: avoid; break-inside: avoid;` to tables, callouts, and diagrams. |
| **Python script crashes with `UnicodeEncodeError: 'charmap'`** | Windows terminal defaults to CP1251. | Add `sys.stdout.reconfigure(encoding="utf-8")` at script startup. |

---

## Pre-Publication Verification Checklist

Before delivering any PDF to a user or repository:
- [ ] **Rhythmic Layout:** No paragraph exceeds 5 lines; tables and lists break up text.
- [ ] **All Callouts Rendered:** Every `> [!NOTE]` block rendered as a styled card with emoji header.
- [ ] **Vector Visuals:** All architecture diagrams are inline SVGs with crisp lines at 400% zoom.
- [ ] **Bookmarks Outline:** PDF sidebar shows a multi-level Table of Contents.
- [ ] **Zero Leaks:** Running `verify_pdf.py` reports 0 absolute `file://` URLs and 0 host usernames in the text layer.
- [ ] **Relative Links:** Any linked files (HTML schematics) open seamlessly relative to the PDF location.
