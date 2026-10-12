---
name: setup
description: Initialize and validate the Literature Research Workbench without modifying the existing vault structure.
---

Read `config.yaml` if it exists; otherwise explain how to create it from `config.example.yaml` and run the intake questionnaire. Do not assume the example domain. Validate `vault_root` and the four top-level directories in `vault_layout`: `10_Weekly`, `20_Research`, `30_Synthesis`, and `99_System`. Map outputs to the existing layout described in `wiki/vault-layout.md`; ask before creating missing subdirectories and never move, rename, or overwrite existing notes. If the user chooses `sidecar`, use a separate `.research-wiki/` tree instead. Check that the ARS, ARIS, Frontend Slides, Zotero, and Undermind dependencies are available before routing tasks. Never request or store passwords, SMTP authorization codes, or API tokens in repository files. Explain the environment-variable entry points for SMTP and optional search APIs. Finish with a checklist and a read-only test before any import, email, or write operation.
