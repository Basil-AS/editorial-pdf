#!/usr/bin/env python3
"""Check editorial PDF structure, destinations and selected disclosure indicators."""
import argparse
import ipaddress
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from pypdf import PdfReader
from pypdf.generic import ArrayObject, NameObject

LOCAL = re.compile(r"file:/{1,3}|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]|/(?:home|Users|workspace)/[^/\s]+", re.I)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
PRIVATE = tuple(map(ipaddress.ip_network, ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16"]))


def check_outline(reader, entries):
    count = 0
    for entry in entries:
        if isinstance(entry, list):
            count += check_outline(reader, entry)
        else:
            if not 0 <= reader.get_destination_page_number(entry) < len(reader.pages):
                raise ValueError("Bookmark points outside the document")
            count += 1
    return count


def valid_uri(uri):
    try:
        url = urlsplit(uri)
        if url.scheme in {"https", "http"}:
            return bool(url.hostname and not url.username and not url.password and url.hostname != "editorial.invalid")
        if url.scheme == "mailto":
            return bool(url.path)
        path = unquote(url.path)
        return (
            uri.startswith("./") and not url.scheme and not url.netloc
            and not any(c in path for c in "\\:\x00") and ".." not in path.split("/")
            and bool(path[2:].strip("/"))
        )
    except ValueError:
        return False


def audit(args):
    reader = PdfReader(args.pdf)
    if reader.is_encrypted or not reader.pages:
        raise ValueError("Expected an unencrypted PDF with at least one page")
    bookmarks = check_outline(reader, reader.outline)
    errors = []
    if args.require_outline and not bookmarks:
        errors.append("Expected bookmarks")
    if args.require_tagged and not reader.root_object.get("/StructTreeRoot"):
        errors.append("Expected a structure tree")
    forbidden = [word.strip().casefold() for word in args.forbidden.split(",") if word.strip()]
    links = 0
    named_destinations = reader.named_destinations
    page_refs = {page.indirect_reference for page in reader.pages}

    def valid_destination(destination):
        if isinstance(destination, str):
            key = str(destination)
            if isinstance(destination, NameObject):
                key = key if key in named_destinations else key.removeprefix("/")
            named = named_destinations.get(key)
            return named is not None and 0 <= reader.get_destination_page_number(named) < len(reader.pages)
        if isinstance(destination, ArrayObject) and destination:
            return list.__getitem__(destination, 0) in page_refs
        return False

    def check_content(label, text):
        if any(term in text.casefold() for term in forbidden):
            errors.append(f"{label}: forbidden literal")
        if args.public and LOCAL.search(text):
            errors.append(f"{label}: local path pattern")
        if args.public:
            for value in IPV4.findall(text):
                try:
                    address = ipaddress.ip_address(value)
                except ValueError:
                    continue
                if any(address in network for network in PRIVATE):
                    errors.append(f"{label}: private or local IPv4")
                    break

    check_content("Metadata", str(reader.metadata))
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if args.require_text and not text.strip():
            errors.append(f"Page {index}: no extractable text")
        check_content(f"Page {index}", text)
        for ref in page.get("/Annots", []):
            annot = ref.get_object()
            if annot.get("/Subtype") != "/Link":
                continue
            links += 1
            action = annot.get("/A")
            if action is None and valid_destination(annot.get("/Dest")):
                continue
            if action is not None:
                action = action.get_object()
                if action.get("/S") == "/GoTo" and valid_destination(action.get("/D")):
                    continue
                if action.get("/S") == "/URI" and valid_uri(str(action.get("/URI", ""))):
                    check_content(f"Page {index} link", unquote(str(action["/URI"])))
                    continue
            errors.append(f"Page {index}: unsupported link or action")
    print(f"{len(reader.pages)} pages, {bookmarks} bookmarks, {links} links")
    for error in errors:
        print(error)
    return not errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--require-outline", action="store_true")
    parser.add_argument("--require-tagged", action="store_true")
    parser.add_argument("--require-text", action="store_true")
    parser.add_argument("--public", action="store_true", help="Flag selected local paths and private IPv4 addresses")
    parser.add_argument("--forbidden", default="", help="Comma-separated case-insensitive literals")
    try:
        passed = audit(parser.parse_args())
    except Exception as error:
        parser.exit(1, f"Audit failed: {error}\n")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
