#!/usr/bin/env python3
"""Exercise GOST review record validation and legacy-edition safeguards."""
from pathlib import Path
import sys

SCRIPT = Path(__file__).resolve().parents[1] / "variants/gost-rf-pdf/scripts/norms.py"
sys.path.insert(0, str(SCRIPT.parent))
import norms


def complete_not_applicable():
    guides = norms.checks()
    return {
        "document_kind": "Проверка валидатора",
        "standards": {
            item["id"]: {
                "decision": "not_applicable",
                "reason": "Не относится к проверочному фрагменту",
                "read_pages": [],
                "checks": [
                    {"requirement": rule, "status": "not_applicable",
                     "evidence": "Проверочный фрагмент не является таким документом"}
                    for rule in guides[item["id"]]
                ],
            }
            for item in norms.catalog()
        },
    }


def main():
    baseline = complete_not_applicable()
    assert norms.validate(baseline) == []
    broken_shape = {"document_kind": "bad", "standards": []}
    assert norms.validate(broken_shape)

    legacy = complete_not_applicable()
    record = legacy["standards"]["gost-7-1-2003"]
    record.update({
        "decision": "apply",
        "reason": "Включён по ошибке как текущая редакция",
        "read_pages": [1],
        "edition_basis": "current",
        "edition_checked_on": "2026-11-20",
        "edition_registry_url": "https://protect.gost.ru/gost",
        "edition_evidence": "Ошибочная проверка",
        "checks": [
            {"requirement": rule, "status": "passed", "evidence": "Проверено"}
            for rule in norms.checks()["gost-7-1-2003"]
        ],
    })
    assert any("утратила силу в РФ" in error for error in norms.validate(legacy))

    malformed = complete_not_applicable()
    malformed["standards"]["gost-7-1-2003"]["checks"] = [None]
    assert norms.validate(malformed)
    print("Проверки записи ГОСТ пройдены")


if __name__ == "__main__":
    main()
