#!/usr/bin/env python3
"""Validate the Codex marketplace catalog and both plugin manifests."""
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents/plugins/marketplace.json"
PLUGIN_ROOT = ROOT / "plugins/codex"


def read_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def check():
    marketplace = read_json(MARKETPLACE)
    plugin = read_json(PLUGIN_ROOT / "plugin.json")
    compatibility = read_json(PLUGIN_ROOT / ".codex-plugin/plugin.json")
    assert marketplace["name"] == "basil-editorial-pdf"
    assert marketplace["interface"]["displayName"]
    assert len(marketplace["plugins"]) == 1
    entry = marketplace["plugins"][0]
    assert entry["name"] == plugin["name"] == compatibility["name"] == "codex"
    assert entry["source"] == {"source": "local", "path": "./plugins/codex"}
    assert entry["policy"] == {
        "installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert entry["category"] == "Productivity"
    assert plugin["$schema"] == (
        "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
    assert plugin["version"] == compatibility["version"] == "2.0.2"
    interface = plugin["extensions"]["com.openai"]["interface"]
    for field in ("displayName", "shortDescription", "longDescription",
                  "developerName", "category"):
        assert interface[field].strip()
        assert compatibility["interface"][field] == interface[field]
    assert len(interface["shortDescription"]) <= 30
    assert interface["category"] == entry["category"]
    assert compatibility["skills"] == "./skills/"

    for field in ("logo", "composerIcon"):
        icon = PLUGIN_ROOT / interface[field].removeprefix("./")
        assert icon.is_file()
        root = ET.parse(icon).getroot()
        width = int(root.attrib["width"])
        height = int(root.attrib["height"])
        assert width >= 48 and height >= 48 and width == height

    skills = PLUGIN_ROOT / "skills"
    for folder in ("editorial-pdf", "gost-rf-pdf"):
        skill = skills / folder / "SKILL.md"
        contents = skill.read_text(encoding="utf-8")
        assert contents.startswith("---\n")
        header = contents.split("---\n", 2)[1]
        assert re.search(r"(?m)^name:\s*\S+", header)
        assert re.search(r"(?m)^description:\s*\S+", header)
    assert (skills / "editorial-pdf/scripts/build_pdf.py").is_file()
    assert (skills / "gost-rf-pdf/assets/standards/gost-7-32-2017.pdf").is_file()
    print("Codex marketplace manifests and plugin payload are valid")


if __name__ == "__main__":
    check()
