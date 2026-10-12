---
name: setup
description: Initialize and validate the Literature Research Workbench without modifying the existing vault structure.
---

Read `config.yaml` if it exists; otherwise explain how to create it from `config.example.yaml` and run the intake questionnaire. Do not assume the example domain. Validate that `vault_root` exists, that the configured `wiki_root` is writable, and that the output directory is ignored by Git. Create the documented Wiki folders (`00_System`, `01_Literature`, `02_Themes`, `03_Ideas`, `04_ExperimentPlans`, `05_Manuscripts`, `06_Figures`, `07_Presentations`, `90_Reports`) under a new or sidecar `wiki_root`; do not move existing notes. Check that the ARS, ARIS, Frontend Slides, Zotero, and Undermind dependencies are available before routing tasks. Never request or store passwords, SMTP authorization codes, or API tokens in repository files. Explain the environment-variable entry points for SMTP and optional search APIs. Finish with a checklist and a read-only test before any import, email, or write operation.
