# Editorial PDF — GOST add-on 2.0.1-gost.1

This is an optional companion to Editorial PDF 2.0.1. It preserves the base skill and adds the supplied GOST workflow as a separate profile with its original source package: the skill instructions, applicability map, review guides, searchable text, 21 source PDFs, integrity catalog and scripts.

## Use

Load `SKILL.md` for the GOST-specific workflow. The package requires Python 3.10 or later, Pandoc 3.1 or later, XeLaTeX with the template packages, Poppler, and the Python libraries in `requirements.txt`.

```bash
python -m pip install -r requirements.txt
python scripts/norms.py catalog
python scripts/norms.py verify-sources
python scripts/norms.py plan review.json --kind "Отчёт о НИР"
```

For a ГОСТ 7.32 report, follow `references/build.md`, record an apply/not_applicable decision and evidence for every source in `review.json`, build with `scripts/build_pdf.py`, and run the final review checks. The bundled Markdown builder is for the ГОСТ 7.32 profile. ЕСКД, ЕСПД, ТЗ, ПМИ and standards projects need their document-specific structure and forms from the included sources.

## Scope and limits

The package preserves the editions provided with this add-on. Its integrity checks verify the supplied source files and workflow records; they do not establish that the editions are current, prove every clause is satisfied, or certify an output document. Verify current status and changes separately when current normative compliance is required. Check the catalog for the scope and edition of each included source.
