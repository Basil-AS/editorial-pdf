#!/usr/bin/env python3
"""Check A4 geometry, printed folios, fonts, text bounds and PDF navigation."""
import argparse
import math
from pathlib import Path
import subprocess

import fitz
from pypdf import PdfReader

from build_pdf import is_a4

MM = 72 / 25.4


def verify(path, hidden):
    errors = []
    reader = PdfReader(path)
    fonts = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True, check=True)
    font_rows = fonts.stdout.splitlines()[2:]
    for row in font_rows:
        fields = row.split()
        if len(fields) >= 6 and fields[-5] != "yes":
            errors.append(f"Шрифт не встроен: {fields[0]}")
    with fitz.open(path) as doc:
        if hidden > len(doc):
            errors.append("Число скрытых номеров больше числа страниц")
        for number, (page, original) in enumerate(zip(doc, reader.pages), 1):
            if not (is_a4(original) or is_a4(original, True)):
                errors.append(f"Лист {number}: геометрия не A4 или задан поворот")
                continue
            if number <= hidden:
                continue
            words = page.get_text("words")
            footer = [word for word in words if word[1] > page.rect.height - 17 * MM]
            if [w[4] for w in footer] != [str(number)]:
                errors.append(f"Лист {number}: проверьте сквозной номер страницы")
            else:
                x0, _, x1, *_ = footer[0]
                target = page.rect.width / 2
                point = (x0 + x1) / 2
                if not math.isclose(point, target, abs_tol=3):
                    errors.append(f"Лист {number}: номер смещён")
            left, right = 30 * MM - 3, page.rect.width - 15 * MM + 3
            if any(w[0] < left or w[2] > right for w in words):
                errors.append(f"Лист {number}: текст выходит за боковые поля")
            for link in page.get_links():
                if link["kind"] == fitz.LINK_GOTO and not 0 <= link["page"] < len(doc):
                    errors.append(f"Лист {number}: битая внутренняя ссылка")
        for _, title, number in doc.get_toc():
            if not 1 <= number <= len(doc):
                errors.append(f"Закладка без страницы: {title}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--hidden", type=int, default=0,
                        help="Number of leading pages with no printed folio")
    args = parser.parse_args()
    if args.hidden < 0:
        parser.error("--hidden must be non-negative")
    errors = verify(args.pdf, args.hidden)
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")
    print("Проверка PDF пройдена")
