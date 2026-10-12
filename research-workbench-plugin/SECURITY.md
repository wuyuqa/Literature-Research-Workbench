# 配置和隐私

插件仓库只保存技能、角色提示、模板和不含个人数据的示例配置。以下内容禁止提交：

- `config.yaml`、`.env`、SMTP 授权码、API token、私钥和 OAuth 文件；
- `.research-wiki/`、`outputs/`、论文 PDF、Zotero 导出库和邮件地址清单；
- 周报运行生成的 JSON、日志和 `__pycache__`。

配置入口是 `config.example.yaml`。复制成 `config.yaml` 后只在本地填写。SMTP 使用 `NETEASE_SMTP_AUTH_CODE` 环境变量，Semantic Scholar、Exa、Gemini 分别使用对应的环境变量。Codex 的 Zotero 和 Undermind 授权通过 connector 完成，不写入仓库。

上传 GitHub 前运行：

```powershell
.\scripts\github-preflight.ps1
```

脚本只报告疑似凭据所在文件名和行号，不打印匹配内容。
