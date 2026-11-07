#!/usr/bin/env python3
"""
build_pdf.py - Publication-ready Editorial PDF Generator from Markdown

Features:
- Converts Markdown to print-ready HTML using markdown-it-py
- Transforms GitHub-style callouts (> [!NOTE], > [!TIP], etc.) into styled alert cards
- Inlines vector SVG diagrams directly from .svg or .html files (eliminating rasterization and external file dependencies)
- Shifts document headings so Chapters become top-level bookmarks in PDF readers
- Renders via headless Edge / Chromium (Playwright) with A4 paged media styles, margins, headers, and footers
- Sanitizes link annotations via pypdf: converts absolute file:/// paths into relative ./ links
- Preserves full hierarchical PDF bookmarks (outline) using writer.append(reader)
"""

import os
import sys
import re
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ALERT_CONFIG = {
    "NOTE": ("#0969da", "#f0f8ff", "ℹ️ ПРИМЕЧАНИЕ"),
    "TIP": ("#1a7f37", "#f0fff4", "💡 СОВЕТ"),
    "IMPORTANT": ("#8250df", "#faf5ff", "⚡ ВАЖНО"),
    "WARNING": ("#9a6700", "#fffdf0", "⚠️ ВНИМАНИЕ"),
    "CAUTION": ("#cf222e", "#fff5f5", "🛑 ОСТОРОЖНО"),
}

def parse_alerts(raw_md: str) -> str:
    def replace_alert(match):
        atype = match.group(1).upper()
        content = match.group(2).strip()
        color, bg, default_title = ALERT_CONFIG.get(atype, ("#0969da", "#f0f8ff", atype))

        lines = []
        for line in content.split("\n"):
            clean = re.sub(r"^>\s?", "", line).strip()
            if not clean:
                continue
            clean = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", clean)
            clean = re.sub(r"`(.*?)`", r"<code>\1</code>", clean)
            lines.append(clean)

        body_html = "<br>".join(lines)
        return (
            f'<div class="callout callout-{atype.lower()}" style="border-left: 4px solid {color}; background-color: {bg}; padding: 10px 14px; margin: 12px 0; border-radius: 5px; page-break-inside: avoid; break-inside: avoid;">'
            f'<div class="callout-header" style="color: {color}; font-size: 9.5px; font-weight: 700; font-family: \'Geist Mono\', monospace; letter-spacing: 0.08em; margin-bottom: 4px;">{default_title}</div>'
            f'<div class="callout-body" style="font-size: 11px; line-height: 1.5; color: #2d3142;">{body_html}</div>'
            f'</div>\n\n'
        )

    return re.sub(r">\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*\n((?:>.*(?:\n|$))*)", replace_alert, raw_md, flags=re.IGNORECASE)

def find_diagram_content(filename: str, diagrams_dir: Path) -> str | None:
    target_name = Path(filename).name
    candidates = [
        diagrams_dir / target_name,
        diagrams_dir / f"{target_name}.svg",
        diagrams_dir / f"{Path(target_name).stem}.svg",
        diagrams_dir / f"{Path(target_name).stem}.html",
    ]
    for p in candidates:
        if p.exists():
            if p.suffix.lower() == ".svg":
                try:
                    return p.read_text(encoding="utf-8")
                except Exception:
                    pass
            elif p.suffix.lower() == ".html":
                try:
                    soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
                    svg = soup.find("svg")
                    if svg:
                        return str(svg)
                except Exception:
                    pass
    return None

def inject_inline_diagrams(html: str, diagrams_dir: Path) -> str:
    # Match markdown images or html img tags
    img_pattern = re.compile(r'<p>\s*<img[^>]+src=[\"\']([^\"\']+)[\"\'][^>]*alt=[\"\']([^\"\']*)[\"\'][^>]*>\s*</p>', re.IGNORECASE)
    img_pattern2 = re.compile(r'<p>\s*<img[^>]+src=[\"\']([^\"\']+)[\"\'][^>]*>\s*</p>', re.IGNORECASE)

    def replacer(match):
        src = match.group(1)
        alt = match.group(2) if len(match.groups()) > 1 else ""
        title = alt or Path(src).stem.replace("_", " ").upper()

        svg_content = find_diagram_content(src, diagrams_dir)
        if svg_content:
            return (
                f'<div class="editorial-diagram" style="page-break-inside: avoid; break-inside: avoid; margin: 16px 0; background: #ffffff; border: 1px solid rgba(45,49,66,0.14); border-radius: 6px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">'
                f'<div class="diagram-title" style="font-family: \'Geist Mono\', monospace; font-size: 8.5px; font-weight: 600; color: #4f5d75; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px;">{title}</div>'
                f'<div style="width: 100%;">{svg_content}</div>'
                f'</div>'
            )
        return match.group(0)

    html = img_pattern.sub(replacer, html)
    html = img_pattern2.sub(replacer, html)
    return html

def shift_headings(html: str) -> str:
    """Promotes h2->h1, h3->h2, h4->h3 in a single pass so chapters become top-level bookmarks."""
    # Convert first H1 into a title banner
    html = re.sub(r'<h1>(.*?)</h1>', r'<div class="doc-main-title">\1</div>', html, count=1)

    def shift_match(match):
        tag = match.group(1).lower()
        attrs = match.group(2)
        content = match.group(3)
        target_tag = {"h2": "h1", "h3": "h2", "h4": "h3"}.get(tag, tag)
        return f"<{target_tag}{attrs}>{content}</{target_tag}>"

    return re.sub(r'<(h[2-4])([^>]*)>(.*?)</\1>', shift_match, html, flags=re.DOTALL)

