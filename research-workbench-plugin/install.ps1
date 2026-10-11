$ErrorActionPreference = 'Stop'

Write-Host 'Installing Research Workbench dependencies...'

codex plugin marketplace add https://github.com/Imbad0202/academic-research-skills --ref main --json
codex plugin marketplace add https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep --ref main --json

codex plugin add academic-research-skills --marketplace academic-research-skills --json
codex plugin add aris --marketplace aris --json

Write-Host 'The following Codex-provided capabilities must be enabled in the same Codex account:'
Write-Host '  Zotero, nature-skills, LaTeX, imagegen, presentations, image-svg-pptx-pro'
Write-Host 'The Undermind connector must also be enabled; it is an app connector, not a local skill folder.'

$source = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$marketplace = Join-Path $source '.agents/plugins/marketplace.json'
if (Test-Path $marketplace) {
  codex plugin marketplace add $source --json
  codex plugin add literature-research-workbench --marketplace personal-research-workbench --json
}

Write-Host 'Installation finished. Restart Codex and run literature-research-workbench:setup.'
