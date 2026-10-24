# Diagrams: archived report figures

The Mermaid sources (`*.mmd`) in this folder, the PNGs under [`rendered/`](rendered) and the
plotting scripts under [`figures/`](figures) are the figures of the archived Psyche technical
report. Its master source is [`REPORT.md`](../REPORT.md), and the published artifact is under
[`docs/report/`](../report).

They are kept as the record of that report, not maintained. Some of them show the project as it
stood when the report was written. The `.mmd` sources and the PNGs are not read by
`tools/ledger_check.py`, which reads Markdown, LaTeX and Python files but not Mermaid sources
or images. [`tools/publish/check_copy.py`](../../tools/publish/check_copy.py) does not read
them either. They are archived figures, historical by design, and are published nowhere: the
docs site and the wiki take no `.mmd` from here. A stale figure in one of them is a record, not
current copy. For the current state of Psyche,
read [`tools/ledger.json`](../../tools/ledger.json) and [`ARCHITECTURE.md`](../ARCHITECTURE.md).

Current diagrams live inside Markdown pages as fenced Mermaid blocks, where GitHub renders them
and the same checks that read the surrounding prose read them too. The thesis diagrams are on
the pages under [`docs/thesis/`](../thesis/README.md). No new `.mmd` files are added here.
