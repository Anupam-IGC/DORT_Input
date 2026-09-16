# Documentation polish update

This update focuses on documentation usability rather than changing the DORT
physics/model semantics.

## Main changes

- Nested Sphinx navigation: Start / User Guide / Examples / API Reference.
- New landing pages with concise workflow-oriented links.
- Custom ReadTheDocs-theme CSS for wider content, cleaner cards, tables, and code blocks.
- Optional offline build mode: `DORT_DOCS_OFFLINE=1 make html`.
- Rewritten quick start and polished mixture, run-control, fixed-source, material,
  and writer pages.
- Five comprehensive runnable examples with corresponding documentation pages.
- Root README shortened to a project overview and navigation entry point.

No core DORT numbering or solver semantics were intentionally changed by this
package.
