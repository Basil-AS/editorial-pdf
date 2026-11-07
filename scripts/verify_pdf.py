#!/usr/bin/env python3
"""
verify_pdf.py - Automated Quality and Leak Audit for Editorial PDFs

Audits:
1. Page count and general metadata
2. PDF Bookmarks (Outlines) hierarchy and chapter count
3. Link annotations: strictly verifies that all links are relative and contain NO absolute file:/// or local drive paths
4. Text layer leak detection: audits for developer usernames, local host paths, internal IPs, etc.
"""

import sys
import re
import argparse
from pathlib import Path
import pypdf

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def print_outline(outline, level=0):
    count = 0
    for item in outline:
        if isinstance(item, list):
            count += print_outline(item, level + 1)
        else:
            title = getattr(item, "title", str(item))
            page_dest = getattr(item, "page", None)
            indent = "  " * level
            print(f"{indent}• {title}")
            count += 1
    return count

def verify_pdf(pdf_path: Path, forbidden_words: list[str] | None = None) -> bool:
    if not pdf_path.exists():
        print(f"❌ Error: File not found: {pdf_path}")
        return False

    print(f"\n==================================================")
    print(f" AUDITING PDF: {pdf_path.name}")
    print(f"==================================================")

    reader = pypdf.PdfReader(str(pdf_path))
    num_pages = len(reader.pages)
    print(f"✔ Page Count: {num_pages} pages")

    # 1. Audit Bookmarks (Outline)
    print(f"\n--- 1. BOOKMARKS / OUTLINES HIERARCHY ---")
    try:
        outline = reader.outline
        if outline:
            total_bookmarks = print_outline(outline)
            print(f"✔ Hierarchical Bookmarks present ({total_bookmarks} entries).")
        else:
            print("⚠️ Warning: No document outline/bookmarks found!")
    except Exception as e:
        print(f"⚠️ Could not parse outline: {e}")

    # 2. Audit Link Annotations
    print(f"\n--- 2. LINK ANNOTATIONS AUDIT ---")
    all_links = []
    abs_links = []

    for page_idx, page in enumerate(reader.pages):
        if '/Annots' in page:
            for annot in page['/Annots']:
                obj = annot.get_object()
                if '/A' in obj and '/URI' in obj['/A']:
                    uri = str(obj['/A']['/URI'])
                    all_links.append((page_idx + 1, uri))
                    if 'file://' in uri or 'C:' in uri or 'Users/' in uri or 'Users\\' in uri:
                        abs_links.append((page_idx + 1, uri))

    print(f"Total Link Annotations: {len(all_links)}")
    if abs_links:
        print(f"❌ FAILED: Found {len(abs_links)} absolute / forbidden links:")
        for page_num, uri in abs_links:
            print(f"   [Page {page_num}] {uri}")
        return False
    else:
        print("✔ No matching local-file URI patterns found.")
        for page_num, uri in all_links[:5]:
            print(f"   Sample [P{page_num}]: {uri}")

    # 3. Audit Text Layer for Leaks
    print(f"\n--- 3. TEXT LAYER LEAK DETECTION ---")
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() or ""

    default_forbidden = ["Users\\\\", ":/Users/", ":\\Users\\", "file://", "192.168.", "10.0.", "172.16."]
    check_list = set(default_forbidden + (forbidden_words or []))

    found_leaks = []
    for word in check_list:
        if not word:
            continue
        matches = re.findall(re.escape(word), full_text, re.IGNORECASE)
        if matches:
            found_leaks.append((word, len(matches)))

    if found_leaks:
        print(f"❌ LEAKS DETECTED in text layer:")
        for word, count in found_leaks:
            print(f"   - '{word}': {count} occurrences")
        return False
    else:
        print(f"✔ TEXT LAYER CLEAN (Audited {len(check_list)} patterns, {len(full_text)} characters, 0 leaks).")

    print(f"\n==================================================")
    print(f"✔ AUDIT RESULT: PASSED ALL CHECKS")
    print(f"==================================================\n")
    return True

def main():
    parser = argparse.ArgumentParser(description="Audit editorial PDF for outlines, links, and leaks")
    parser.add_argument("pdf_path", type=Path, help="Path to PDF file to verify")
    parser.add_argument("--forbidden", type=str, default="", help="Comma-separated forbidden words/usernames to check")

    args = parser.parse_args()
    forbidden = [w.strip() for w in args.forbidden.split(",") if w.strip()]

    passed = verify_pdf(args.pdf_path, forbidden)
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
