# Editorial PDF

[![CI](https://github.com/Basil-AS/editorial-pdf/actions/workflows/ci.yml/badge.svg)](https://github.com/Basil-AS/editorial-pdf/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Basil-AS/editorial-pdf)](https://github.com/Basil-AS/editorial-pdf/releases)

Create and verify polished PDF reports from Markdown, with Cyrillic typography, hierarchical bookmarks, embedded diagrams and tables that continue across pages.

## Get started

Download a versioned skill archive from [Releases](https://github.com/Basil-AS/editorial-pdf/releases), or clone this repository. The archive contains the skill instructions, Python scripts, print stylesheet and reference material.

For an AI agent, load [SKILL.md](SKILL.md). For direct command-line use, install Python 3.10 or later and run these commands from the repository root.

## Install the Codex marketplace

In Codex, add `git@github.com:Basil-AS/editorial-pdf.git` with Git ref `master` and these two sparse paths, each on its own line:

```text
.agents/plugins
plugins/codex
```

The repository contains a curated `Editorial PDF` plugin with the base PDF and GOST 7.32 skills. The source-of-truth skills remain in the repository root and `variants/gost-rf-pdf`; CI checks that the marketplace copies stay synchronized. The `main` ref does not exist in this repository.

The same source can be added from the Codex CLI:

```bash
codex plugin marketplace add git@github.com:Basil-AS/editorial-pdf.git --ref master --sparse .agents/plugins --sparse plugins/codex
```

```bash
python -m venv .venv
# Linux and macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python -m playwright install chromium
mkdir -p output
python scripts/build_pdf.py examples/report.md -o output/report.pdf
python scripts/verify_pdf.py output/report.pdf --require-outline --require-tagged --require-text --public
```

On Windows, create the output directory with `New-Item -ItemType Directory -Force output`. For Russian labels and page numbering, pass `--lang ru`. Use `--paper Letter` when needed. Install Noto or DejaVu fonts for consistent Cyrillic rendering.

## Capabilities

| Feature | Behavior |
|---|---|
| Typography | Local fonts, A4 or Letter, running title and page numbers |
| Markdown | Headings, pipe tables, lists, code and five GitHub callout types |
| Images | Embedded SVG, PNG, JPEG, WebP and GIF from local files |
| Navigation | Heading anchors, hierarchical bookmarks and verified destinations |
| Long content | Repeated table headers, row-level page breaks and wrapped code |
| Companions | Optional relative file links retaining directories and fragments |
| Failed builds | Existing PDF is replaced only after successful rendering |
| Audit | Optional text, outline, tags and disclosure indicator checks |

See [builder options](references/builder.md) and [existing PDF guidance](references/existing-pdf.md). Render and visually inspect every final page. Structural tags alone do not establish PDF/UA compliance.

## Versions and history

| Version | Scope | Merged changes |
|---|---|---|
| 1.0.0 | Cleaned original implementation | [#1](https://github.com/Basil-AS/editorial-pdf/pull/1), [#2](https://github.com/Basil-AS/editorial-pdf/pull/2) |
| 2.0.0 | Rewritten builder, stylesheet and verifier | [#3](https://github.com/Basil-AS/editorial-pdf/pull/3), [#4](https://github.com/Basil-AS/editorial-pdf/pull/4) |
| 2.0.1 | CI, release packaging and repository documentation | Repository maintenance |
| 2.0.1-gost.1 | Companion profile with the supplied 21-standard GOST set, source PDFs, review guidance and a ГОСТ 7.32 builder | [GOST add-on](variants/gost-rf-pdf/README.md) |
| 2.0.1-codex.1 | Codex marketplace catalog with Editorial PDF and GOST skills | [Codex plugin source](plugins/codex) |

Versioned release archives include SHA-256 checksum files. The GOST companion and Codex marketplace package are distributed as separate tar.gz archives. Version 2.0 changes CLI options. Consult `python scripts/build_pdf.py --help` when migrating from 1.0.

The GOST add-on is a separately versioned profile. It includes the editions supplied in its source package and keeps their text, PDF originals, applicability map, review guides and source-integrity checks together. It does not change the default 2.0.1 profile. Its Markdown builder implements the ГОСТ 7.32 profile; other document families require their own applicable forms and layouts. The included review ledger records applicability and evidence, but its checks do not by themselves certify a document as compliant or confirm that an edition is current.

## Development and delivery

`master` holds the integrated project. Use a temporary feature or maintenance branch and a pull request into `master`, then merge with a merge commit after CI succeeds. Delete merged branches. The original Gitflow PRs remain available in the history.

CI builds a multi-page Russian report with SVG, a 100-row table and internal links. It verifies navigation, structure, text extraction and preservation of a previous PDF after a failed build. A separate sample PDF is retained as an Actions artifact.

After successful checks on `master`, the release job publishes the versioned archives and checksums. Release targets are recorded explicitly in the workflow. Update the release version and notes when preparing a new release.

Contributions produced with Codex include `Co-authored-by: Codex <codex@openai.com>` in the commit message.