def build_pdf(
    input_path: Path,
    output_path: Path,
    css_path: Path | None = None,
    diagrams_dir: Path | None = None,
    channel: str = "",
    doc_header: str | None = None,
    shift_heading_levels: bool = True,
    sanitize_links: bool = True,
    keep_temp: bool = False,
):
    from playwright.sync_api import sync_playwright
    import pypdf

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    input_dir = input_path.parent
    if diagrams_dir is None:
        diagrams_dir = input_dir

    raw_md = input_path.read_text(encoding="utf-8")

    # Extract title from first H1 if available
    h1_match = re.search(r"^#\s+(.+)$", raw_md, re.MULTILINE)
    default_title = h1_match.group(1).strip() if h1_match else input_path.stem.replace("_", " ")
    header_text = doc_header or default_title

    # 1. Parse GitHub-style alerts
    raw_md = parse_alerts(raw_md)

    # 2. Render Markdown
    md_parser = MarkdownIt("default", {"html": True}).enable("table")
    rendered_html = md_parser.render(raw_md)

    # 3. Inject Vector SVGs
    rendered_html = inject_inline_diagrams(rendered_html, diagrams_dir)

    # 4. Heading Promotion for PDF Bookmarks
    if shift_heading_levels:
        rendered_html = shift_headings(rendered_html)

    # 5. Load CSS
    css_content = ""
    if css_path and css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
    else:
        # Default skill CSS path
        default_skill_css = Path(__file__).parent.parent / "assets" / "editorial.css"
        if default_skill_css.exists():
            css_content = default_skill_css.read_text(encoding="utf-8")

    full_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{default_title}</title>
<style>
{css_content}
</style>
</head>
<body>
{rendered_html}
</body>
</html>"""

    temp_html_path = output_path.parent / f"_temp_render_{output_path.stem}.html"
    temp_html_path.write_text(full_html, encoding="utf-8")

    try:
        print(f"[1/3] Rendering PDF with Playwright ({channel})...")
        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            if channel:
                try:
                    browser = p.chromium.launch(channel=channel, **launch_kwargs)
                except Exception as e:
                    print(f"Warning: Channel '{channel}' failed ({e}), falling back to bundled Chromium...")
                    browser = p.chromium.launch(**launch_kwargs)
            else:
                browser = p.chromium.launch(**launch_kwargs)

            page = browser.new_page()
            page.goto(temp_html_path.resolve().as_uri(), wait_until="load")

            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "14mm", "bottom": "14mm", "left": "10mm", "right": "10mm"},
                display_header_footer=True,
                header_template=f'<div style="font-size: 7.5pt; color: #7a8399; width: 100%; text-align: right; padding-right: 10mm; font-family: Segoe UI, sans-serif;">{header_text}</div>',
                footer_template='<div style="font-size: 7.5pt; color: #7a8399; width: 100%; text-align: center; font-family: Segoe UI, sans-serif;">Страница <span class="pageNumber"></span> из <span class="totalPages"></span></div>',
                outline=True,
                tagged=True
            )
            browser.close()

        # 6. Post-processing with pypdf
        if sanitize_links:
            print("[2/3] Sanitizing link annotations & preserving outline...")
            reader = pypdf.PdfReader(str(output_path))
            writer = pypdf.PdfWriter(clone_from=reader)

            rewritten_count = 0
            for p_obj in writer.pages:
                if '/Annots' in p_obj:
                    for annot in p_obj['/Annots']:
                        obj = annot.get_object()
                        if '/A' in obj and '/URI' in obj['/A']:
                            uri = str(obj['/A']['/URI'])
                            if 'file://' in uri:
                                filename = uri.split('/')[-1]
                                obj['/A'][pypdf.generic.NameObject('/URI')] = pypdf.generic.create_string_object(f"./{filename}")
                                rewritten_count += 1

            temp_sanitized = output_path.parent / f"_temp_sanitized_{output_path.name}"
            with open(temp_sanitized, "wb") as f_out:
                writer.write(f_out)

            os.replace(temp_sanitized, output_path)
            print(f"Sanitized {rewritten_count} link annotations to relative paths.")

        print(f"[3/3] PDF generated successfully: {output_path} ({os.path.getsize(output_path)} bytes)")

    finally:
        if not keep_temp and temp_html_path.exists():
            temp_html_path.unlink()

def main():
    parser = argparse.ArgumentParser(description="Editorial PDF Builder: Turn Markdown into publication-ready PDFs")
    parser.add_argument("input", type=Path, help="Input Markdown (.md) file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output PDF file path")
    parser.add_argument("--css", type=Path, default=None, help="Path to custom CSS stylesheet")
    parser.add_argument("--diagrams-dir", type=Path, default=None, help="Directory containing SVG/HTML diagrams")
    parser.add_argument("--channel", type=str, default="", help="Browser channel ('msedge' or 'chromium')")
    parser.add_argument("--header", type=str, default=None, help="Document header running title")
    parser.add_argument("--no-heading-shift", action="store_true", help="Do not shift h2..h4 headings")
    parser.add_argument("--no-link-sanitize", action="store_true", help="Do not rewrite file:// links to relative")
    parser.add_argument("--keep-temp", action="store_true", help="Keep intermediate HTML file")

    args = parser.parse_args()
    output_path = args.output or args.input.with_suffix(".pdf")

    build_pdf(
        input_path=args.input,
        output_path=output_path,
        css_path=args.css,
        diagrams_dir=args.diagrams_dir,
        channel=args.channel,
        doc_header=args.header,
        shift_heading_levels=not args.no_heading_shift,
        sanitize_links=not args.no_link_sanitize,
        keep_temp=args.keep_temp,
    )

if __name__ == "__main__":
    main()
