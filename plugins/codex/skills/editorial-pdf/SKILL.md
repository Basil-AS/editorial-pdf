---
name: editorial-pdf
description: Create, review, or refine polished, print-ready PDFs, especially reports, specifications, manuals, and white papers from Markdown. Use for typography, page layout, Cyrillic, diagrams, long tables, bookmarks, PDF links, or pre-delivery rendering and checks. For edits to an existing PDF, inspect and preserve the original structure and use the appropriate PDF workflow.
---

# Editorial PDF

## Choose the workflow

- **Author from Markdown or supplied content.** Use the bundled builder and stylesheet. Preserve source facts, code, numbers, citations, and document language. Use the user's template and page-size requirements where provided.
- **Review a PDF.** Inspect metadata and extracted text, then render pages to verify layout. For scans, use OCR where needed and compare uncertain text against the image.
- **Edit an existing PDF.** Keep the original. Make targeted changes using the host PDF workflow, preserving page geometry, links, bookmarks, and forms where applicable. Read [existing-pdf.md](references/existing-pdf.md) for forms, signed files, and redaction.
- Follow host artifact contracts and save the requested deliverable through the host's file workflow.

## Compose and build

1. Use one document title and a logical heading hierarchy. Favor short, coherent paragraphs, tables for exact comparisons, callouts for exceptions, and figures when they explain a relationship. Avoid layout elements that add no information.
2. Check assets and links before printing. Supply local, static SVGs for diagrams and sufficient resolution for raster images. Use meaningful alt text, captions, and descriptive link labels.
3. From the skill directory, run the builder. It uses local fonts, embeds images, keeps semantic heading levels, generates bookmarks and tags, and blocks network resource loads. See [builder.md](references/builder.md) for setup, supported syntax, and output options.

```bash
python scripts/build_pdf.py report.md -o output/report.pdf --lang ru
python scripts/verify_pdf.py output/report.pdf --require-outline --require-tagged --require-text
pdftoppm -r 120 -png output/report.pdf scratch/page
```

## Verify the delivered revision

- Render every page of the final PDF. Scan all pages for pacing and whitespace, then inspect tables, diagrams, code, and page transitions at readable scale. Confirm headings stay with text, long tables repeat headers, glyphs render, and nothing clips. Re-render after edits.
- Compare representative extracted text, totals, and page order to the source. Open internal links and bookmarks and confirm they reach the intended sections. Validate companion files and relative paths in the target viewer when used.
- Use `--public` and `--forbidden` for disclosure checks where appropriate. Inspect metadata, images, and attachments separately when disclosure matters. Automated checks cover selected indicators and structural properties. For PDF/A or PDF/UA requirements, use dedicated conformance validation and review.
- Deliver only requested outputs and state any consequential verification limits.
