$ErrorActionPreference = 'Stop'

Write-Host 'Installing Research Workbench dependencies...'

codex plugin marketplace add https://github.com/Imbad0202/academic-research-skills --ref main --json
codex plugin marketplace add https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep --ref main --json

codex plugin add academic-research-skills --marketplace academic-research-skills --json
codex plugin add aris --marketplace aris --json
codex plugin add zotero --marketplace openai-curated-remote --json
codex plugin add app-6a60df60877081919ad4a8109d27535d --marketplace openai-curated-remote --json

Write-Host 'Bundled skills include LaTeX, imagegen, presentations, nature figure checks, SVG/PPTX conversion and Zotero.'
Write-Host 'The Undermind connector may require a one-time sign-in/connection in Codex.'

$source = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$marketplace = Join-Path $source '.agents/plugins/marketplace.json'
if (Test-Path $marketplace) {
  codex plugin marketplace add $source --json
  codex plugin add literature-research-workbench --marketplace personal-research-workbench --json
}

Write-Host 'Installation finished. Restart Codex and run literature-research-workbench:setup.'
