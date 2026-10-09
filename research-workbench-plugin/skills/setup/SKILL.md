---
name: setup
description: Initialize and validate the Literature Research Workbench without modifying the existing vault structure.
---

Read `config.yaml` if it exists; otherwise explain how to create it from `config.example.yaml`. Validate that `vault_root` exists, that the configured `wiki_root` is writable, and that the output directory is ignored by Git. Explain that Zotero and Undermind must be connected in Codex before live actions work. Never request or store passwords, SMTP authorization codes, or API tokens in repository files. Finish with a short checklist and the first safe read-only test.
