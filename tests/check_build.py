"""Exercise the normal CLI and verify navigation, Cyrillic and failed-build safety."""
from pathlib import Path
import os
import subprocess
import sys
from tempfile import TemporaryDirectory

from pypdf import PdfReader

root = Path(__file__).resolve().parents[1]


def run(script, *args, success=True):
    result = subprocess.run([sys.executable, str(root / "scripts" / script), *map(str, args)], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise AssertionError(result.stdout + result.stderr)
    return result


with TemporaryDirectory() as directory:
    folder = Path(directory)
    source = folder / "report.md"
    output = folder / "report.pdf"
    source.write_text(
        "# Проверка PDF\n\n## Обзор\n\n[Итог](#итог)\n\n"
        "> [!TIP]\n> **Совет**\n>\n> - Первый\n> - Второй\n\n"
        "![Схема](diagram.svg)\n\n| Номер | Проверка |\n|---|---|\n"
        + "".join(f"| {i} | Строка таблицы |\n" for i in range(100))
        + "\n## Итог\n\nПроверка завершена.\n", encoding="utf-8"
    )
    (folder / "diagram.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 40"><rect width="200" height="40" fill="#247578"/></svg>'
    )
    browser_args = ["--browser-executable", os.environ["TEST_BROWSER"]] if os.environ.get("TEST_BROWSER") else []
    run("build_pdf.py", source, "-o", output, "--lang", "ru", *browser_args)
    run("verify_pdf.py", output, "--require-outline", "--require-tagged", "--require-text", "--public")
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) >= 2
    assert all(word in text for word in ["Проверка завершена", "Первый", "Второй", "99"])
    before = output.read_bytes()
    source.write_text("# Broken\n\n[missing](#missing)", encoding="utf-8")
    run("build_pdf.py", source, "-o", output, success=False)
    assert output.read_bytes() == before
    run("verify_pdf.py", output, "--forbidden", "Проверка", success=False)
print("PDF integration checks passed")
