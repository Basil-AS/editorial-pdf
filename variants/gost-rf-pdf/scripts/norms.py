#!/usr/bin/env python3
"""Find supplied standard pages and maintain an explicit coverage record."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references/catalog.json"
GUIDES = ROOT / "references/review-guides.md"
SUPERSEDED_IN_RF = {
    "gost-7-1-2003", "gost-7-9-95", "gost-7-80-2000",
    "gost-7-82-2001", "gost-7-12-93",
}


def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def checks():
    result = {}
    current = None
    for line in GUIDES.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:]
            result[current] = []
        elif current and line.startswith("- "):
            result[current].append(line[2:])
    return result


def pages(item):
    text = (ROOT / item["text"]).read_text(encoding="utf-8")
    return [(int(n), s) for n, s in re.findall(
        r"\[PDF page (\d+)\]\n(.*?)(?=\n\[PDF page \d+\]|\Z)", text, re.S)]


def validate(plan, final=False):
    errors = []
    if not isinstance(plan, dict):
        return ["Корневая запись должна быть JSON-объектом"]
    entries = plan.get("standards", {})
    if not isinstance(entries, dict):
        return ["Поле standards должно быть JSON-объектом"]
    rules = checks()
    expected = {item["id"] for item in catalog()}
    if set(entries) != expected:
        errors.append("Запись должна содержать ровно все обозначения каталога")
    if not isinstance(plan.get("document_kind"), str) or not plan["document_kind"].strip():
        errors.append("Не указан вид документа")
    for key in sorted(expected):
        item = entries.get(key, {})
        if not isinstance(item, dict):
            errors.append(f"{key}: запись источника должна быть JSON-объектом")
            continue
        decision = item.get("decision")
        if decision not in {"apply", "not_applicable"}:
            errors.append(f"{key}: определите применимость")
        if decision == "apply":
            basis = item.get("edition_basis")
            if basis not in {"current", "contractual"}:
                errors.append(f"{key}: применяйте только проверенную действующую редакцию "
                              "или укажите договорно закреплённую")
            if key in SUPERSEDED_IN_RF and basis == "current":
                errors.append(f"{key}: редакция не действует в РФ; отметьте not_applicable "
                              "и добавьте действующую замену как внешний источник либо "
                              "зафиксируйте договорное основание")
            try:
                date.fromisoformat(item.get("edition_checked_on", ""))
            except (TypeError, ValueError):
                errors.append(f"{key}: укажите дату проверки статуса YYYY-MM-DD")
            registry = item.get("edition_registry_url")
            if not isinstance(registry, str) or not registry.startswith("https://"):
                errors.append(f"{key}: укажите HTTPS-ссылку на официальный реестр")
            evidence = item.get("edition_evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                errors.append(f"{key}: укажите результат проверки статуса и редакции")
            elif basis == "contractual" and not re.search(
                    r"(договор|контракт|ТЗ|спецификац|задани|пункт|раздел)",
                    evidence, re.I):
                errors.append(f"{key}: для договорной редакции укажите конкретный пункт "
                              "договора/ТЗ/задания")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            errors.append(f"{key}: отсутствует обоснование")
        selected = item.get("checks", [])
        if not isinstance(selected, list) or len(selected) != len(rules[key]):
            errors.append(f"{key}: неполный перечень проверок")
            continue
        for index, check in enumerate(selected):
            label = f"{key}/{index+1}"
            if not isinstance(check, dict):
                errors.append(f"{label}: запись проверки должна быть JSON-объектом")
                continue
            if check.get("requirement") != rules[key][index]:
                errors.append(f"{label}: изменено описание проверки")
            status = check.get("status")
            if decision == "apply":
                allowed = {"passed", "not_applicable"} if final else {
                    "pending", "passed", "not_applicable"}
                if status not in allowed:
                    errors.append(f"{label}: проверка не завершена")
                if status in {"passed", "not_applicable"}:
                    if not isinstance(check.get("evidence"), str) or not check["evidence"].strip():
                        errors.append(f"{label}: отсутствует свидетельство или причина")
            elif decision == "not_applicable" and status != "not_applicable":
                errors.append(f"{label}: согласуйте статус с решением по стандарту")
        if decision == "apply":
            read_pages = item.get("read_pages", [])
            limit = next(s["pages"] for s in catalog() if s["id"] == key)
            if not isinstance(read_pages, list) or not read_pages or any(
                    type(p) is not int or not 1 <= p <= limit for p in read_pages):
                errors.append(f"{key}: укажите действительно прочитанные страницы PDF")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    read = sub.add_parser("read")
    read.add_argument("id")
    read.add_argument("--pages", required=True, help="Physical PDF pages, e.g. 2,5-8")
    query = sub.add_parser("search")
    query.add_argument("query", help="Case-insensitive literal text")
    query.add_argument("--id")
    query.add_argument("--limit", type=int, default=15)
    sub.add_parser("verify-sources")
    plan = sub.add_parser("plan")
    plan.add_argument("output", type=Path)
    plan.add_argument("--kind", required=True)
    check = sub.add_parser("check")
    check.add_argument("input", type=Path)
    check.add_argument("--final", action="store_true")
    args = parser.parse_args()
    items = catalog()
    if args.command == "catalog":
        for item in items:
            print(item["id"], item["pages"], item["file"])
    elif args.command == "verify-sources":
        for item in items:
            pdf = ROOT / item["pdf"]
            if hashlib.sha256(pdf.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Источник изменён: " + item["id"])
            if hashlib.sha256((ROOT / item["text"]).read_bytes()).hexdigest() != item["text_sha256"]:
                raise ValueError("Текст источника изменён: " + item["id"])
            values = pages(item)
            if [n for n, _ in values] != list(range(1, item["pages"] + 1)):
                raise ValueError("Потеряна страница текста: " + item["id"])
            if any(not text.strip() and n not in item.get("blank_pages", []) for n, text in values):
                raise ValueError("Пустая страница извлечения: " + item["id"])
        if set(checks()) != {s["id"] for s in items}:
            raise ValueError("Не для всех источников есть маршрут проверки")
        print(f"Проверены источники и маршруты: {len(items)}")
    elif args.command == "read":
        item = next((s for s in items if s["id"] == args.id), None)
        if item is None:
            parser.error("Неизвестное обозначение")
        numbers = set()
        for interval in args.pages.split(","):
            edges = interval.split("-")
            start, end = int(edges[0]), int(edges[-1])
            if len(edges) > 2 or not 1 <= start <= end <= item["pages"]:
                parser.error("Страница вне источника")
            numbers.update(range(start, end + 1))
        for number, text in pages(item):
            if number in numbers:
                print(f"\n{item['id']} / PDF page {number}\n{text}")
    elif args.command == "search":
        if args.id and not any(s["id"] == args.id for s in items):
            parser.error("Неизвестное обозначение")
        if args.limit < 1 or not args.query.strip():
            parser.error("Нужен непустой запрос и положительный limit")
        count = 0
        for item in items:
            if args.id and args.id != item["id"]:
                continue
            for number, text in pages(item):
                for match in re.finditer(re.escape(args.query), text, re.I):
                    print(f"\n{item['id']} / PDF page {number}\n"
                          + text[max(0, match.start()-180):match.end()+400])
                    count += 1
                    if count >= args.limit:
                        return
        if count == 0:
            print("Совпадений нет. Проверьте перенос слова и исходный PDF.")
    elif args.command == "plan":
        rules = checks()
        output = {"document_kind": args.kind, "standards": {
            s["id"]: {"decision": "pending", "reason": "", "read_pages": [],
                      "edition_basis": "pending", "edition_checked_on": "",
                      "edition_registry_url": "", "edition_evidence": "",
                      "checks": [{"requirement": rule, "status": "pending", "evidence": ""}
                                 for rule in rules[s["id"]]]} for s in items}}
        # Refuse overwriting an existing review record.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(output, stream, ensure_ascii=False, indent=2)
        print(args.output)
    elif args.command == "check":
        failures = validate(json.loads(args.input.read_text(encoding="utf-8")), args.final)
        if failures:
            parser.exit(1, "\n".join(failures) + "\n")
        print("Запись учёта проверена. Содержательность свидетельств проверяет исполнитель.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, TypeError, KeyError) as error:
        raise SystemExit(str(error))
