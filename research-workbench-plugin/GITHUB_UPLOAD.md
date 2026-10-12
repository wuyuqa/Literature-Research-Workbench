# GitHub 上传清单

建议上传版本：`v0.1.5`（当前插件 manifest 版本）。上传对象只选 `research-workbench-plugin/`，不要把整个 Obsidian 知识库作为插件仓库上传。

上传前：

1. 删除或确认没有 `config.yaml`、`.env`、`.research-wiki/`、`outputs/`、PDF、Zotero 导出文件和授权文件。
2. 运行 `scripts/github-preflight.ps1`。
3. 检查 `git diff --cached`，确认没有 token、密码、邮件授权码或本机绝对路径。
4. 提交并打 tag：

```powershell
git add research-workbench-plugin
git commit -m "Release literature research workbench 0.1.5"
git tag v0.1.5
git push origin master --tags
```

新用户下载插件目录后运行 `install.ps1`。用户自己的 `config.yaml` 和 Wiki 数据留在本地，不进入 GitHub。
