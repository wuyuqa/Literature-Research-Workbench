---
name: send-email
description: Send a Markdown weekly literature digest through the user's configured 163 SMTP account.
---

Use the 163 SMTP connector or the local `send_email.py` helper only after the user has explicitly enabled email sending. Read `smtp.host`, `smtp.port`, `smtp.username`, `smtp.recipients`, and `smtp.auth_code_env` from `config.yaml`; read the authorization code from the named environment variable. Never ask the user to paste a password or authorization code into chat or a repository file. If SMTP is disabled or the environment variable is missing, produce the digest file and report the missing configuration without sending.
