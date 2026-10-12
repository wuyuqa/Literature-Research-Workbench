---
name: intake
description: Collect the user's research domain, task, constraints, data, output location, and connector authorization before routing.
---

Ask only what is missing. Collect: domain and subdomain, keywords, task type, target venue, language, date range, existing literature/idea/draft/results, desired output path, and whether Zotero import or email sending is authorized. Never assume network security or fuzzing. Never ask for token, password, SMTP authorization code, or private Zotero data; ask whether the corresponding environment variable or connector is already configured. Return a compact intake record for the orchestrator and write it to the configured Wiki only after the user agrees.
