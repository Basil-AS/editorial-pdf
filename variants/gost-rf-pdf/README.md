# Editorial PDF — GOST add-on 2.0.2-gost.1

This is an optional companion to Editorial PDF 2.0.1. It preserves the base skill and adds the supplied GOST workflow as a separate profile with its original source package: the skill instructions, applicability map, review guides, searchable text, 21 source PDFs, integrity catalog and scripts. Its PDF builder uses 16 pt body text, same-size headings, 14 pt table text, compact content-width tables, tighter heading spacing and PDF outline navigation without a printed contents page. ГОСТ 7.32 requires body text no smaller than 12 pt. It permits omitting the contents for reports up to and including 10 pages. For longer reports, the owner's preference is a documented deviation; do not claim full structural conformity when the printed contents is omitted.

## Use

Load `SKILL.md` for the GOST-specific workflow. The package requires Python 3.10 or later, Pandoc 3.1 or later, XeLaTeX with the template packages, Poppler, and the Python libraries in `requirements.txt`.

```bash
python -m pip install -r requirements.txt
python scripts/norms.py catalog
python scripts/norms.py verify-sources
python scripts/norms.py plan review.json --kind "Отчёт о НИР"
```

For every `apply` entry, record `edition_basis` (`current` or `contractual`), `edition_checked_on`, an official registry card URL, and `edition_evidence`. The validator refuses applicable entries without this record and blocks the five archived editions known to have lost force in Russia from being marked current. Contractually fixed editions require the exact clause or task reference.

For a ГОСТ 7.32 report, follow `references/build.md`, record an apply/not_applicable decision and evidence for every source in `review.json`, build with `scripts/build_pdf.py`, and run the final review checks. The bundled Markdown builder is for the ГОСТ 7.32 profile. ЕСКД, ЕСПД, ТЗ, ПМИ and standards projects need their document-specific structure and forms from the included sources.

## Scope and limits

The package preserves the editions provided with this add-on; it is not a consolidated current normative library. In particular, five included bibliographic standards are no longer in force in the Russian Federation. Read the required [edition status register](references/edition-status.md), then verify every applicable edition, amendment and referenced document in the official register for the document's jurisdiction and submission date. The `norms.py` integrity and review checks ensure the archive and review record are complete; they do not establish that evidence is correct, that every clause is met, or certify a document.
