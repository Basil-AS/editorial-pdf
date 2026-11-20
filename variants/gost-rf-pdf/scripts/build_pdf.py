#!/usr/bin/env python3
"""Render trusted Markdown to a GOST 7.32 report or fragment."""
import argparse
import os
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from pypdf import PdfReader
from norms import validate

ROOT = Path(__file__).resolve().parents[1]
A4 = (595.28, 841.89)


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError(result.stdout[-6500:])
    return result.stdout


def is_a4(page, landscape=False):
    dimensions = A4[::-1] if landscape else A4
    return (page.rotation % 360 == 0
            and abs(float(page.mediabox.width) - dimensions[0]) < 2
            and abs(float(page.mediabox.height) - dimensions[1]) < 2)


def build(args):
    if args.review:
        review = json.loads(args.review.read_text(encoding="utf-8"))
        failures = validate(review)
        if failures:
            raise ValueError("Запись учёта требований не готова:\n" + "\n".join(failures))
        if review["standards"]["gost-7-32-2017"]["decision"] != "apply":
            raise ValueError("Для этого сборщика должен применяться ГОСТ 7.32")
        incompatible = {
            "gost-19-104-78", "gost-19-105-78", "gost-19-106-78",
            "gost-19-201-78", "gost-19-301-79", "gost-r-2-105-2019",
            "gost-r-1-5-2012"
        }
        if any(review["standards"][key]["decision"] == "apply" for key in incompatible):
            raise ValueError("Выбран вид документа, требующий отдельного шаблона. "
                             "Уточните применимость для самостоятельного документа "
                             "либо сверстайте его по соответствующему стандарту.")
    elif not args.draft:
        raise ValueError("Для полной сборки требуется --review review.json. "
                         "Для технического прогона используйте --draft.")
    source = args.input.resolve(strict=True)
    output = args.output.resolve()
    if output.suffix.lower() != ".pdf" or output == source:
        raise ValueError("Укажите отдельный выходной файл .pdf")
    if not re.fullmatch(r"[\w .-]+", args.font):
        raise ValueError("Недопустимое имя шрифта")
    env = os.environ.copy()
    fonts = run(["fc-list", ":lang=ru", "family"], source.parent, env)
    if args.font.casefold() not in {f.strip().casefold() for f in re.split(r"[,\n]", fonts)}:
        raise ValueError(f"Шрифт с кириллицей не найден: {args.font}. Установите его "
                         "или укажите доступный шрифт через --font.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".gost-", dir=output.parent) as path:
        work = Path(path)
        front_count = 0
        if args.front_pdf:
            front = args.front_pdf.resolve(strict=True)
            if front == output:
                raise ValueError("Выходной PDF совпадает с вводными листами")
            if not all(is_a4(page) for page in PdfReader(front).pages):
                raise ValueError("Вводные листы должны быть книжными A4 без поворота")
            front_count = len(PdfReader(front).pages)
            shutil.copyfile(front, work / "front.pdf")
        env.update(GOST_NUMBERING=args.numbering, GOST_PROJECT=str(source.parent),
                   GOST_WORK=str(work), GOST_FRONT=str(front_count),
                   GOST_DRAFT=str(int(args.draft)))
        run(["pandoc", str(source), "-f",
             "markdown+implicit_figures-raw_html-raw_tex", "-t", "latex", "-s",
             "--lua-filter", str(ROOT / "scripts/gost.lua"),
             "--template", str(ROOT / "assets/gost.tex"), "--no-highlight",
             "-V", f"mainfont={args.font}",
             "-V", f"tablefont={args.table_font}",
             "-V", f"bodyfont={args.body_font}",
             "-o", "document.tex"], work, env)
        previous = None
        for _ in range(6):
            log = run(["xelatex", "-no-shell-escape", "-halt-on-error",
                       "-interaction=nonstopmode", "document.tex"], work, env)
            aux = tuple((work / name).read_bytes() if (work / name).exists() else b""
                        for name in ("document.aux", "document.toc", "document.out"))
            if aux == previous:
                break
            previous = aux
        else:
            raise ValueError("Содержание или ширины таблиц не стабилизировались")
        issues = [line for line in log.splitlines()
                  if ("Overfull" in line and not re.search(r"\([0-1]\.\d+pt too", line))
                  or "Missing character:" in line or "undefined references" in line
                  or "multiply defined" in line]
        if issues:
            raise ValueError("Исправьте переполнение или потерянные символы:\n" + "\n".join(issues))
        pdf = work / "document.pdf"
        reader = PdfReader(pdf)
        if not reader.pages or not all(is_a4(p) or is_a4(p, True) for p in reader.pages):
            raise ValueError("Неожиданный формат страницы")
        os.replace(pdf, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--review", type=Path, help="Coverage record from norms.py")
    parser.add_argument("--numbering", choices=["continuous", "section"], default="continuous")
    parser.add_argument("--body-font", type=int, choices=[12, 13, 14], default=14)
    parser.add_argument("--front-pdf", type=Path)
    parser.add_argument("--table-font", type=int, choices=[12, 14], default=12)
    parser.add_argument("--font", default="Times New Roman")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()
    try:
        build(args)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Сборка остановлена. {error}\n")
    print(args.output)


if __name__ == "__main__":
    main()
