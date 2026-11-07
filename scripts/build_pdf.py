#!/usr/bin/env python3
"""Render Markdown to a tagged PDF with local assets and stable navigation."""
import argparse
import base64
from html import escape
import os
from pathlib import Path, PurePosixPath
import re
from tempfile import TemporaryDirectory
from urllib.parse import quote, unquote, urlsplit

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject

ORIGIN = "https://editorial.invalid"
DOCUMENT = ORIGIN + "/document"
CSS = Path(__file__).resolve().parents[1] / "assets/editorial.css"
MEDIA = {
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif",
}
LABELS = {
    "NOTE": ("Note", "Примечание"), "TIP": ("Tip", "Совет"),
    "IMPORTANT": ("Important", "Важно"), "WARNING": ("Warning", "Внимание"),
    "CAUTION": ("Caution", "Осторожно"),
}


def local_path(raw):
    path = unquote(raw)
    if not path or path.startswith("/") or any(c in path for c in "\\:\x00"):
        raise ValueError(f"Expected a relative path: {raw}")
    if ".." in PurePosixPath(path).parts:
        raise ValueError(f"Parent traversal is disallowed: {raw}")
    return path


def read_image(src, roots):
    url = urlsplit(src)
    if url.scheme or url.netloc or url.query or url.fragment:
        raise ValueError(f"Use a local image file: {src}")
    relative = local_path(url.path)
    for root in roots:
        asset = (root / relative).resolve()
        if not asset.is_relative_to(root):
            raise ValueError(f"Image resolves outside its asset directory: {src}")
        if asset.is_file():
            break
    else:
        raise ValueError(f"Missing image: {src}")
    mime = MEDIA.get(asset.suffix.lower())
    if asset.suffix.lower() == ".html":
        html = BeautifulSoup(asset.read_text(encoding="utf-8"), "html.parser")
        svgs = html.find_all("svg")
        if len(svgs) != 1:
            raise ValueError(f"Export a static SVG from {src}; expected exactly one SVG")
        data = str(svgs[0]).encode()
        mime = MEDIA[".svg"]
    elif mime:
        data = asset.read_bytes()
    else:
        raise ValueError(f"Unsupported image format: {src}")
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def prepare_document(args):
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    soup = BeautifulSoup(md.render(args.input.read_text(encoding="utf-8-sig")), "html.parser")
    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    first_h1 = next((h for h in headings if h.name == "h1"), None)
    title = args.title or (first_h1.get_text(" ", strip=True) if first_h1 else args.input.stem)
    ru = args.lang.lower().split("-")[0] == "ru"

    ids = set()
    for heading in headings:
        slug = re.sub(r"[^\w-]", "", heading.get_text().strip().lower().replace(" ", "-"))
        base = slug or "section"
        candidate = base
        number = 1
        while candidate in ids:
            number += 1
            candidate = f"{base}-{number}"
        ids.add(candidate)
        heading["id"] = candidate
    if first_h1:
        first_h1["class"] = "document-title"

    for block in soup.find_all("blockquote"):
        paragraph = block.find("p", recursive=False)
        if paragraph is None or not paragraph.contents:
            continue
        node = paragraph.contents[0]
        match = re.match(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\](?:\n|$)", str(node))
        if not match or node.name is not None:
            continue
        kind = match[1]
        node.replace_with(str(node)[match.end():])
        if not paragraph.get_text(strip=True) and not paragraph.find():
            paragraph.decompose()
        block.name = "aside"
        block["class"] = ["callout", f"callout-{kind.lower()}"]
        label = soup.new_tag("div", attrs={"class": "callout-label"})
        label.string = LABELS[kind][ru]
        block.insert(0, label)

    roots = [args.input.resolve().parent]
    if args.diagrams_dir:
        roots.append(args.diagrams_dir.resolve(strict=True))
    for img in soup.find_all("img"):
        img["src"] = read_image(img["src"], roots)

    companions = {}
    for link in soup.find_all("a", href=True):
        href = link["href"]
        url = urlsplit(href)
        if href.startswith("#") and unquote(url.fragment) in ids:
            continue
        if url.scheme in {"http", "https"} and url.hostname and not url.username and not url.password:
            continue
        if url.scheme == "mailto" and url.path:
            continue
        if args.companion_root and not url.scheme and not url.netloc and not href.startswith("#"):
            path = local_path(url.path)
            target = (args.companion_root / path).resolve()
            if target.is_relative_to(args.companion_root) and target.is_file():
                key = ORIGIN + f"/companion/{len(companions)}"
                companions[key] = "./" + quote(path, safe="/") + url.geturl()[len(url.path):]
                link["href"] = key
                continue
        raise ValueError(f"Unresolved or unsupported link: {href}")
    return title, str(soup), companions


