---
name: send-email
description: 通过网易 163 SMTP（端口 465 SSL）发送 markdown 渲染为 html 的邮件。用于每周论文推荐和顶会推荐的邮件推送。读取 academic_agent.yaml 中的邮件配置。
allowed-tools: Read, Write, Bash
---

# 邮件发送

## 目标

把 markdown 格式的论文推荐报告渲染为 html 后，通过 SMTP 发送到用户指定邮箱。

## 先决条件

`E:\obsidian_note\文献管理库\文献知识库\99_System\Config\academic_agent.yaml` 中已配置：

```yaml
email:
  smtp_server: "smtp.163.com"
  smtp_port: 465
  use_ssl: true
  sender: "your_email@163.com"           # 用户填
  auth_code: "TFfwmJ5MwSvPZiCx"          # 163 客户端授权码
  recipient: "recipient@example.com"      # 用户填
```

如果 `sender` 或 `recipient` 为空，本 skill 报错并提示用户填写。

## 输入

- `--subject` 邮件主题
- `--md-file` 或 `--md` markdown 正文（互斥）
- `--config` 配置 yaml 路径（可选，默认从环境变量 `OBSIDIAN_VAULT_PATH` 推断）

## 调用方式

### 命令行（独立测试）

```powershell
# 文件方式
python "C:/Users/86159/.claude/skills/send-email/scripts/send_email.py" `
  --config "E:/obsidian_note/文献管理库/文献知识库/99_System/Config/academic_agent.yaml" `
  --subject "[周报] 2026-W22 论文推荐" `
  --md-file "C:/temp/weekly_report.md"

# 直接 markdown 字符串
python "C:/Users/86159/.claude/skills/send-email/scripts/send_email.py" `
  --config "..." --subject "test" --md "# Hello`n`n正文"
```

### Agent 内调用

`/send-email --subject {主题} --md-file {markdown_path}`

## Markdown 渲染规则

- 使用 Python `markdown` 库（`pip install markdown`），开启 `extra`, `tables`, `fenced_code`, `nl2br` 扩展
- 在 html 顶部自动插入：
  - 邮件发送时间
  - 邮件类型（周报 / 顶会）
- 包裹 `<html><head><meta charset="utf-8"><style>...</style></head><body>` 提供基础样式
- 内联简单 CSS（表格边框、代码块背景、wikilink 转链接）

## 错误处理

| 场景 | 行为 |
|------|------|
| sender/recipient 为空 | 报错退出，提示用户编辑 yaml |
| SMTP 连接失败 | 重试 1 次，失败则报错（让上游 skill 决定是否继续） |
| 认证失败（535） | 报错并提示用户检查授权码或邮箱开启 SMTP |
| 编码异常（中文标题） | 使用 RFC 2047 编码主题 |

## 网易 163 SMTP 注意事项

- 端口 465（SSL）或 994（SSL）或 25（无加密，不推荐）
- 必须使用客户端授权码，不能用登录密码
- 单封邮件大小限制 50MB
- 单日发件量有限制，避免频繁触发

## 输出

控制台打印：
- 发送成功：`Email sent: {subject} -> {recipient}`
- 失败：详细错误信息

退出码：0 成功，非 0 失败
