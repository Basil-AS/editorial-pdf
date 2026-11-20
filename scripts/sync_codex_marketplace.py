#!/usr/bin/env python3
"""Build or check the checked-in Codex plugin skill payloads."""
import argparse
import filecmp
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SKILLS = Path("plugins/codex/skills")


def copy_tree(source, destination, ignore_agents=False):
    ignore = shutil.ignore_patterns("agents") if ignore_agents else None
    shutil.copytree(source, destination, ignore=ignore)


def populate(skills_root):
    if skills_root.exists():
        shutil.rmtree(skills_root)
    skills_root.mkdir(parents=True)

    editorial = skills_root / "editorial-pdf"
    editorial.mkdir()
    shutil.copy2(ROOT / "SKILL.md", editorial / "SKILL.md")
    for name in ("assets", "references"):
        copy_tree(ROOT / name, editorial / name)
    scripts = editorial / "scripts"
    scripts.mkdir()
    for name in ("build_pdf.py", "verify_pdf.py"):
        shutil.copy2(ROOT / "scripts" / name, scripts / name)
    shutil.copy2(ROOT / "requirements.txt", editorial / "requirements.txt")

    copy_tree(ROOT / "variants/gost-rf-pdf", skills_root / "gost-rf-pdf",
              ignore_agents=True)


def same_tree(left, right):
    if not left.is_dir() or not right.is_dir():
        return False
    comparison = filecmp.dircmp(left, right, ignore=["__pycache__", ".DS_Store"])
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    return (all(filecmp.cmp(left / name, right / name, shallow=False)
                for name in comparison.common_files)
            and all(same_tree(left / name, right / name)
                    for name in comparison.common_dirs))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if checked-in plugin payloads are out of sync")
    args = parser.parse_args()
    destination = ROOT / PLUGIN_SKILLS
    if args.check:
        with tempfile.TemporaryDirectory(prefix="codex-marketplace-") as temporary:
            expected = Path(temporary) / "skills"
            populate(expected)
            if not same_tree(expected, destination):
                raise SystemExit("Codex plugin skill payloads are out of sync; run "
                                 "python scripts/sync_codex_marketplace.py")
        print("Codex marketplace skill payloads are in sync")
    else:
        populate(destination)
        print(destination.relative_to(ROOT))


if __name__ == "__main__":
    main()