def rewrite_companions(source, output, companions):
    with source.open("rb") as stream:
        writer = PdfWriter(clone_from=PdfReader(stream))
        for page in writer.pages:
            for ref in page.get("/Annots", []):
                action = ref.get_object().get("/A")
                if action is not None:
                    action = action.get_object()
                    target = companions.get(str(action.get("/URI", "")))
                    if target:
                        action[NameObject("/URI")] = TextStringObject(target)
        with output.open("wb") as result:
            writer.write(result)


def build(args):
    title, body, companions = prepare_document(args)
    css = (args.css or CSS).read_text(encoding="utf-8")
    if re.search(r"</style", css, flags=re.IGNORECASE):
        raise ValueError("CSS must be a stylesheet without HTML tags")
    html = (
        f'<!doctype html><html lang="{escape(args.lang)}"><meta charset="utf-8">'
        f"<title>{escape(title)}</title><style>{css}</style><body><main>{body}</main>"
        "</body></html>"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".editorial-", dir=args.output.parent) as temp:
        draft = Path(temp) / "draft.pdf"
        with sync_playwright() as playwright:
            options = {"channel": args.channel} if args.channel else {}
            if args.browser_executable:
                options["executable_path"] = str(args.browser_executable.resolve(strict=True))
            browser = playwright.chromium.launch(**options)
            page = browser.new_page(java_script_enabled=False, service_workers="block")
            blocked = []

            def route_request(route):
                if route.request.url == DOCUMENT and route.request.is_navigation_request():
                    route.fulfill(content_type="text/html; charset=utf-8", body=html)
                else:
                    blocked.append(route.request.resource_type)
                    route.abort()

            page.route("**/*", route_request)
            page.goto(DOCUMENT, wait_until="load")
            broken = page.locator("img").evaluate_all(
                "(images) => images.filter(img => !img.complete || !img.naturalWidth).length"
            )
            page.evaluate("document.fonts.ready.then(() => true)")
            if blocked or broken:
                raise ValueError(f"Blocked resource types: {blocked}; broken images: {broken}")
            footer = 'Страница <span class="pageNumber"></span> из' if args.lang.startswith("ru") else 'Page <span class="pageNumber"></span> of'
            header = escape(args.header if args.header is not None else title)
            page.pdf(
                path=draft, format=args.paper, print_background=True, tagged=True, outline=True,
                display_header_footer=True,
                margin={"top": "21mm", "bottom": "19mm", "left": "19mm", "right": "19mm"},
                header_template=f'<div style="margin:0 19mm;font:8pt sans-serif;color:#475569;width:100%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{header}</div>',
                footer_template=f'<div style="font:8pt sans-serif;color:#475569;width:100%;text-align:center">{footer} <span class="totalPages"></span></div>',
            )
            browser.close()
        if companions:
            final = Path(temp) / "final.pdf"
            rewrite_companions(draft, final, companions)
        else:
            final = draft
        os.replace(final, args.output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--css", type=Path, help="Replace the bundled stylesheet")
    parser.add_argument("--diagrams-dir", type=Path, help="Additional local image root")
    parser.add_argument("--companion-root", type=Path, help="Directory to ship alongside the PDF")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--channel", help="Installed Playwright browser channel, e.g. msedge")
    browser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--title", help="Override metadata title")
    parser.add_argument("--header", help="Override running title; pass empty to suppress")
    parser.add_argument("--lang", default="en", help="Document language tag, e.g. ru")
    parser.add_argument("--paper", choices=["A4", "Letter"], default="A4")
    args = parser.parse_args()
    args.output = args.output or args.input.with_suffix(".pdf")
    if args.output.suffix.lower() != ".pdf" or args.output.resolve() == args.input.resolve():
        parser.error("Choose a .pdf output distinct from the input")
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", args.lang):
        parser.error("--lang must be a language tag")
    if args.companion_root:
        args.companion_root = args.companion_root.resolve()
        if args.companion_root != args.output.resolve().parent:
            parser.error("--companion-root must be the PDF output directory")
    try:
        build(args)
    except Exception as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(args.output)


if __name__ == "__main__":
    main()
