#!/usr/bin/env python3
"""
通过 163 SMTP 发送 markdown 渲染为 html 的邮件。

用法：
    python send_email.py --config <yaml> --subject <s> --md-file <f>
    python send_email.py --config <yaml> --subject <s> --md "<markdown text>"
"""

from __future__ import annotations

import argparse
import logging
import smtplib
import ssl
import sys
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from pathlib import Path

logger = logging.getLogger(__name__)


def load_yaml(path: Path) -> dict:
    """轻量 yaml 加载。"""
    try:
        import yaml  # type: ignore
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        logger.error("PyYAML not installed. Run: pip install PyYAML")
        sys.exit(2)


def render_markdown_to_html(md_text: str, subject: str) -> str:
    """把 markdown 渲染为带样式的 html。"""
    try:
        import markdown  # type: ignore
    except ImportError:
        logger.error("markdown library not installed. Run: pip install markdown")
        sys.exit(2)

    body_html = markdown.markdown(
        md_text,
        extensions=["extra", "tables", "fenced_code", "nl2br", "toc"],
    )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    style = """
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
             max-width: 880px; margin: 24px auto; padding: 0 16px; color: #24292e;
             font-size: 15px; line-height: 1.6; }
      h1 { border-bottom: 2px solid #e1e4e8; padding-bottom: 6px; }
      h2 { border-bottom: 1px solid #e1e4e8; padding-bottom: 4px; margin-top: 28px; }
      h3 { margin-top: 22px; color: #0366d6; }
      a { color: #0366d6; text-decoration: none; }
      a:hover { text-decoration: underline; }
      code { background: #f6f8fa; padding: 2px 6px; border-radius: 3px; font-size: 90%; }
      pre code { display: block; padding: 12px; overflow-x: auto; }
      blockquote { color: #6a737d; border-left: 4px solid #dfe2e5; padding: 0 12px; margin: 12px 0; }
      table { border-collapse: collapse; margin: 12px 0; }
      th, td { border: 1px solid #dfe2e5; padding: 6px 12px; }
      th { background: #f6f8fa; }
      .meta { color: #6a737d; font-size: 13px; margin-bottom: 16px; padding: 8px 12px;
              background: #f6f8fa; border-left: 3px solid #0366d6; }
    </style>
    """

    meta = f"""
    <div class="meta">
      <strong>📬 {subject}</strong><br/>
      发送时间：{timestamp}
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>{subject}</title>
  {style}
</head>
<body>
  {meta}
  {body_html}
</body>
</html>
"""
    return html


def send_email(
    smtp_server: str,
    smtp_port: int,
    use_ssl: bool,
    sender: str,
    auth_code: str,
    recipient: str,
    subject: str,
    html_body: str,
    md_body: str | None = None,
) -> None:
    """通过 SMTP 发送 html 邮件。失败抛出异常。"""
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((str(Header("Academic Agent", "utf-8")), sender))
    msg["To"] = recipient
    msg["Subject"] = Header(subject, "utf-8")
    msg["Date"] = formatdate(localtime=True)

    if md_body:
        msg.attach(MIMEText(md_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=30)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.starttls(context=context)

    try:
        server.login(sender, auth_code)
        server.sendmail(sender, [recipient], msg.as_string())
        logger.info("Email sent: %r -> %s", subject, recipient)
    finally:
        try:
            server.quit()
        except smtplib.SMTPException:
            pass


def main():
    parser = argparse.ArgumentParser(description="Send markdown email via SMTP")
    parser.add_argument("--config", required=True, help="academic_agent.yaml path")
    parser.add_argument("--subject", required=True, help="Email subject")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--md-file", help="Markdown file path")
    group.add_argument("--md", help="Markdown text inline")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        return 1
    config = load_yaml(config_path)
    email_cfg = config.get("email", {}) or {}

    sender = (email_cfg.get("sender") or "").strip()
    recipient = (email_cfg.get("recipient") or "").strip()
    auth_code = (email_cfg.get("auth_code") or "").strip()
    if not sender:
        logger.error("email.sender is empty in %s — please fill it", config_path)
        return 1
    if not recipient:
        logger.error("email.recipient is empty in %s — please fill it", config_path)
        return 1
    if not auth_code:
        logger.error("email.auth_code is empty in %s", config_path)
        return 1

    smtp_server = email_cfg.get("smtp_server", "smtp.163.com")
    smtp_port = int(email_cfg.get("smtp_port", 465))
    use_ssl = bool(email_cfg.get("use_ssl", True))

    if args.md_file:
        md_text = Path(args.md_file).read_text(encoding="utf-8")
    else:
        md_text = args.md

    html_body = render_markdown_to_html(md_text, args.subject)

    try:
        send_email(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            use_ssl=use_ssl,
            sender=sender,
            auth_code=auth_code,
            recipient=recipient,
            subject=args.subject,
            html_body=html_body,
            md_body=md_text,
        )
        print(f"Email sent: {args.subject!r} -> {recipient}")
        return 0
    except smtplib.SMTPAuthenticationError as e:
        logger.error("SMTP authentication failed: %s", e)
        logger.error("Please check email.auth_code in %s and that SMTP service is enabled in your 163 mailbox", config_path)
        return 3
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
        return 4
    except (OSError, ssl.SSLError) as e:
        logger.error("Network/SSL error: %s", e)
        return 5


if __name__ == "__main__":
    sys.exit(main())
